# 实验 7:per-design 初始化组合器(路由表 + 神谕上限)

> **⚠️ 数据污染标注(2026-08-26,conn-y 初始化 bug)**:BasicPlace.py 的
> y 段覆盖 bug(实验 0 起即存在,修复分支 dev_fix_conn_y)使 conn 系全部
> GPU 运行(conn-grid / cap-spread / obsfield / obsspread / shrink001 列)
> 实测的是"x=场分布、y=底边直线"的意外变体。**表中数字作为该意外变体的
> 成绩仍然有效**(组合器测什么得什么),但其机制语义不成立;center 与
> gift 列不受影响。路由表与规则链冻结暂缓,待修复后的核心 32 重跑
> (asus 主责)落地后用 `make_table.py` 重算。


三方分工(见 `docs/ADAPTEC4_DIAGNOSIS.md` E6 结案后的队列):本实验(cf)
出完整路由表与组合器口径;asus 做路由信号离线回测;e0 做序→跌落机制
刻画与动力学探针。组合结果**零新增 GPU 运行**——所有变体均为同机、同种子
(deterministic, seed 1000)的已入库运行,组合即逐设计引用。

## 数据补齐

实验 6 的 shrink-001 缺 {a3,b1,b2},本实验按 e0 的配置协议补跑
(σ=0.001,其在全部五个已测设计上占优;`experiments/conn_shrink/configs/
{adaptec3,bigblue1,bigblue2}_s001.json`,日志在 `logs/`):
a3 +0.38%(719 it)、**b1 −0.06%**(716 it,又一反超)、b2 +0.41%(701 it)。

## 完整路由表(wHPWL delta vs 同机 center;粗体 = 每行最优)

| 设计 | conn-grid | cap-spread | obsfield | obsspread | gift | shrink001 |
|---|---|---|---|---|---|---|
| adaptec1 | +0.06% | **−0.08%** | +0.06% | **−0.08%** | +0.50% | +0.11% |
| adaptec2 | +2.04% | **−0.89%** | +0.49% | −0.81% | −0.56% | +1.76% |
| adaptec3 | **+0.05%** | +1.09% | +0.26% | +0.37% | +0.59% | +0.38% |
| adaptec4 | +3.60% | +3.09% | +3.59% | +3.46% | **+2.46%** | +2.55% |
| bigblue1 | −0.13% | +0.22% | **−0.17%** | +0.20% | +0.33% | −0.06% |
| bigblue2 | +0.85% | +0.35% | +0.93% | **+0.32%** | +3.15% | +0.41% |
| bigblue3 | +1.15% | +20.70% | +0.91% | +20.89% | +5.14% | **+0.52%** |
| bigblue4 | +0.01% | +3.50% | +0.31% | +4.10% | +3.42% | **−0.15%** |

单一策略基线:shrink001 +0.69%(8 设计补齐后)、obsfield +0.79%、
conn-grid +0.95%、gift +1.86%、uniform +2.10%、cap-spread +3.30%、
obsspread +3.35%。(由 `make_table.py` 自动再生,见 `routing_table.md`。)

## 组合器口径

| 口径 | geomean | 说明 |
|---|---|---|
| oracle-always(全 6 变体) | **+0.25%** | 每设计取最优非中心变体 |
| oracle-always(set4:obsf/obss/gift/shrink) | +0.29% | asus 提议的精简选集 |
| **oracle-or-center**(center 入选集) | **−0.16%** | 无变体胜出则回退 center |

oracle-or-center 的路由:a1 cap(−23% it)、a2 cap(−13% it)、b1 obsf、
b4 shrink(+10% it),其余 center——**整体反超 center 0.16%,且 a1/a2 附带
13-23% 迭代节省**。反超 center 的设计已达 4/8:a1(cap/obss)、
a2(cap/obss/gift)、b1(obsf/shrink)、b4(shrink)。

上限的结构:a4 的 +2.46% 地板(E6:预制序内在质量)是 oracle-always 转正
的唯一主因;若 a4 被解决,全表 oracle-always ≈ −0.05%。

## 路由信号(asus 回测,终版)

**冻结候选规则链**(补齐数据代入后):

```
snap 膨胀比 > 7                     → shrink001
elif fp_dy < −0.02 且 util < 0.3    → center      # a4 型序地板:正确路由是"不用预制序"
elif |fp 质心| > 0.15               → obsfield
else                                → obsspread
```

回测 geomean **+0.000%(与 center 整体持平)**;路由明细:a1 obss −0.08 /
a2 obss −0.81 / a3 shrink +0.38 / a4 **center 0** / b1 obsf −0.17 /
b2 obss +0.32 / b3 shrink +0.52 / b4 shrink −0.15。距 oracle-or-center
(−0.15~−0.16%)的 0.15pp 差距全部来自 a3/b2/b3——"全变体皆负但幅度小"
的设计,静态信号无法分离;e0 探针若能预测"无增益设计"可吃掉这部分。
utilization 用 center 日志真值(a1 0.573 / a2 0.443 / a3 0.335 /
a4 0.271 / b1 0.447 / b2 0.378 / b3 0.561 / b4 0.443)。

**三条告警**(asus,须随任何声称一并引用):(1) n=8 拟 3 阈值,过拟合
风险极高;(2) 边际极薄——a1 的 fp_dy −0.021 距 −0.02 阈值仅 0.001(靠
util 分支挡住),snap>7 处 a4 6.86 / a3 7.64 / b3 7.81 相挤;(3) 这条链的
可信度**完全取决于 ISPD2015 盲测**(实验 8:2005 冻结规则——链 or 探针
二选一等 e0 结果,2015 零调参;主指标 geomean + 逐设计不劣于 center 比例)。
ISPD2015 基准已就位(`dreamplace-src/benchmarks/ispd2015/`)。

动力学探针(e0,进行中):用 DREAMPlace CPU 路径跑 60 迭代真实
WA+Nesterov 流、以质心漂移为"跌落风险"度量(每设计-初始化 5-10min 纯
CPU)。E6 后续帧分析两发现支撑此路线:跌落轨迹与初始几何无关(warm 与
shrink 逐点重合)、深跌更像动量+WA 梯度的相干失稳而非锚方向拉拽(b3 锚
居中仍深跌 −38.7%)。若探针在 a4 复现 −3 vs −35 分离,路由升级为
"先算场 → 60 迭代探针 → 按漂移选初始化",绕开全部静态信号告警。

## 复现

```bash
# 数据补齐(3 运行,flock gpu0.lock)
experiments/combiner/run_completion.sh
# 口径计算:README 表格由 scripts/ab_report.py 各实验 metrics + 本文件手工汇总
```
