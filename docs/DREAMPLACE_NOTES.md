# DREAMPlace Source Code Notes

Repo: `dreamplace-src/` (github.com/limbo018/DREAMPlace, master @ 6627f33, DREAMPlace 4.x)

## What it is

GPU-accelerated analytical placer. Formulates global placement (GP) as nonlinear
optimization: `min_pos  WL(pos) + lambda * D(pos)`, solved with PyTorch autograd +
custom C++/CUDA ops. The analogy: cell positions = trainable parameters, objective =
"loss", one optimization = "training". Electrostatics-based density (ePlace/RePlAce
family), Nesterov optimizer, then legalization + detailed placement.

## Top-level flow (`dreamplace/Placer.py`)

```
Params (json) -> PlaceDB (parse bookshelf/LEF-DEF via Limbo C++)
             -> NonLinearPlace(params, placedb, timer)   # GP + LG + DP
             -> placedb.write(...)                        # .gp.pl solution
             -> optional external NTUplace detailed placement
```

## Class hierarchy

- `BasicPlace` (`BasicPlace.py`): base nn.Module.
  - `PlaceDataCollection`: all numpy arrays from PlaceDB moved to torch tensors
    (node sizes, pin offsets, net/pin maps, bin structure). `pos` is the single
    trainable flat tensor `[x_all; y_all]` (movable + fixed + fillers).
  - `PlaceOpCollection`: lazily built ops: `pin_pos_op`, `hpwl_op`, `move_boundary_op`,
    `legality_check_op`, `legalize_op` (macro_legalize -> greedy_legalize -> abacus),
    `detailed_place_op` (global_swap / independent_set_matching / k_reorder),
    `draw_place_op`, fence-region variants.
- `NonLinearPlace(BasicPlace)` (`NonLinearPlace.py`): the GP engine.
- `PlaceObj(nn.Module)` (`PlaceObj.py`): objective for one GP stage.

## GP algorithm structure (`NonLinearPlace.__call__`)

3-nested loop generalizing ePlace/RePlAce:

```
for Lgamma iter (outer, updates gamma of WL smoothing):        # <= iteration (1000)
  for Llambda iter (updates density weight lambda):            # Llambda_density_weight_iteration (1)
    for Lsub iter (inner descent steps):                       # Lsub_iteration (1)
      one_descent_step: obj_and_grad_fn -> optimizer.step()
```

- Optimizer: custom `NesterovAcceleratedGradientOptimizer.py` (Nesterov with
  Lipschitz-constant-based step size prediction, per ePlace; optional BB step via
  `use_bb`) or any torch/torch_optimizer solver (adam etc. configured in json).
- Stop criteria:
  - Lgamma: `step > 100 && overflow < stop_overflow (0.07) && hpwl increasing`,
    plus divergence detection (overflow rising & hpwl > 2x best).
  - Llambda: overflow < stop or max_density < 1.
  - Lsub: moving-average objective plateau (threshold 0.999).
- Extra machinery: divergence check + entropy injection (gradient noise to escape
  saddle/local minima at high overflow plateau), best-solution checkpointing
  (`best_metric`/`best_pos`), fence-region multi-electrostatics (DREAMPlace 3.0),
  2-stage macro placement (`macro_place_flag`, 4.1), routability opt
  (rudy/pin-utilization based cell inflation), timing opt (4.x, OpenTimer/HeteroSTA
  net weighting).

## Objective (`PlaceObj`)

- `obj_fn(pos) = wirelength_op(pos) + density_weight * density_op(pos)`
  - optional quadratic density penalty (`quad_penalty`, RePlAce-style).
- `obj_and_grad_fn`: zero grad -> obj.backward() -> `precondition_op` divides grad by
  Jacobi preconditioner (num_pins + lambda * node_area per node).
- WL models: `weighted_average` (WA, default) or `logsumexp`; both with per-net gamma,
  `gamma = base_gamma * f(overflow)` updated each Lgamma iter (10^(k*overflow+b) scaling).
- Density: `electric_potential` op = ePlace electrostatics, spectral Poisson solve via
  DCT/IDCT (`ops/dct`), grad = field * charge(area). Fillers included.
- `initialize_density_weight`: lambda_0 s.t. density grad norm ~ density_weight_factor *
  WL grad norm (8e-5 config).

## Key ops (dreamplace/ops/, each = python wrapper + C++ + optional CUDA kernel)

| op | role |
|---|---|
| `weighted_average_wirelength`, `logsumexp_wirelength` | differentiable WL (net-by-net, atomic/merged impls) |
| `electric_potential` (+`dct`) | ePlace density function & gradient (FFT-based Poisson) |
| `hpwl` | exact HPWL metric (evaluation only) |
| `pin_pos` | cell pos -> pin pos scatter |
| `move_boundary` | clamp cells into placeable region |
| `greedy_legalize`, `abacus_legalize`, `macro_legalize`, `legality_check` | legalization |
| `global_swap`, `independent_set_matching`, `k_reorder` | ABCDPlace detailed placement |
| `place_io` | Limbo-based bookshelf/LEF/DEF parse + write (pybind11) |
| `rudy`, `pinrudy`, `pin_utilization`, `adjust_node_area`, `route_utilization` | routability |
| `gift_init` | GiFt graph-signal-processing initialization (ICCAD'24) |
| `timing`, `timing_heterosta` | timing-driven net weighting |
| `fence_region` | region-constrained multi-electrostatics |

## Entry points for our GP algorithm research

- Objective/optimizer live in pure Python: `PlaceObj.py` (obj/grad, lambda & gamma
  schedules), `NonLinearPlace.py` (loop, stop criteria), `NesterovAcceleratedGradientOptimizer.py`.
  These can be modified without touching CUDA.
- New WL/density models = new op dir under `dreamplace/ops/` mirroring an existing one
  (python wrapper + C++/CUDA + CMakeLists), registered in `PlaceObj.build_*`.
- Config: json in `test/ispd2005/*.json`; all knobs in `dreamplace/params.json`.

## ISPD2005 config (test/ispd2005/adaptec1.json)

Bookshelf aux input, 512x512 bins, WA wirelength, nesterov, up to 1000 iters,
target_density 1.0, stop_overflow 0.07, gamma 4.0, density_weight 8e-5,
random_center_init, deterministic, seed 1000. `gpu: 1`.

## Reference HPWL (from DREAMPlace paper/repo, ISPD2005, GP+LG+DP)

adaptec1 ~ 7.3e7 class results; exact numbers vary with version — compare our runs
against the RePlAce/DREAMPlace published tables (DAC'19 paper Table; both legalized HPWL).
