# 实验 6：conn-shrink——序内容 vs 轨迹历史的判别实验

对应 `docs/ADAPTEC4_DIAGNOSIS.md` E5b 的判别设计：把连通性场解绕其面积
加权质心整体收缩到 center-init 的几何状态（每轴 σ = `conn_shrink_scale` ×
版图跨度；0.001 与 center 的 `random_center_init` 完全同量级），**保留场的
相对序**，跳过吸附/展开，走完全标准的同伦流程。它复刻 center 熔化结束态
的一切可测属性（紧凑、居中、标准调度），唯独序由场预制——从而分离
"序的内容"与"轨迹历史"两个最后嫌疑。

实现：`ConnectivityGridInit.py` 的 `conn_shrink_scale` 旋钮（本分支引入，
默认 0 关闭），CPU 冒烟验证 σ 精确命中、质心距芯片中心 <0.5%。

## 结果（相对本机 center 基线；参照列取实验 0/2/5）

| 设计 | conn-grid | GiFt | **shrink-001** | shrink-010 | GP 迭代 (C/S1/S10) |
|---|---|---|---|---|---|
| adaptec1 | +0.06% | +0.50% | +0.11% | +0.13% | 611/656/647 |
| adaptec2 | +2.04% | −0.56% | +1.76% | +2.27% | 640/670/652 |
| adaptec4 | +3.60% | +2.46% | **+2.55%** | +2.69% | 715/729/711 |
| bigblue3 | +1.15% | +5.14% | **+0.52%** | +0.88% | 995/1101/1070 |
| bigblue4 | +0.01% | +3.42% | **−0.15%** | −0.05% | 846/933/885 |

5 设计 geomean：shrink-001 **+0.95%**、shrink-010 +1.18%。全部合法。
σ=0.001（忠实复刻 center 紧凑度）在所有设计上不劣于 σ=0.01，后续以
0.001 为准。

## 判决：罪在序的内容，轨迹历史是下游症状

帧质心轨迹（adaptec4，s001）：

| iter | 47 | 141 | 235 | 329 | 517 | 705（收敛） |
|---|---|---|---|---|---|---|
| dy% | **−39.2** | −20.2 | −2.6 | +1.1 | +1.8 | +1.8 |

- **shrink 没有消除暴跌，反而放大了它**（−39.2% vs 未收缩场族的
  −27~−29%、center 的 −3.7%）。几何上与 center-init 无差别的紧凑居中团，
  只因内部序不同，WL 段的走向就完全不同：场序让互联簇**相干地**跌向
  各自的锚吸引盆；center 的随机序对称跌落、质量保持平衡。
  E5b 的两个嫌疑就此合并：**暴跌与钉死都是序内容的表达**，
  "轨迹历史"不是独立原因。
- 恢复后仅迁移到 +1.8%（center 全程 +5.5~6），最终 +2.55%——与 GiFt 的
  +2.46% 几乎重合：**去掉吸附/展开/几何因素后，Jacobi 序与谱序在
  adaptec4 上的内在质量代价趋同（~+2.5%）**，这是"序质量谱"的又一个
  定量点位。adaptec4 至今无非中心初始化能破 +2.4%。
- **bigblue4 −0.15%：项目第二个胜过 center 的数据点**（第一个是 GiFt 在
  adaptec2 的 −0.56%），且质心尾迹 −6.7% 表明它完成了该设计"正确方向"
  （锚几何决定，b4 朝下）的全程迁移——"完成迁移 ⇔ 小劣势/反超"的
  符号化版本继续成立。
- **bigblue3 +0.52%：历来最佳非中心结果**（conn-grid +1.15、cap-spread
  +20.7、GiFt +5.14）。塌缩场网表的正确处理方式不是展开也不是全局谱解，
  而是"保序收缩 + 标准熔化"——实验 1 遗留问题的目前最优答案。
- adaptec2 +1.76%：收缩丢掉了吸附/障碍处理挽回的部分（obsfield +0.49、
  GiFt −0.56 仍是该设计最优）——序的"错侧"缺陷收缩救不了，符合判决。

## 程序含义

六个实验后的全景：场类初始化的损失分解为三个独立成分——**错侧**
（obsfield/GiFt 可修，adaptec2）、**几何/展开**（shrink 可修，bigblue3/4）、
**序内在质量**（adaptec4 型，现有所有序生成器同罪 ~+2.5%，唯 center 的
"随机序 + 对称熔化"免疫）。下一步最有价值的方向：
1. **per-design 组合器**：obsfield / GiFt / shrink 三者在 8 设计上各有
   胜场，简单的静态特征（E4 锚几何 + 场塌缩度）可能足以路由——
   目标 geomean < +0.3% 且全面省迭代；
2. **序质量的根因**（研究向）：为什么随机序熔化不跌、任何预制序都跌？
   刻画"序→WL 段跌落方向场"的映射，寻找"抗跌序"的构造原理；
3. 50cd98 提议的谱全局 + Jacobi 局部混合场，作为 2 的实验载体。

## 复现

```bash
python experiments/conn_shrink/make_configs.py
experiments/conn_shrink/run_all.sh   # 持 gpu0.lock 串行
python scripts/ab_report.py --a-logs experiments/obstacle_field/logs/center \
  --a-name center \
  --variant "shrink-001=experiments/conn_shrink/logs/s001" \
  --variant "shrink-010=experiments/conn_shrink/logs/s010" \
  --out experiments/conn_shrink
```

迭代可视化：`viz/{s001,s010}/<design>_all.png`。
