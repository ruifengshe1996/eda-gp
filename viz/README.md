# Iteration Visualization — ISPD2005 Baseline

10 snapshots per design of the global placement trajectory, from initialization
(iter 0) to the final legalized + detailed-placed layout (last slice). Slices are
evenly spaced by iteration index. Red = fixed macros/IO, blue = movable cells,
gray speckle = filler cells.

Generated from deterministic re-runs (same seed/config as the baseline in
`docs/ISPD2005_BASELINE.md`; final wHPWL bit-identical to baseline logs) with
`plot_flag=1` and the `plot_iteration_interval` parameter added in
`dreamplace/NonLinearPlace.py`, then selected/compressed by
`scripts/select_viz_slices.py`.

Regenerate:

```bash
source env.sh
cd install
for d in adaptec1 ... bigblue4; do python dreamplace/Placer.py viz_configs/$d.json; done
cd .. && python scripts/select_viz_slices.py
```
