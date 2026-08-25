# ISPD2005 Baseline Results (DREAMPlace master @ 6627f33)

Date: 2026-08-21. Machine: RTX 3080 Laptop 8GB (sm_86), CUDA 11.8, torch 2.0.1+cu118,
float32, deterministic_flag=1, random_seed=1000, default `test/ispd2005/*.json` configs
(WA wirelength, nesterov, 512x512 bins for small designs, target_density 1.0,
stop_overflow 0.07). Full flow = GP + legalization (greedy+abacus) + DP (ABCDPlace
k_reorder etc.). All designs pass legality check.

wHPWL = detailed-placement-final weighted HPWL as reported by Placer.py.
Reference = DREAMPlace column of Table 2, DAC'19 paper (V100, double precision).

| Design   | #cells | ours wHPWL (x1e6) | paper (x1e6) | delta | GP iters | total time (s) |
|----------|--------|-------------------|--------------|-------|----------|----------------|
| adaptec1 | 211K   | 72.79             | 73.30        | -0.7% | 613      | 9.9            |
| adaptec2 | 255K   | 81.89             | 82.19        | -0.4% | 648      | 13.0           |
| adaptec3 | 452K   | 193.02            | 194.12       | -0.6% | 681      | 22.1           |
| adaptec4 | 496K   | 173.56            | 174.43      | -0.5% | 718      | 23.7           |
| bigblue1 | 278K   | 89.25             | 89.43        | -0.2% | 684      | 12.2           |
| bigblue2 | 558K   | 136.86            | 136.69       | +0.1% | 676      | 24.2           |
| bigblue3 | 1097K  | 304.35            | 303.99       | +0.1% | 995      | 65.0           |
| bigblue4 | 2177K  | 742.64            | 743.75       | -0.2% | 847      | 94.3           |

Reproduction is within +-0.7% of published HPWL on all 8 designs — baseline confirmed.

## How to reproduce

```bash
cd /home/ruifengshe/research/eda/gp
source env.sh                      # venv + PATH + LD_LIBRARY_PATH
cd install
python dreamplace/Placer.py test/ispd2005/adaptec1.json
# logs from this baseline: install/<design>_run.log
# solutions: install/results/<design>/<design>.gp.pl
```

## Rebuild after source changes

```bash
source env.sh
cd dreamplace-src/build
make -j2 && make install           # keep -j2: machine is memory-tight (oomd)
```

Note: python-only changes under `dreamplace/*.py` still require `make install`
(or edit directly in `install/` during experiments, then port back).
