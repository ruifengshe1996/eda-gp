# Global Placement Research (DREAMPlace-based)

Goal: improve global placement algorithms on top of DREAMPlace.

## Layout

- `dreamplace-src/` — DREAMPlace source (github.com/limbo018/DREAMPlace master + submodules);
  ISPD2005 benchmarks at `dreamplace-src/benchmarks/ispd2005/`
- `dreamplace-src/build/` — CMake build tree (incremental rebuilds)
- `install/` — installed DREAMPlace; run everything from here
- `venv/` — Python 3.10 + torch 2.0.1+cu118
- `deps/local/` — locally built bison/flex/boost/m4 (no sudo)
- `deps/cuda-11.8/` — user-local CUDA 11.8 toolkit
- `docs/DREAMPLACE_NOTES.md` — code architecture notes
- `docs/ISPD2005_BASELINE.md` — reproduced baseline results & how-to-run

## Quick start

```bash
source env.sh
cd install
python dreamplace/Placer.py test/ispd2005/adaptec1.json
```

## Where the GP algorithm lives (for our research)

- `dreamplace/PlaceObj.py` — objective (WL + lambda*density), lambda/gamma schedules
- `dreamplace/NonLinearPlace.py` — optimization loop, stopping criteria
- `dreamplace/NesterovAcceleratedGradientOptimizer.py` — solver
- `dreamplace/ops/` — C++/CUDA operators (wirelength, electrostatic density, ...)
