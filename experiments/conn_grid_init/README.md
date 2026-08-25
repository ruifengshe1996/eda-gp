# Experiment: connectivity-aware grid-anchored initialization

Branch `dev_conn_grid_init`. Third init strategy after center (baseline) and
uniform ([experiments/uniform_init](../uniform_init/README.md)):

1. **Connectivity-aware field**: `conn_init_sweeps` (32) damped Jacobi sweeps —
   each movable cell moves toward the mean position of its net neighbors (nets
   with degree > `ignore_net_degree` skipped), starting from a uniform scatter,
   with fixed macros/IO as boundary anchors. This approximates a quadratic
   (harmonic) placement: strongly connected cells end up near each other and
   near their fixed pins.
2. **Snap to lattice anchors**: every cell snaps to the nearest *feasible*
   anchor, where anchors = bin-grid vertices + bin-edge midpoints (half-step
   lattice minus bin centers).
3. **Infeasible-region mask**: anchors covered by any fixed node's bounding box
   or outside the layout are removed before snapping (e.g. adaptec1: 43% of
   790k lattice points masked; bigblue4: 7.85M anchors remain).

Implementation: `dreamplace/ConnectivityGridInit.py` + `connectivity_grid_init_flag`
(precedence over the other init flags), knobs `conn_init_sweeps`, `conn_init_damping`.
Init cost: ~0.3s (adaptec1, 211k cells) to ~12s (bigblue4, 2.2M cells), CPU numpy
sweeps + KD-tree snap.

## Results (full flow, seed 1000, all runs pass legality check)

See `metrics.md` / `metrics.csv`; three-way vs. baseline and uniform:

| Design | center | uniform | conn-grid | uniform delta | conn-grid delta | GP iters (C/U/G) |
|---|---|---|---|---|---|---|
| adaptec1 | 72.79 | 73.21 | 72.85 | +0.58% | +0.08% | 611/381/611 |
| adaptec2 | 81.89 | 81.66 | 83.62 | -0.29% | +2.11% | 646/396/626 |
| adaptec3 | 193.02 | 194.45 | 193.08 | +0.74% | +0.03% | 679/412/657 |
| adaptec4 | 173.56 | 180.04 | 179.72 | +3.74% | +3.55% | 716/420/677 |
| bigblue1 | 89.25 | 89.45 | 89.13 | +0.23% | **-0.14%** | 682/407/688 |
| bigblue2 | 136.86 | 141.07 | 138.01 | +3.07% | +0.84% | 674/409/623 |
| bigblue3 | 304.35 | 319.66 | 307.87 | +5.03% | +1.16% | 993/723/1017 |
| bigblue4 | 742.64 | 771.17 | 742.84 | +3.84% | +0.03% | 845/507/804 |

Geomean wHPWL delta: **conn-grid +0.95%** vs uniform +2.10%. wHPWL in x1e6.

## Findings

- **Quality**: conn-grid recovers most of what pure uniform loses. Four designs
  are neutral-or-better (adaptec1/3, bigblue1/4; bigblue1 beats the baseline),
  and the large-design penalty of uniform (+3.8..5.0%) collapses to +0.03..1.2%.
  The connectivity sweeps restore the global relative order that uniform
  scatter destroys — confirming that this ordering is exactly what center init
  buys.
- **Convergence**: unlike uniform (-38% iterations), conn-grid tracks the
  baseline overflow trajectory almost exactly (same ~0.8 plateau, similar
  iteration counts, slightly earlier descent on adaptec4/bigblue2/4). The
  harmonic field re-clusters connected cells, so local density — and hence the
  spreading work — is back to baseline-like levels.
- **Outliers**: adaptec2 (+2.1%) and adaptec4 (+3.6%) still lose; adaptec4 is
  init-sensitive for every non-center strategy tried so far.
- Initial wHPWL is only ~1.3-1.5x the final value (uniform: 30-40x), so the
  optimizer starts in a near-feasible basin. HPWL curves: `curves_hpwl.png`,
  overflow: `curves_overflow.png`, snapshots: `viz/<design>/`.

## Takeaway

Connectivity-aware anchoring turns uniform init from "2% worse, 40% faster"
into "1% worse, same speed" — i.e. it trades the speed win back for quality.
Neither variant dominates center init on quality yet. Follow-ups: fewer/damped
sweeps to *partially* preserve spread (interpolate between uniform and harmonic
field), per-anchor capacity limits to avoid re-clustering (keep some of the
uniform iteration savings), and a hybrid schedule (uniform-style low-overflow
start + connectivity-ordered assignment).

## Reproduce

```bash
source env.sh && cd install
for d in adaptec1 ... bigblue4; do
  python dreamplace/Placer.py ../experiments/conn_grid_init/configs/$d.json
done
cd .. && python scripts/ab_report.py \
  --variant "uniform=experiments/uniform_init/logs" \
  --variant "conn-grid=experiments/conn_grid_init/logs" \
  --out experiments/conn_grid_init
python scripts/select_viz_slices.py --src install/conn_results --dst experiments/conn_grid_init/viz
```
