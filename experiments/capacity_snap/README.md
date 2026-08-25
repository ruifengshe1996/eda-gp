# Experiment 1: capacity-constrained spreading of connectivity seeds

Branch `dev_capacity_snap`, direction D3 of `docs/INIT_SENSITIVITY_ANALYSIS.md`:
compose conn-grid's *order* with uniform's *low-overflow spread*.

## Method (`conn_capacity_spread_flag`)

Between the connectivity field and the anchor snap, run a **capacity-clipped,
geometry-respecting recursive bisection**: cuts sit at the area-weighted median
coordinate of the cells (following the field); cells cross a cut only when one
side would exceed `conn_spread_density_slack (1.5) x average fill` of its free
capacity (free = lattice anchors outside fixed-node bboxes, via a prefix-sum
raster). Leaves clip cells into their rect; a global nearest-feasible-anchor
snap finishes. Movable macros (height > 1.5 rows) keep their field positions —
spreading reorders them too aggressively (bigblue3, 2480 movable macros).
Where capacity never binds the method reduces to conn-grid.

Two earlier iterations are documented here for the record: (a) free-area-
proportional bisection with leaf round-robin scatter — destroyed sparse-region
order (bigblue4 +7.9%); (b) geometry-respecting cuts fixed that (+3.4%);
macro exclusion was needed for bigblue3 but is not sufficient (see below).

## Results (vs. center baseline; uniform/conn-grid columns for reference)

| Design | center | uniform d | conn-grid d | **cap-spread d** | GP iters (C/U/G/S) |
|---|---|---|---|---|---|
| adaptec1 | 72.79 | +0.58% | +0.08% | **-0.08%** | 611/381/611/473 |
| adaptec2 | 81.89 | -0.29% | +2.11% | **-0.79%** | 646/396/626/558 |
| adaptec3 | 193.02 | +0.74% | +0.03% | +1.16% | 679/412/657/564 |
| adaptec4 | 173.56 | +3.74% | +3.55% | +3.23% | 716/420/677/565 |
| bigblue1 | 89.25 | +0.23% | -0.14% | +0.22% | 682/407/688/518 |
| bigblue2 | 136.86 | +3.07% | +0.84% | **+0.39%** | 674/409/623/571 |
| bigblue3 | 304.35 | +5.03% | +1.16% | **+20.74%** | 993/723/1017/872 |
| bigblue4 | 742.64 | +3.84% | +0.03% | +3.42% | 845/507/804/708 |

Geomean: +3.34% (bigblue3 dominates; excluding it: ~+1.0%). All runs legal.

## Findings

- The order+spread composition works on regular standard-cell designs:
  adaptec1/2 now **beat the baseline** (-0.08%/-0.79%) with 13-23% fewer GP
  iterations — the first strategy to win on quality anywhere while saving
  iterations everywhere (-13..-24%).
- **bigblue3 is a hard counterexample** (+20.7%): its connectivity field is one
  extremely dense clump, so *any* capacity bound (slack 1.5 or 3.0 tested)
  stretches the whole netlist (init HPWL 2.3e9 vs 0.56e9 for conn-grid), and
  the optimizer converges quickly into a poor basin (overflow 0.07 at iter 600
  with HPWL stuck ~15% high, then divergence-recovery). This design *needs*
  the melt phase; macro exclusion alone does not save it.
- bigblue4 (+3.42%) sits between: spreading trades its conn-grid quality
  (+0.03%) for iteration savings (804 -> 708).
- Interpretation: spreading pays where the field is locally clumped (declump =
  low overflow head start); it hurts where the field is *globally* collapsed,
  because bounded-density projection of a point-like field is
  order-destroying at long range. A field-quality gate (e.g. spread only if
  field spans > x% of the layout, or per-region partial spreading) is the
  obvious follow-up; the obstacle-aware field (experiment 2) may also
  de-collapse such fields at the source.

## Reproduce

```bash
source env.sh && cd install
for d in adaptec1 ... bigblue4; do python dreamplace/Placer.py ../experiments/capacity_snap/configs/$d.json; done
cd .. && python scripts/ab_report.py --variant "uniform=experiments/uniform_init/logs" \
  --variant "conn-grid=experiments/conn_grid_init/logs" \
  --variant "cap-spread=experiments/capacity_snap/logs" --out experiments/capacity_snap
```
