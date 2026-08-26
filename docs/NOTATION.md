# 术语与编号对照表（NOTATION）

本项目所有文档的用词与编号以本文为准。**编写或修改任何文档前先通读本文；
出现新术语或新编号时，先在此登记再使用。** 同一概念只允许一种称呼与一个
编号。

## 1. 基础术语（中文 — 英文 — 说明）

| 中文 | 英文 / 缩写 | 说明 |
|---|---|---|
| 全局布局 | global placement, GP | 布局流程的连续优化阶段 |
| 半周长线长 | half-perimeter wirelength, HPWL | 每条网线包围盒半周长之和 |
| 加权半周长线长 | weighted HPWL, wHPWL | 按网线权重加权的 HPWL；ISPD2005 权重全为 1；本项目**主质量指标** |
| 密度溢出 | density overflow, overflow | 单元密度超出 bin 容量的程度；收敛判据 stop_overflow = 0.07 |
| 目标函数 | objective | wHPWL 的平滑代理（WA 模型）+ λ × 静电密度势能 |
| WA 线长模型 | weighted-average wirelength model | 由 γ 控制锐度的可微线长代理 |
| γ（伽马） | gamma | WA 模型平滑参数；随 overflow 调度 |
| λ（密度权重） | density weight, lambda | 密度项权重；初值按初始梯度比归一，乘性增长 |
| 同伦/延拓调度 | continuation (homotopy) schedules | γ、λ 随迭代演化的整套机制 |
| 中心初始化 | center init (`random_center_init_flag`) | DREAMPlace 默认：全部可动单元置于芯片中心，加 0.1% 芯片宽的高斯噪声 |
| 熔化阶段 | melt phase | 中心初始化后、密度项尚弱时的近纯线长下降段，隐式求解全局相对秩序 |
| 均匀初始化 | uniform init (`random_uniform_init_flag`) | 可动单元在版图上均匀撒点 |
| 连通性场 | connectivity field | 对网表做阻尼 Jacobi 松弛（向网内邻居均值收敛）得到的连续嵌入，由固定引脚锚定 |
| 格点吸附 | anchor snapping | 把场坐标吸附到"半 bin 步长格点 ∖ 固定单元覆盖区"的最近可行锚点 |
| 障碍投影 | obstacle projection | 每次 Jacobi 扫掠后，用预计算 EDT 把落入固定单元区域的单元弹到最近自由栅格点 |
| 容量展开 | capacity spreading | 场与吸附之间的容量受限递归二分：面积加权中位数切割，仅在超出 slack×平均填充率时跨切割移动单元 |
| 保序收缩 | order-preserving shrink (`conn_shrink_scale`) | 保持场解相对秩序，绕面积加权质心按轴缩放到 σ = scale×芯片跨度的紧凑团（模仿中心初始化的几何） |
| 谱初始化 | GiFt init (`gift_init_flag`) | DREAMPlace 自带的图滤波（graph filter）谱嵌入初始化，二次目标的全局解性质 |
| 调度热身 | schedule warm-up | `gamma_warmup_iters`（前 N 迭代把 overflow 视作从 1 线性衰减）、`gamma_monotone_flag`（γ 系数单调包络）、`density_weight_warmup_iters`（推迟 λ 增长） |
| conn-y 缺陷 | conn-y bug | BasicPlace.py 初始化 y 段曾无条件用基准原始 y 覆盖连通性初始化写好的 y（修复提交见 git log "Fix conn-init y-clobber"） |
| 意外变体 | accidental variant | conn-y 缺陷下实际被测的初始化："x = 场分布，y = 基准底行直线"，等效于一种底边点熔化 |
| 底边点熔化 / 熔化点位置 | bottom-edge point melt / melt-point location | 把全部单元置于某指定点（如底边中点）再走标准流程；意外变体的抽象化，(x*, y*) 为待研究旋钮 |
| 几何平均 | geomean | 8 个设计上 (1+Δ) 的几何平均减 1；Δ 为 wHPWL 相对 center 的变化 |
| 竞速门 | race gate | 两个候选初始化各跑到 overflow ≤ 0.4 后按 wHPWL 择优继续的经验判别 |
| 神谕 | oracle | 每设计逐一取已知最优变体的假想组合，作为路由上界 |
| 逐设计路由 | per-design routing | 按设计特征在多个初始化变体间选择 |
| 基准设计 | benchmarks | ISPD2005：adaptec1、adaptec2、adaptec3、adaptec4、bigblue1、bigblue2、bigblue3、bigblue4（文档中一律写全名，不用 a1/b1 等缩写）；ISPD2015：mgc 系列（计划中的盲测集） |
| 填充单元 | filler | 补足面积到目标密度的虚拟单元；只进密度项不进线长项；当前实现均匀随机播种 |
| 熵注入 | entropy injection | 高溢出平台期的内建扰动：整体向质心收缩 ×0.996 + 大幅高斯噪声；仅 overflow>0.95 触发 |
| 发散回滚 | divergence rollback | overflow∈(0.077,0.28) 带内检测发散则回退到最低溢出快照并终止全局布局 |
| 预条件器 | preconditioner | 梯度除以 max(1, 引脚权重和 + λ·单元面积) 的对角缩放 |
| 探针步 | probe step | 初始学习率估计：x₁=x₀−0.01·g₀，α₀=‖Δx‖/‖Δg‖ 的逆 Lipschitz 估计 |
| BB 步长 | Barzilai–Borwein step | `use_bb="auto"`：仅含可动宏的设计（ISPD2005 中只有 bigblue3）启用 |
| 信赖域 | trust region | 对单迭代单元位移施加上限的机制（N6 提案） |
| 调度状态对齐 | schedule state-alignment | 按初始 overflow 查参考轨迹取 γ/λ 入口值（N1 提案） |
| 逆密度播种 | inverse-density filler seeding | 按初始密度图的补集采样播种 filler（N2 提案） |
| 长程重排算子 | long-range reassignment operator | 中溢出里程碑处的粗 bin 成组指派交换（N3 提案） |

## 2. 实验编号（目录名 — 内容一句话）

| 编号 | 目录 | 内容 | 数据有效性 |
|---|---|---|---|
| 实验 0a | `experiments/uniform_init` | 均匀初始化 vs 中心初始化 | 干净（旧 GPU） |
| 实验 0b | `experiments/conn_grid_init` | 连通性场 + 格点吸附 | 原跑=意外变体；修复重跑见实验 R |
| 实验 1 | `experiments/capacity_snap` | 容量展开（组合秩序与低溢出铺开） | 原跑=意外变体；修复后语义由实验 R 的 obsspread 代表 |
| 实验 2 | `experiments/obstacle_field` | 障碍投影场（obsfield / obsspread 两变体） | 原跑=意外变体；修复重跑见实验 R |
| 实验 3 | `experiments/schedule_warmup` | 调度热身（γ/λ 入口修正） | 原跑=意外变体；修复后未重跑，结论悬置 |
| 实验 4 | `experiments/field_gate` | 展开伤害的静态门控证伪 + 种子敏感性 | CPU 探测干净；GPU 部分=意外变体 |
| 实验 5 | `experiments/gift_init` | GiFt 谱初始化 A/B + 质心签名 | 干净 |
| 实验 6 | `experiments/conn_shrink` | 保序收缩（复刻中心初始化几何、保留场秩序） | 原跑=意外变体；修复重跑见实验 R |
| 实验 7 | `experiments/combiner` | 逐设计路由表与神谕口径 | 已按修复后数据重算 |
| 实验 R | `experiments/conn_rebuild` | conn-y 缺陷修复后 conn 系全量重跑（33 运行），修复后权威数据 | 干净 |
| 实验 8（计划） | — | ISPD2015 盲测（全量、路由预注册、零调参） | — |
| 实验 9（计划） | — | 熔化点位置对照（注册预测：adaptec3 底边点熔化应胜修复版连通性场初始化） | — |
| 实验 10 | `experiments/align_filler` | N1 调度状态对齐 × N2 逆密度 filler 播种的 2×2 消融，基座 obsspread（(off,off) 臂复用实验 R） | 干净 |

## 3. 编号系列（均出自 `docs/` 分析文档）

| 系列 | 出处 | 含义 |
|---|---|---|
| M1–M5 | INIT_SENSITIVITY_ANALYSIS | 散开初始化退化的五个机制（M1 排列非凸/排序自由度；M2 λ₀ 归一化导致初始塌落；M3 γ 调度对散开起点失配；M4 超参为中心轨迹调优；M5 无长程修复通道且障碍成壁垒） |
| D1–D5 | INIT_SENSITIVITY_ANALYSIS | 五个改进方向（D1 状态感知调度；D2 障碍感知场；D3 容量约束吸附；D4 中途重熔；D5 诊断）；各自的实验结局已在原文标注 |
| H1、H2 | 实验 2 | H1 障碍错侧假设；H2 场塌缩的障碍成因假设 |
| E1–E7 | ADAPTEC4_DIAGNOSIS | adaptec4 诊断的证据/分析节编号（含后续勘误节） |
| S1–S3 | ADAPTEC4_DIAGNOSIS | 后续实验计划（S1 多种子方差；S2 GiFt 判别；S3 场+重熔）；S1 已并入实验 3/4，S2 即实验 5 |
| P0–P4 | RESULTS_SUMMARY | 修复后下一步优先级（P0 收缩邻域深挖；P1 调度×初始化联合重检；P2 ISPD2015 盲测；P3 bigblue3 展开修复；P4 stop_overflow 稳健性） |
| C1–C5 | MECHANISM_ANALYSIS | 劣化机制论证链（C1 λ₀ 归一化强制重演熔化；C2 γ 瞬时映射过锐；C3 长程错误无修复通道；C4 场系残余损失的两个来源；C5 λ 更新律无阻尼振荡） |
| N1–N6 | MECHANISM_ANALYSIS | 新机制方向（N1 调度状态对齐；N2 逆密度 filler 播种；N3 中途长程重排算子；N4 γ 空间局部化；N5 λ 目标轨迹控制器；N6 单步位移信赖域） |

## 4. 写作规范

- 设计名写全名；变体名用本表第 1 节的中文称呼（首次出现附英文/旗标名）。
- 涉及 conn-y 缺陷前的 GPU 数字时，行文注明"意外变体"；修复后权威数字
  以实验 R 为准。
- 实验 README 按"背景 → 动机 → 方法 → 实现 → 结果与反思"自包含成文，
  不假设读者读过其他文档；交叉引用给出文件路径。
