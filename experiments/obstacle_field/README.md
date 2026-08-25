# 实验 2：障碍感知连通性场（obstacle-aware connectivity field）

分支 `dev_obstacle_field`，对应 `docs/INIT_SENSITIVITY_ANALYSIS.md` 的方向 **D2**：
连通性场在计算时对固定宏障碍视而不见（仅在吸附步应用掩码），推测这是
conn-grid 在 adaptec2/4 上退化、以及部分场塌缩的来源。本实验把障碍投影
引入场的迭代本身，检验两个假设：

- **H1**：adaptec2/4 的退化来自"细胞被嵌到障碍错误一侧"（M5）；
- **H2**：障碍感知场能在源头缓解 bigblue3 型的场全局塌缩（实验 1 遗留问题）。

## 方法（`conn_obstacle_project_flag`）

对固定节点占用做半步栅格化后，用一次 EDT（欧氏距离变换）预计算每个被占
栅格点的最近自由点；每次 Jacobi 扫掠结束后，把落入障碍内部的细胞中心投影
到最近自由栅格点（`ConnectivityGridInit.py: _make_obstacle_projector`）。
场的松弛过程因此始终在可行域附近演化，细胞在扫掠间被迫绕开障碍选边。

两个变体，均与实验 0/1 的对应版本仅差这一个开关：

- **obsfield** = conn-grid 吸附 + 障碍投影；
- **obsspread** = 容量约束展开（实验 1）+ 障碍投影。

由于 GPU 架构较此前提交的数字发生变化，center / conn-grid / cap-spread
三个参照全部在本机重跑（`run_all.sh`，GPU 0 串行）。

## 结果（相对本机 center 基线，wHPWL ×1e6）

| 设计 | center | conn-grid | cap-spread | obsfield | obsspread | GP 迭代 (C/G/S/OF/OS) |
|---|---|---|---|---|---|---|
| adaptec1 | 72.81 | +0.06% | −0.08% | +0.06% | **−0.08%** | 611/603/471/610/466 |
| adaptec2 | 81.96 | +2.04% | −0.89% | **+0.49%** | −0.81% | 640/636/557/601/533 |
| adaptec3 | 193.05 | +0.05% | +1.09% | +0.26% | +0.37% | 679/657/564/616/538 |
| adaptec4 | 173.62 | +3.60% | +3.09% | +3.59% | +3.46% | 715/657/585/666/555 |
| bigblue1 | 89.26 | −0.13% | +0.22% | −0.17% | +0.20% | 677/684/514/686/517 |
| bigblue2 | 136.92 | +0.85% | +0.35% | +0.93% | +0.32% | 664/622/570/629/570 |
| bigblue3 | 304.23 | +1.15% | +20.70% | **+0.91%** | +20.89% | 995/1018/873/1013/879 |
| bigblue4 | 742.60 | +0.01% | +3.50% | +0.31% | +4.10% | 846/809/704/781/692 |

geomean：conn-grid **+0.95%**，cap-spread +3.30%，obsfield **+0.79%**，
obsspread +3.35%。全部运行合法（legal flag = 1）。

## 发现

- **H1 部分成立，且只对 adaptec2 成立。** obsfield 把 conn-grid 的最大离群
  点 adaptec2 从 +2.04% 修复到 +0.49%（正是分析文档点名的宏密集设计），
  bigblue3 也小幅改善（+1.15% → +0.91%）；obsfield 以 geomean +0.79% 成为
  迄今最好的非中心初始化。但 **adaptec4 完全不动**（+3.60% → +3.59%）：
  它的退化与障碍错侧无关，"adaptec2/4 同病"的猜想被证伪。其余设计上投影
  近似中性（adaptec3/bigblue2/bigblue4 各恶化 0.2–0.3pp，可视作噪声级）。
  迭代数与 conn-grid 相当，无节省。
- **H2 不成立。** obsspread 相对 cap-spread 无整体增益（+3.35% vs +3.30%）：
  bigblue3 依旧灾难性（+20.89%）——其连通性场塌缩为一个点团是**连通结构
  本身**驱动的，不是障碍造成的，障碍感知无从解救；实验 1 提出的
  "field-quality gate（场质量门控，塌缩时退回不展开）"仍是该设计的正解。
  adaptec3 上投影确实救回了展开的损失（+1.09% → +0.37%），但 bigblue4
  恶化（+3.50% → +4.10%），两相抵消。展开系变体保留 −13~−24% 的迭代节省。
- **adaptec4 对所有已试策略免疫**（四个变体全部停在 +3.1~3.6%）：非纯排序
  （conn-grid 无效）、非密度容量（cap-spread 无效）、非障碍错侧（obsfield
  无效）。它是当前理解框架外的失败模式，需要 D5 式专项归因（多种子方差、
  逐迭代与 center 轨迹的分叉点定位、宏几何相关性）。

## 下一步

1. **组合最优 + 门控**：obsfield 修复 adaptec2、cap-spread 提供迭代节省，
   两者已在 obsspread 中组合但被 bigblue3 拖垮 —— 实现 field-quality gate
   （场跨度 < 阈值时跳过展开），预期得到 geomean < +0.5% 且大部分设计省
   迭代的变体。
2. **adaptec4 专项诊断**（D5）。
3. **D1 调度热身**（gamma_warmup / density_weight_warmup 脚手架已提交，
   尚未测试）。

## 复现

```bash
experiments/obstacle_field/run_all.sh   # 5 变体 × 8 设计，GPU 0 串行，可断点续跑
python scripts/ab_report.py --a-logs experiments/obstacle_field/logs/center \
  --variant "conn-grid=experiments/obstacle_field/logs/conn_grid" \
  --variant "cap-spread=experiments/obstacle_field/logs/cap_spread" \
  --variant "obsfield=experiments/obstacle_field/logs/obsfield" \
  --variant "obsspread=experiments/obstacle_field/logs/obsspread" \
  --out experiments/obstacle_field
python scripts/select_viz_slices.py --src install/obsfield_results --dst experiments/obstacle_field/viz/obsfield
python scripts/select_viz_slices.py --src install/obsspread_results --dst experiments/obstacle_field/viz/obsspread
python scripts/make_montage.py experiments/obstacle_field/viz/obsfield experiments/obstacle_field/viz/obsspread
```

迭代过程可视化：`viz/obsfield/<design>_all.png`、`viz/obsspread/<design>_all.png`
（每设计 10 张均匀切片拼图，含 iter 0 与最终合法化结果）。
