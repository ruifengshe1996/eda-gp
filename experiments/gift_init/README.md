# 实验 5:GiFt 谱初始化 A/B(S2 判别)

分支延续 `dev_field_gate` 系列,承接 `docs/ADAPTEC4_DIAGNOSIS.md` 的 S2 判别:
GiFt(ICCAD'24,仓库自带 `gift_init_flag`,graph-filter 谱嵌入)是二次目标的
**全局解**,与 Jacobi 局部松弛(conn-grid 系)形成机制对照。判别逻辑:
GiFt 也 +3.5% ⇒ 二次目标本身是错误来源;GiFt 修复 ⇒ Jacobi 欠收敛。
每设计跑完自动记录最终可动质心(`scripts/movable_centroid.py`),检验
E4/E5 的锚点拖拽与迁移机制预测。

## 配置

center 默认配置 + `gift_init_flag: 1`(`gift_init_scale` 默认 0.7),
单种子(4B 已证明种子极差 0.1-0.4pp,±0.5pp 以上声称安全),plot 间隔
沿用 conn-grid 配置。center 基线复用 `experiments/obstacle_field/logs/center`
(同机)。判别设计优先的运行顺序:a4 → a2 → b3 → a1 → 其余。

## 结果(相对本机 center 基线)

| 设计 | center | gift wHPWL | delta | GP iters (C/G) | 最终质心 dy(%h) |
|---|---|---|---|---|---|
| adaptec1 | 72.81 | 73.17 | +0.50% | 611/421 | +1.8 |
| adaptec2 | 81.96 | 81.50 | **−0.56%** | 640/426 | −1.9 |
| adaptec3 | 193.05 | 194.20 | +0.59% | 679/451 | −4.7 |
| adaptec4 | 173.62 | 177.89 | **+2.46%** | 715/471 | **+3.4** |
| bigblue1 | 89.26 | 89.56 | +0.33% | 677/448 | +6.0 |
| bigblue2 | 136.92 | 141.23 | +3.15% | 664/469 | +1.7 |
| bigblue3 | 304.23 | 319.85 | +5.14% | 995/956 | +2.8 |
| bigblue4 | 742.60 | 768.00 | +3.42% | 846/563 | −5.0 |

geomean **+1.86%**(conn-grid +0.95%,obsfield +0.79%,uniform +2.10%);
GP 迭代 −25~−34%(bigblue3 除外)。全部合法。

## 发现

- **S2 判别结果:分级中间态,两个假设都不完整。** adaptec4 上 GiFt +2.46%,
  介于场族(+3.1~3.6%)与 center(0)之间;最终质心 +3.4% h,恰为场族
  (~0%)与 melt(+6.5%)之半。二次目标本身贡献了部分差距(其全局解仍
  劣 2.46%),但不是全部——序质量呈**连续谱**:熔化序 > 谱序 > Jacobi
  局部序,携带的定向迁移力同序。
- **e0 的帧轨迹分析**(用本实验 plot 帧,方法同 E5b;详见
  `docs/ADAPTEC4_DIAGNOSIS.md`):GiFt 的 WL 塌缩瞬态几乎消失(dy 最低
  −0.5%,对比 Jacobi 场族 −27~−29%、center −3.7%),爬坡段迁移完成约一半
  (−0.5→+3.0,center 为 0→+5.5)。三族剂量-响应:跌落幅度与后续钉死
  强相关——跌落大小本身可能就是序质量的症状(坏序=长网=远距拉拽=大跌落
  =途中重冻),(a) 序内容与 (b) 轨迹历史并非二选一。实验 6(conn-shrink)
  仍是干净判别。
- **adaptec2 里程碑:GiFt −0.56% 反超 center,且省 33% 迭代。** a2 全排序:
  obsspread −0.81% < GiFt −0.56% < obsfield +0.49% < center 0 <
  conn-grid +2.04%——"胜过 center"在 a2 上已有两例(两条独立路线:容量
  展开与谱嵌入),GiFt 的独特价值是同时给出迭代节省与机制判别地位;
  谱嵌入天然绕开 Jacobi 场的宏障碍错侧问题,与实验 2(obsfield 修复
  adaptec2)互为 D2 的独立铁证。
- **失败侧同样有信息**:bigblue2 +3.15%(conn-grid 仅 +0.85%)与 bigblue3
  +5.14%(conn-grid +1.15%)说明谱全局解在部分净表上排序**劣于** Jacobi
  局部松弛——GiFt 与 conn-grid 的每设计胜负交错(a2/a4 GiFt 优,
  b2/b3/b4-quality conn-grid 优),没有一致的支配关系;初始化质量是
  设计依赖的,提示 per-design 选择或混合(谱做全局、Jacobi 做局部精修)
  是下一层机会。
- 质心侧记:bigblue1 的 GiFt 质心 +6.0%(完整 melt 式上迁)且仅 +0.33%;
  bigblue4 −5.0% 且 +3.42%——"完成上迁 ⇔ 小劣势"的相关性在 8 设计上
  继续成立(a3 是温和例外:−4.7% 但仅 +0.59%,其固定锚质心本就偏上,
  方向意义与 a4 相反,与 E4 的锚几何逐设计符号预测一致)。

## 复现

```bash
experiments/gift_init/run_all.sh   # flock gpu0.lock,判别设计优先,可断点续跑
python scripts/ab_report.py --a-logs experiments/obstacle_field/logs/center \
  --variant "gift=experiments/gift_init/logs" --out experiments/gift_init
python scripts/select_viz_slices.py --src install/gift_results --dst experiments/gift_init/viz
python scripts/make_montage.py experiments/gift_init/viz
```

迭代过程:`viz/<design>_all.png`;最终质心:`logs/centroids.txt`。
