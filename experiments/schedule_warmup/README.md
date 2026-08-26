# 实验 3：调度热身（D1）试点 + adaptec4 种子方差（S1）

> ⚠ **勘误（2026-08-26）**：本实验全部变体基于 conn-grid 初始化，受
> conn-y 覆盖 bug 影响（`docs/ADAPTEC4_DIAGNOSIS.md` 勘误节，修复
> 434fa96），实际初始态为 x=场、y=底边直线。D1 调度热身的否定结论
> 在被污染初始态上得出，**作废待重做**；下表数字作为该意外变体的
> 成绩仍可复现。S1 种子方差结论(center 系)不受影响。


对应 `docs/INIT_SENSITIVITY_ANALYSIS.md` 的方向 **D1**（状态感知调度）与
`docs/ADAPTEC4_DIAGNOSIS.md` 的后续项 **S1/S3**。所有旋钮在 a80a934 已作为
默认关闭的脚手架提交，本实验零代码改动、纯配置驱动
（`make_configs.py` 生成，`run_warmup.sh` 串行执行并持有 gpu0.lock）。

## 方法

三个热身变体，全部基于 conn-grid 初始化（实验 0 配置 + 调度旋钮）：

- **gmono**：`gamma_monotone_flag=1` —— γ 单调包络，禁止 overflow 反弹时
  回松 γ（隔离 M3"γ 摆动"机制）；
- **warm**：`gamma_warmup_iters=100` + `density_weight_warmup_iters=50` ——
  前 100 迭代把 γ 当作从 overflow=1 衰减（平滑 WL 模型），λ 冻结 50 个
  Llambda 迭代后按当前状态重新归一化（"主动重熔"，重新进入标准同伦）；
- **warmmono**：二者组合。

试点设计 4 个：adaptec1（对照）、adaptec2（场变体离群点）、adaptec4
（对所有非中心初始化免疫）、bigblue3（场塌缩反例）。S1 部分：adaptec4 上
center 与 conn-grid 各加 2 个种子（2000/3000；1000 为既有参照）。

## 结果（相对本机 center 基线；conn-grid 列为实验 2 参照）

| 设计 | conn-grid | gmono | warm | warmmono | GP 迭代 (C/G/W/WM) |
|---|---|---|---|---|---|
| adaptec1 | +0.06% | +0.09% | +0.14% | +0.15% | 611/590/629/626 |
| adaptec2 | +2.04% | +1.70% | **+2.60%** | **+2.78%** | 640/652/644/671 |
| adaptec4 | +3.60% | +3.13% | +3.28% | +3.04% | 715/680/684/712 |
| bigblue3 | +1.15% | **+4.94%** | +1.82% | +1.73% | 995/1069/**1421**/**1539** |

4 设计 geomean：gmono +2.45%、warm +1.95%、warmmono +1.92%
（conn-grid 同 4 设计参照 +1.70%）。全部运行合法。

**S1 种子方差（adaptec4）**：center 三种子 173.62/173.73/173.58（极差
0.09%）；conn-grid 三种子 179.88/179.58/179.68（极差 0.17%）。组间差
+3.53% 为噪声的 20~40 倍——adaptec4 结论统计上坚实，**S1 其余补跑取消**
（判据 σ_a4 ≤ 0.3%，见与会话 50cd98 的协调记录）。

## 发现：D1 方向的干净否定结果

1. **没有任何热身变体在任何设计上明确战胜 plain conn-grid**。唯一的
   改善是 adaptec4 上 0.3~0.6pp（+3.60 → +3.04~3.28），远不足以修复。
   "调度失配（M2/M3）"不是场初始化残余差距的主因——它解释了实验 0 中
   uniform 初始化的部分损失，但对 conn-grid 系已无增量。
2. **gmono 摧毁 bigblue3（+4.94%）**：单调 γ 包络禁止了发散-恢复循环所
   依赖的 γ 回松。M3 所谓的"γ 摆动"在该设计上是必要机制而非缺陷——
   这直接否定了分析文档中"单调包络杀摆动"的 D1 子提案。
3. **warm 在 adaptec2 上是负面的（+2.60/+2.78 vs +2.04）**：重熔阶段的
   再塌缩把场已经做对的部分（相对侧位承诺）重新局部冻结——M2"局部塌缩
   重解序"机制从一个更好的起点复现了它的危害。且 warm 在 bigblue3 上
   迭代数爆炸（1421/1539 vs 995），质量还略差。
4. **adaptec4 修不动**——`docs/ADAPTEC4_DIAGNOSIS.md` E4（修订版）注册
   预测的第二分支成立：conn-grid 种子几何上已是"中心塌缩团 + 已解序"，
   热身又恢复了调度状态，两者都不缺之后仍差 3%，说明 center 的不可替代
   价值在于**质量为一点时的相干整体定位（melt 动力学本身）**，预解的序
   反而是负资产。
5. 程序层面的推论：场初始化损失中"可修复"的部分已被实验 2 的 obsfield
   捕获（错侧修复），剩余部分（adaptec4 型）需要不同机制——不是调度，
   而是长程质量输运/整体定位。下一个判别点是实验 5（GiFt 谱初始化，
   会话 50cd98，S2）：看全局二次解能否复现 melt 的迁移。

## 复现

```bash
python experiments/schedule_warmup/make_configs.py
experiments/schedule_warmup/run_warmup.sh   # 串行 GPU 0，持 gpu0.lock，可断点续跑
python scripts/ab_report.py --a-logs experiments/obstacle_field/logs/center \
  --a-name center \
  --variant "gmono=experiments/schedule_warmup/logs/gmono" \
  --variant "warm=experiments/schedule_warmup/logs/warm" \
  --variant "warmmono=experiments/schedule_warmup/logs/warmmono" \
  --out experiments/schedule_warmup
```

迭代可视化：`viz/{gmono,warm,warmmono}/<design>_all.png`（每设计 10 切片）。
本实验顺带给 `scripts/ab_report.py` 加了缺失日志容忍（部分设计实验可用）。
