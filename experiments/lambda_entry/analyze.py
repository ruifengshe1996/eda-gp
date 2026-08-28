#!/usr/bin/env python3
"""Experiment 12 analysis: schedule ENTRY (lambda0) vs RATE (ramp) vs GEOMETRY.

Four arms compared against the same-machine center baseline:
  entry      center init + obsspread's measured lambda0   (this experiment)
  obsspread  spread geometry, lambda0 arises from it      (experiment R)
  ramp1.43   center init, lambda ramp rate x1.43          (experiment 11)
  shrink001  order-preserving shrink                      (experiment R)
"""
import math
import os
import re

GP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DESIGNS = ["adaptec1", "adaptec2", "adaptec3", "adaptec4",
           "bigblue1", "bigblue2", "bigblue3", "bigblue4"]
FINAL = re.compile(r"iteration\s+(\d+), wHPWL (\S+), time")
ITER = re.compile(r"iteration\s+(\d+), \([^)]*\), Obj \S+, DensityWeight (\S+), "
                  r"wHPWL (\S+), Overflow (\S+), MaxDensity (\S+),")

BASE = ("experiments/obstacle_field/logs/center", "{d}_run.log")
ARMS = {
    "entry":     ("experiments/lambda_entry/logs", "{d}.log"),
    "obsspread": ("experiments/conn_rebuild/logs/obsspread", "{d}.log"),
    "ramp1.43":  ("experiments/lambda_ramp/logs/s143", "{d}.log"),
}


def final(path):
    try:
        h = FINAL.findall(open(path).read())
    except FileNotFoundError:
        return None
    return (float(h[-1][1]), int(h[-1][0])) if h else None


def traj(path):
    try:
        r = ITER.findall(open(path).read())
    except FileNotFoundError:
        return None
    return {int(x[0]): (float(x[1]), float(x[3])) for x in r}  # it -> (lambda, ov)


def geomean(v):
    return (math.exp(sum(math.log(1 + x / 100) for x in v) / len(v)) - 1) * 100


def main():
    base = {d: final(os.path.join(GP, BASE[0], BASE[1].format(d=d))) for d in DESIGNS}

    print("=" * 92)
    print("实验 12：λ 入口（λ₀）vs 速率（斜坡）vs 几何（铺开）")
    print("=" * 92)
    print(f"{'design':10}" + "".join(f"{a:>22}" for a in ARMS))
    print(f"{'':10}" + "".join(f"{'wHPWL%   iters  ov@100':>22}" for _ in ARMS))
    cols = {a: {"q": [], "i": []} for a in ARMS}
    ov100 = {a: [] for a in ARMS}
    ov100["center"] = []
    for d in DESIGNS:
        line = f"{d:10}"
        bt = traj(os.path.join(GP, BASE[0], BASE[1].format(d=d)))
        ov100["center"].append(bt.get(100, (0, float('nan')))[1])
        for a, (ld, pat) in ARMS.items():
            r = final(os.path.join(GP, ld, pat.format(d=d)))
            t = traj(os.path.join(GP, ld, pat.format(d=d)))
            if r is None:
                line += f"{'--':>22}"
                continue
            q = (r[0] / base[d][0] - 1) * 100
            it = (r[1] / base[d][1] - 1) * 100
            o = t.get(100, (0, float('nan')))[1]
            cols[a]["q"].append(q)
            cols[a]["i"].append(it)
            ov100[a].append(o)
            line += f"{q:+9.2f}{r[1]:8d}{o:7.3f}"
        print(line)
    print("-" * 92)
    line = f"{'geomean':10}"
    for a in ARMS:
        line += f"{geomean(cols[a]['q']):+9.2f}{geomean(cols[a]['i']):+7.1f}%"
        line += f"{sum(ov100[a]) / len(ov100[a]):7.3f}"
    print(line)
    print(f"{'center':10}{0.0:+9.2f}{0.0:+7.1f}%"
          f"{sum(ov100['center']) / len(ov100['center']):7.3f}")

    e, o, r = (geomean(cols["entry"]["i"]), geomean(cols["obsspread"]["i"]),
               geomean(cols["ramp1.43"]["i"]))
    eq, oq, rq = (geomean(cols["entry"]["q"]), geomean(cols["obsspread"]["q"]),
                  geomean(cols["ramp1.43"]["q"]))
    print("\n" + "-" * 92)
    print("预注册判据")
    print("-" * 92)
    d1 = (1 + e / 100) / (1 + o / 100) - 1
    print(f"E1 迭代数 entry vs obsspread：{e:+.1f}% vs {o:+.1f}%  相对差 "
          f"{d1 * 100:+.1f}%  → {'成立' if abs(d1) <= 0.05 else '不成立'}（阈值 ±5%）")
    print(f"E2 wHPWL entry {eq:+.2f}% vs obsspread {oq:+.2f}%  → "
          f"{'成立' if eq < oq else '不成立'}")
    print(f"E3 入口 vs 速率：entry {eq:+.2f}% @ {e:+.1f}%  |  ramp {rq:+.2f}% @ "
          f"{r:+.1f}%  → 入口{'更贵（预测成立）' if eq > rq else '更便宜（预测不成立）'}")
    a_e = sum(ov100['entry']) / len(ov100['entry'])
    a_c = sum(ov100['center']) / len(ov100['center'])
    print(f"E4 第 100 迭代 overflow：entry {a_e:.3f} vs center {a_c:.3f}  差 "
          f"{a_e - a_c:+.3f}  → 吸引子{'未被打破（成立）' if abs(a_e - a_c) < 0.05 else '被打破（不成立）'}")


if __name__ == "__main__":
    main()
