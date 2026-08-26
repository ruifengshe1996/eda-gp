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
- `viz/` — 10 iteration snapshots per ISPD2005 design (see `viz/README.md`)
- `scripts/` — helper scripts

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

## 实验结果 WebUI（tools/webui）

实时扫描 `experiments/` 与 `docs/` 的展示站：实验卡片总览、每个实验的
介绍（README 渲染 + 核心代码 diff）/ 可视化（迭代切片拼图、日志实时解析
的收敛曲线）/ A/B 结果表，以及 docs 文档渲染（marked + KaTeX 公式，
静态资源全部本地 vendor，离线隧道可用）。

```bash
# 首次部署（vendor 静态资源不入库，一次性下载；Flask 装入项目 venv）
bash tools/webui/fetch_vendor.sh
source env.sh && pip install flask

# 长久挂起（单实例 flock 保护，崩溃自动重启；服务器重启后重跑此行即可）
setsid nohup tools/webui/daemon.sh > /dev/null 2>&1 < /dev/null &

# 访问：本地终端建 ssh 隧道，然后浏览器打开 http://localhost:8377
ssh -L 8377:localhost:8377 h200

# 停止
pkill -f "webui/daemon.sh"; pkill -f "webui/app.py"
```

服务只绑定 `127.0.0.1:8377`，不对外暴露；日志在 `tools/webui/webui.log`。

## 数据与复现约定

- 仓库只跟踪**文本记录**：configs / logs / metrics / docs / scripts。
  拉取后即可复现任何实验（各实验 README 的 Reproduce 节）。
- 生成的可视化（迭代切片、拼图、曲线 PNG）**不入库**（.gitignore），
  留在生成机本地由 WebUI 展示；缺失时可用
  `scripts/select_viz_slices.py` + `scripts/make_montage.py` 从运行结果
  再生，收敛曲线由 WebUI 从 logs 现场解析、无需 PNG。
- 全项目结果汇总与下一步方向见 `docs/RESULTS_SUMMARY.md`。
