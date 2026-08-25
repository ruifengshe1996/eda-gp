# Experiment: uniform initialization vs. center initialization

Branch `dev_uniform_init`. Question: DREAMPlace initializes all movable cells in a
tight Gaussian cluster at the layout center (`random_center_init_flag`); what
happens if we instead scatter them **uniformly over the whole placement region**?

## Change

New `random_uniform_init_flag` parameter (default 0, takes precedence over
`random_center_init_flag`) in `dreamplace/BasicPlace.py` + `dreamplace/params.json`:
movable x ~ U(xl, xh - w_i), y ~ U(yl, yh - h_i). Everything else (seed 1000,
deterministic, WA wirelength, nesterov, ISPD2005 configs) identical to the
baseline in `docs/ISPD2005_BASELINE.md`.

## Results (full flow GP + LG + DP, all runs pass legality check)

| Design | wHPWL center (x1e6) | wHPWL uniform (x1e6) | delta | GP iters (C/U) | flow time s (C/U)* |
|---|---|---|---|---|---|
| adaptec1 | 72.79 | 73.21 | +0.58% | 611/381 | 9.9/6.2 |
| adaptec2 | 81.89 | 81.66 | -0.29% | 646/396 | 13.0/7.7 |
| adaptec3 | 193.02 | 194.45 | +0.74% | 679/412 | 22.1/9.9 |
| adaptec4 | 173.56 | 180.04 | +3.74% | 716/420 | 23.7/22.1 |
| bigblue1 | 89.25 | 89.45 | +0.23% | 682/407 | 12.2/6.0 |
| bigblue2 | 136.86 | 141.07 | +3.07% | 674/409 | 24.2/10.9 |
| bigblue3 | 304.35 | 319.66 | +5.03% | 993/723 | 65.0/56.9 |
| bigblue4 | 742.64 | 771.17 | +3.84% | 845/507 | 94.3/44.5 |

*uniform times have per-frame plotting overhead subtracted (its runs recorded
snapshots); treat them as approximate.

Geomean HPWL delta: **+2.1% worse**. GP iterations: **-38% on average**.

## Reading the curves (`curves_hpwl.png`, `curves_overflow.png`)

- Uniform init starts with ~30-40x higher HPWL (cells scattered at random) but the
  wirelength force collapses it within ~30 iterations to near the baseline level.
- Overflow starts *low* (0.35-0.6 vs 1.0 — cells are already spread), spikes
  briefly while the WL collapse re-clusters cells, then descends much earlier and
  steeper than baseline: the long ~0.8 overflow plateau of center init is skipped
  almost entirely, which is where the iteration savings come from.
- The price: center init lets wirelength organize the *global* relative order of
  cells while everything is still co-located and mobile; uniform init freezes
  random relative order into the spread-out state, and later iterations never fully
  recover it. The damage grows with design size/density: near-neutral on
  adaptec1-3/bigblue1 (<=0.7%), +3-5% on adaptec4/bigblue2-4.
- bigblue3 shows an overflow dip-and-rebound on both variants (divergence
  recovery); uniform hits it earlier but with the same recovery mechanism.

## Takeaway

Uniform init is a **speed/quality trade-off, not a free win**: ~1.4-2x faster GP
with ~2% (up to 5%) worse HPWL, worsening with scale. Supports the ePlace-family
folklore that center init matters for quality. Possible follow-ups: hybrid init
(uniform within a center-biased envelope), net-cluster-aware seeding (place
strongly connected components together, e.g. GiFt `gift_init_flag`), or an
early-iteration gamma/density schedule tuned for the uniform start.

## Files

- `configs/` — the 8 run configs (uniform init + snapshot plotting)
- `logs/` — full run logs (A-side logs live in `docs/logs/`)
- `metrics.csv`, `metrics.md` — parsed A/B metrics (via `scripts/ab_report.py`)
- `curves_hpwl.png`, `curves_overflow.png` — per-design A/B convergence overlays
- `viz/<design>/slice01..10_iterNNNN.png` — 10 evolution snapshots per design
  (baseline snapshots: `viz/<design>/` on branch `main`)

## Reproduce

```bash
source env.sh && cd install
for d in adaptec1 ... bigblue4; do
  python dreamplace/Placer.py ../experiments/uniform_init/configs/$d.json
done
cd .. && python scripts/ab_report.py --b-logs experiments/uniform_init/logs --out experiments/uniform_init
python scripts/select_viz_slices.py --src install/uniform_results --dst experiments/uniform_init/viz
```
