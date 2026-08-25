# Why scattered initialization degrades DREAMPlace results — an analysis

Premise under examination: *"with an objective of overflow + netlist HPWL, a
scattered initialization should not, in theory, degrade the final result."*
That premise holds only for (a) a globally optimal solver, or (b) a convex
objective optimized by a convergent method with a fixed objective. Neither is
true here, and — more importantly — DREAMPlace/ePlace is not even optimizing a
*fixed* objective: it is a **continuation (homotopy) method** whose schedules
are feedback-coupled to the trajectory. Initialization selects the entire
homotopy path, not just a starting point.

Evidence base: `experiments/uniform_init/` (+2.10% geomean wHPWL, −38% GP
iterations) and `experiments/conn_grid_init/` (+0.95%, baseline-like
iterations), 8 ISPD2005 designs, deterministic seed.

## The objective actually optimized

At iteration t the model minimizes

    f_t(x) = WL_gamma(t)(x) + lambda(t) * D(x)

- `WL` is the weighted-average (WA) model — non-convex (unlike LSE), sharpness
  set by gamma;
- `D` is the electrostatic potential energy — strongly non-convex;
- `gamma(t)` and `lambda(t)` are **functions of the trajectory**, not of t alone.

Three code facts (dreamplace/PlaceObj.py):

1. **lambda_0 is normalized to the initial state**
   (`initialize_density_weight`): `lambda_0 = 8e-5 * ||grad WL(x_0)||_1 /
   ||grad D(x_0)||_1`. The WL:density force ratio at iteration 0 is therefore
   1 : 8e-5 *for every initialization* — density starts 12,500x weaker by
   construction. Measured lambda_0 on adaptec1: 7.5e-12 (center) vs 3.9e-8
   (uniform) — 5000x different absolute scale, identical relative force.
2. **lambda grows multiplicatively** (`update_density_weight_op_hpwl`,
   RePlAce-style): `lambda *= mu`, `mu <= UPPER_PCOF (1.05)`, rate driven by
   per-iteration delta-HPWL. The whole lambda(t) ramp is path-dependent.
3. **gamma is a memoryless function of current overflow** (`update_gamma`):
   `gamma = 4.0 * (bin_w + bin_h) * 10^((overflow - 0.1) * 20/9 - 1)`.
   Overflow 1.0 -> coef 10; overflow 0.42 -> coef 0.51. A scattered start
   (low overflow) begins with a ~20x *sharper* WL model than the center start.

## Mechanisms behind the observed degradation

**M1 — The ordering degrees of freedom are combinatorially non-convex.**
D is (nearly) invariant under permutations of equal-size cells; WL is not. The
landscape has exponentially many permutation-local-minima, and gradient descent
cannot perform long-range swaps once cells are spread and interleaved. Center
init solves the *global relative order* almost for free: with all cells
coincident and density initially negligible (fact 1), the first iterations are
a nearly pure WL descent from a symmetric state — effectively a continuous
embedding driven only by connectivity (the "melt" phase). Scattered init
freezes a random order into the spread state.
*Evidence*: connectivity sweeps (conn-grid) — which approximately solve that
embedding — recover most of uniform's loss (+2.10% -> +0.95% geomean; large
designs +3.8..5.0% -> +0.03..1.2%). The residual gap *is* mostly ordering.

**M2 — lambda_0 normalization guarantees an initial collapse.**
Because the initial force ratio is pinned at 1 : 8e-5, any init that is not
already a WL minimizer undergoes a near-pure WL collapse first. Uniform init:
overflow 0.42 -> 0.9 in the first ~30 iterations while HPWL drops 2.2e9 ->
~1e8 — i.e. the algorithm *re-does center init, badly*: cells fall to their
nearest attractor cluster (non-order-preserving), and the ordering that
emerges from this local collapse is what the rest of the flow inherits.
The scattered-random-order dilemma: either lambda is small and the state
collapses (order re-solved locally, poorly), or lambda is large enough to
hold the spread and the random order is frozen. Both lose; only an
*order-aware* scattering escapes the dilemma (see D3).

**M3 — the gamma schedule mis-fires on scattered starts.**
gamma tracks overflow instantaneously. A scattered start gets a sharp WL model
immediately (~20x tighter for uniform), concentrating gradients on extreme
pins and locking in wrong orderings faster. Worse, the non-monotone overflow
path (0.42 -> 0.9 -> 0.07) makes gamma swing back and forth: the optimizer
chases a target that changes non-monotonically. The schedule encodes the
center-init assumption "overflow starts at ~1 and decreases".

**M4 — hyper-parameters are tuned to the center trajectory.**
Minimum 100 Lgamma iterations, stop_overflow 0.07, mu cap 1.05,
density_weight 8e-5, gamma 4.0 — all calibrated around the center-init
homotopy. Scattered trajectories run these knobs off-design. (Secondary.)

**M5 — no long-range repair mechanism downstream, and obstacles are barriers.**
Legalization and ABCDPlace detailed placement are local (row reorder, window
swaps, independent sets); they cannot fix global ordering errors. Fixed macros
are high-potential barriers in D: a cell embedded on the wrong side of a large
blockage cannot migrate across it by gradient descent. The conn-grid field is
computed *obstacle-blind* (mask applies only at the snapping step), which
plausibly explains its outliers adaptec2 (+2.11%) / adaptec4 (+3.55%) — both
macro-heavy floorplans where the harmonic field can place cells on the wrong
side of blockages. adaptec4 degrades under every non-center init tried.

## Improvement directions (mapped to mechanisms)

- **D1 (M2/M3) State-aware schedules.** After a scattered init, deliberately
  re-enter the standard homotopy: an explicit WL-only warm-up phase (lambda=0,
  gamma forced large for N iterations), or initialize lambda/gamma against a
  *reference* state rather than the raw initial state; make gamma follow a
  monotone envelope (e.g. min-overflow-so-far) to kill the swing.
  *Outcome (experiments/schedule_warmup): negated — no warm-up variant beats
  plain conn-grid. The monotone gamma envelope destroys bigblue3 (+4.94%:
  the swing is a necessary divergence-recovery mechanism), warm-up re-freezes
  adaptec2's side commitments (+2.60%), adaptec4 unmoved. The melt's value
  is its dynamics, not its schedule.*
- **D2 (M1/M5) Obstacle-aware connectivity field.** Project each Jacobi sweep
  onto the feasible region (or solve the Laplace system with macro regions
  excluded), so cells choose the correct side of blockages — targets the
  adaptec2/4 failures. Alternatively replace slow local smoothing with a
  spectral / multilevel embedding (the repo's `gift_init_flag` GiFt operator
  is exactly such a graph-filter init and should be A/B'd as a reference).
  *Outcome (experiments/obstacle_field): confirmed for adaptec2 (+2.04% ->
  +0.49%), best non-center variant overall (+0.79% geomean vs conn-grid's
  +0.95%); adaptec4 unmoved (its loss is not obstacle-related) and the
  spread pipeline / bigblue3 collapse unaffected.*
- **D3 (M1 + speed) Capacity-constrained snapping.** Replace nearest-anchor
  snapping with a capacity-limited assignment (cells per anchor bounded by
  local free area — greedy rank assignment or approximate optimal transport
  from the harmonic field to a uniform density). Goal: an initial state that
  is simultaneously *well-ordered* (conn-grid's quality) and *spread at low
  overflow* (uniform's −38% iterations). The two experiments show these
  benefits are separable; this direction tries to compose them. Most promising
  next experiment.
  *Outcome (experiments/capacity_snap, experiments/field_gate): composed
  successfully on 6/8 designs but structurally harmful on bigblue3/4
  (+20.9%/+4.1%, seed-stable to 0.1–0.4pp), and no init-time statistic
  separates the harmed designs — span, displacement, HPWL inflation and
  centroid position all fail (gating falsified). Only an empirical race
  decided at overflow <= 0.4 can arbitrate (+40–80% GP cost). Best single
  choice remains obsfield (D2).*
- **D4 (M5) Mid-flight re-melting.** On plateau detection (overflow stalled,
  HPWL rising), locally raise gamma / inject targeted noise on high-WL-gradient
  cells (the existing entropy_injection machinery, but order-aware), or run one
  discrete reordering pass (ABCDPlace ops) during GP to give frozen orderings a
  second chance.
- **D5 Diagnostics.** Multi-seed variance per init strategy; correlate
  per-design loss with macro area fraction / blockage geometry to confirm the
  wrong-side-of-barrier hypothesis on adaptec2/4.
  *Outcome: seed variance measured (0.09–0.17% for center/conn-grid on
  adaptec4, 0.1–0.4pp for spread variants) — every claimed delta >= 0.5pp in
  this repo is significant. The geometry-correlation hunt came up empty
  (experiments/field_gate probe battery); the per-design diagnosis moved to
  docs/ADAPTEC4_DIAGNOSIS.md.*

## One-line summary

The objective would indeed be init-insensitive under an ideal solver; the
observed sensitivity is a property of the *algorithm*: a permutation-non-convex
landscape optimized by local descent, under a continuation schedule
(lambda_0 normalization, multiplicative lambda ramp, overflow-slaved gamma)
whose implicit assumption is "start clustered, melt by wirelength, then
spread". Scattered inits violate that assumption; the fix is either to restore
the assumption deliberately (warm-up), make the seed order-and-obstacle-aware
(D2), or re-engineer the schedules and the seeding to compose order with
spread (D3).
