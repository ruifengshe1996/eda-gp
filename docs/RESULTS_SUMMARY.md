# 全局布局初始化研究：总结与展望（截至 2026-08-26）

本文汇总本仓库全部九条实验线的结果与机制结论，区分 conn-y bug 勘误前后的
数据有效性，给出修复后的最终数据全景与下一步方向。所有特性均为默认关闭的
可开关旋钮（见 §5），所有实验数据、日志与迭代可视化均保留在
`experiments/<name>/`。

## 1. 研究问题与时间线

问题：DREAMPlace（ePlace 系）的全局布局对初始化的敏感性——能否用比
center（中心堆叠 + WL 熔化）更聪明的初始化改进 wHPWL / overflow 收敛？

| 实验 | 分支 | 内容 | 数据状态 |
|---|---|---|---|
| 0a uniform | dev_uniform_init | 均匀撒点 vs center | 干净（旧 GPU，仅定性引用） |
| 0b conn-grid | dev_conn_grid_init | 连通性 Jacobi 场 + 格点吸附 | 污染→已重跑 |
| 1 capacity | dev_capacity_snap | 容量约束递归二分展开 | 污染（由 obsspread 语义代表） |
| 2 obstacle | dev_obstacle_field | 障碍感知场（EDT 投影） | 污染→已重跑 |
| 3 warmup | dev_field_gate | D1 调度热身（γ/λ） | 污染，结论作废待重检 |
| 4 field-gate | dev_field_gate | 展开门控证伪 + 种子方差 | CPU 探测干净；GPU 结论待重检 |
| 5 GiFt | dev_field_gate | 谱初始化 A/B + 质心签名 | **干净** |
| 6 conn-shrink | dev_conn_shrink | 保序收缩居中紧凑团 | 污染→已重跑，**修复版冠军** |
| 7 combiner | dev_conn_shrink | 逐设计路由 + 三口径 | 已按修复版重算 |
| 勘误+重跑 | dev_fix_conn_y | bug 修复 + 33 运行重跑 | 本文主数据 |

## 2. conn-y bug（贯穿实验 0b–7 的勘误）

`BasicPlace.py` 初始化的 y 段曾把 conn 分支写好的 conn_y 整段覆盖为基准
文件原始 y（ISPD2005 的 movable 全部堆在底边）。因此修复（434fa96）前所有
`connectivity_grid_init_flag=1` 的 GPU 运行实测的都是**意外变体
"x=场分布、y=底边直线"**（一种底边中点的点熔化）。GiFt / center / uniform
路径不受影响。发现过程与方法论教训见 `docs/ADAPTEC4_DIAGNOSIS.md` 勘误节；
两条守则已入项目规范：**探测与真实运行的初值不一致本身就是 bug 信号**；
分析结论必须注明数据来自哪个代码版本。

## 3. 修复后主数据（本机 L20X，同机 center 基线，确定性种子）

| 设计 | conn-grid | obsfield | obsspread | shrink001 | GiFt |
|---|---|---|---|---|---|
| adaptec1 | +0.07% (543) | **−0.03%** (547) | +0.24% (421) | +0.04% (607) | +0.50% (423) |
| adaptec2 | +0.58% (573) | +0.37% (542) | +1.14% (429) | −0.11% (648) | **−0.56%** (428) |
| adaptec3 | +0.55% (574) | +0.63% (575) | +0.15% (456) | **−0.12%** (690) | +0.59% (453) |
| adaptec4 | +0.20% (605) | **+0.05%** (597) | +1.40% (502) | +0.07% (715) | +2.46% (473) |
| bigblue1 | +0.02% (644) | +0.01% (649) | +0.21% (461) | +0.01% (674) | +0.33% (450) |
| bigblue2 | +0.94% (592) | +0.99% (597) | +1.21% (481) | **−0.05%** (660) | +3.15% (471) |
| bigblue3 | +0.86% (905) | +0.75% (910) | +9.27% (818) | **−0.10%** (1027) | +5.14% (958) |
| bigblue4 | −0.05% (727) | **−0.07%** (755) | +1.26% (561) | −0.06% (923) | +3.42% (565) |
| **geomean** | +0.40% | +0.34% | +1.82% | **−0.04%** | +1.86% |
| 迭代 vs center | −5~15% | −4~16% | **−18~34%** | −1~+9% | −25~34% |

组合器口径（`experiments/combiner/routing_table.md`）：oracle-always
−0.11%，oracle-or-center −0.12%；相对 always-shrink001 的路由增益仅
~0.08pp。**质量维度上逐设计路由已无必要，shrink001 单策略即达 center
水平且过半设计微胜；路由的剩余价值在速度模式**（迭代预算下选
obsspread/GiFt）。

## 4. 机制结论清单（幸存 / 被证伪）

**幸存（修复后数据支持）**：
1. **"预制序 + 居中紧凑几何 + 标准同伦" ⇔ center**：shrink001 全面等价
   甚至微胜。center 的熔化没有不可替代的魔法；此前的"+2.4~2.6% 序质量
   地板""adaptec4 免疫""熔化动力学不可替代（D1 否定的正面叙事）"全部是
   bug 伪影。
2. **塌缩场 + 容量展开的长程排序破坏在 bigblue3 上真实存在**（修复后仍
   +9.27%，幅度腰斩）；其余设计展开代价 ≤ +1.4%。
3. **迭代节省来自低 overflow 起步**：obsspread −30%、GiFt −30%、
   obsfield −12%，修复前后一致成立。
4. **GiFt 与 Jacobi 场在 adaptec2 上非支配**（GiFt −0.56% 仍是 a2 最优），
   谱全局解与局部松弛各有胜场。
5. **种子噪声极小**：center/conn 系种子极差 0.1~0.4pp（S1 + 实验 4B，
   4B 为污染版测量，但 center 部分干净）——±0.5pp 以上的声称可信。
6. 意外变体（底边点熔化）本身成绩不俗（污染版 conn-grid +0.95%），说明
   **一维场序即有价值、熔化点位置是待正式化的旋钮**（实验 9 注册预测：
   a3 底边点熔化应胜修复版 conn-grid 的 +0.55%）。

**被证伪 / 作废**：
- D1 调度热身的否定结论（污染数据，待重检——见 §6/P2）；
- 实验 4 "展开伤害结构性、门控不可分" 的 GPU 部分（待修复版重提，问题
  本身已缩水：只剩 b3 一个大受害者）；
- E4 锚点拖拽、E5 集中度、E6 序内容地板（e0 已在机制文档中勘误撤销）；
- 障碍投影"修复 adaptec2 错侧"的大部分效应（+2.04→+0.49 主要是 y 直线
  伪影；修复版上 obsfield 对 a2 的增益只剩 +0.58→+0.37）。

## 5. 特性开关清单（全部默认关闭，可自由组合）

| 旋钮 | 功能 | 引入实验 |
|---|---|---|
| `connectivity_grid_init_flag` | 连通性 Jacobi 场初始化（总开关） | 0b |
| `conn_init_sweeps` / `conn_init_damping` | 场松弛迭代数 / 阻尼 | 0b |
| `conn_obstacle_project_flag` | 场的 EDT 障碍投影 | 2 |
| `conn_capacity_spread_flag` + `conn_spread_leaf_size` / `conn_spread_density_slack` | 容量约束递归二分展开 | 1 |
| `conn_shrink_scale` | 保序收缩到 σ×芯片宽的居中紧凑团 | 6 |
| `gift_init_flag` / `gift_init_scale` | GiFt 谱初始化（上游自带） | 5 |
| `gamma_warmup_iters` / `gamma_monotone_flag` / `density_weight_warmup_iters` | 调度热身旋钮 | 3 |
| `random_center_init_flag` | center 基线（DREAMPlace 原默认） | — |

推荐配置：**质量优先** `connectivity_grid_init_flag=1, conn_shrink_scale=0.001`；
**速度优先** `connectivity_grid_init_flag=1, conn_obstacle_project_flag=1,
conn_capacity_spread_flag=1`（−30% 迭代 @ +1.8%）或 `gift_init_flag=1`。

## 6. 下一步方向（首要目标：优化 overflow 与 wHPWL）

**P0 — shrink 邻域深挖（当前冠军的直接优化）**
shrink001 是 −0.04% 的新起点，其参数空间几乎未探索：
(a) σ 扫描：仅测过 0.001（优）/0.01，向更小 σ 与"σ 随设计规模自适应"推进；
(b) **收缩中心位置 = 熔化点旋钮**（实验 9，零代码 .pl 注入物料已就绪，
含 a3 底边注册预测）——若按锚几何选边可预测地增益，就是免费的质量维度；
(c) shrink × obstacle projection / shrink × 部分展开杂交：shrink 起步
overflow≈1 无迭代节省，若收缩到 σ=0.05~0.1（半紧凑）可能在保质量的同时
拿回部分节省——**质量-速度前沿的内插是最有希望把 geomean 推向明确负值
且省迭代的方向**；
(d) shrink 的 b3/b4 迭代惩罚（+3~9%）源于大设计的重熔成本，λ₀/γ 起点
微调有回收空间。

**P1 — 调度×初始化联合重检（D1 复活）**
实验 3 的否定建立在污染数据上。修复版的具体问题：obsspread 起步
overflow≈0.6，沿用为 center 设计的 λ₀ 归一化与 γ(overflow) 调度——
按实验 4 竞速门数据，其质量损失在 ov 0.5 前就锁定。针对**低 overflow
起步态**重新设计 λ₀/γ 入口（如 λ₀ 按参考态归一、γ 按初始 overflow 平移），
目标：保住 −30% 迭代并把 +1.8% 压到 +0.5% 以内。这是"速度模式"的关键。

**P2 — 实验 8：ISPD2015 盲测（可信度收官）**
协议已定（全量 mgc 设计、路由表预注册先 commit、单设计冒烟例外、阈值
迁移如实报告）。修复后地基上主轴简化为 **always-shrink001 vs center**
（单策略、零路由自由度，盲测最干净），副轴 obsspread（速度模式泛化性）。
n=8→n≈24，是把本仓库全部结论从"ISPD2005 拟合"升级为"可信方法"的
唯一路径。

**P3 — bigblue3 型网表的展开修复（幸存的真机制）**
b3 +9.27% 是修复后唯一的大失败点。方向：展开位移半径上限（局部解团、
不做全局重排）、或 shrink 后按 bin 溢出率做**部分展开**——与 P0(c) 合流。

**P4 — overflow 目标本身**
现有全部结论以 stop_overflow=0.07 的 wHPWL 为指标。值得做一次
stop_overflow ∈ {0.05, 0.07, 0.10} × {center, shrink001, obsspread} 的
小扫描，确认结论对合法性目标的稳健性，并观察 shrink001 是否在更严
overflow 下扩大优势（其最终态密度分布更均匀的假设待验）。

**执行建议**：P0(b)（3-4 运行）与 P0(a)（4-6 运行）最便宜先行；P1 需少量
代码（调度入口旋钮已有脚手架）；P2 在 P0/P1 冻结后启动。

## 7. 数据与可视化索引

- 修复版主数据：`experiments/conn_rebuild/`（logs / metrics / 32 张 montage）
- 修复版路由表：`experiments/combiner/routing_table.md`
- 意外变体存档：各 `experiments/<name>/`（README 带污染横幅）+
  `install/*_results`（未跟踪）
- 机制文档：`docs/ADAPTEC4_DIAGNOSIS.md`（含勘误链）、
  `docs/INIT_SENSITIVITY_ANALYSIS.md`（D1–D5 结果标注）
- 取证与注入工具：`scripts/`（fallprobe / initpos_diff / frame_centroid /
  spread_trace / pmix_gen / gen_shrinkblob / meltpoint_gen /
  spread_gate_probe）
