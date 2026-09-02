#!/usr/bin/env python3
"""Experiment 13 analysis: the per-net gamma sign test.

Quality is reported the way experiment 11 requires -- as a residual to each
design's own lambda-ramp frontier, i.e. against a center run forced to spend
the same number of iterations. A raw delta vs the baseline would re-introduce
the iteration-count confound.
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
# the exp-11 ramp arms define the equal-iteration reference curve
RAMP = [("experiments/lambda_ramp/logs/s070", "{d}.log"),
        (None, None),  # s=1.0 is the baseline itself
        ("experiments/lambda_ramp/logs/s143", "{d}.log"),
        ("experiments/lambda_ramp/logs/s200", "{d}.log")]
# phase 1 preserved the mean per-net OVERFLOW (gamma's mean then drifts up by
# Jensen); phase 2 preserves the mean GAMMA, isolating locality itself
ARMS = {"gneg": "experiments/gamma_local/logs/gneg",
        "gpos": "experiments/gamma_local/logs/gpos",
        "nneg": "experiments/gamma_local/logs/nneg",
        "npos": "experiments/gamma_local/logs/npos",
        # phase 3 placebo: npos's gamma multiset permuted randomly across nets
        "nshuf": "experiments/gamma_local/logs/nshuf"}
ARMS = {k: v for k, v in ARMS.items()
        if os.path.isdir(os.path.join(GP, v))}


def final(p):
    try:
        h = FINAL.findall(open(p).read())
    except FileNotFoundError:
        return None
    return (float(h[-1][1]), int(h[-1][0])) if h else None


def ov_at(p, it):
    try:
        m = {int(x[0]): float(x[3]) for x in ITER.findall(open(p).read())}
    except FileNotFoundError:
        return None
    return m.get(it)


def geomean(v):
    return (math.exp(sum(math.log(1 + x / 100) for x in v) / len(v)) - 1) * 100


def interp(curve, x):
    xs = [p[0] for p in curve]
    if x <= xs[0]:
        (x0, y0), (x1, y1) = curve[0], curve[1]
    elif x >= xs[-1]:
        (x0, y0), (x1, y1) = curve[-2], curve[-1]
    else:
        i = max(j for j in range(len(curve) - 1) if curve[j][0] <= x)
        (x0, y0), (x1, y1) = curve[i], curve[i + 1]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0)


def main():
    base = {d: final(os.path.join(GP, BASE[0], BASE[1].format(d=d))) for d in DESIGNS}
    base_ov = {d: ov_at(os.path.join(GP, BASE[0], BASE[1].format(d=d)), 100)
               for d in DESIGNS}

    print("=" * 96)
    print("实验 13：逐网线 γ 的符号判据（G2 杠杆 / G3 镜像 / G4 去混杂质量）")
    print("=" * 96)
    print(f"{'design':10}{'ov@100 base':>12}"
          + "".join(f"{a + ' ov@100':>14}{a + ' Δov':>12}" for a in ARMS))
    dov = {a: [] for a in ARMS}
    for d in DESIGNS:
        line = f"{d:10}{base_ov[d]:12.3f}"
        for a, ld in ARMS.items():
            o = ov_at(os.path.join(GP, ld, f"{d}.log"), 100)
            if o is None:
                line += f"{'--':>14}{'--':>12}"
                continue
            dov[a].append(o - base_ov[d])
            line += f"{o:14.3f}{o - base_ov[d]:+12.3f}"
        print(line)
    print("-" * 96)
    line = f"{'mean':10}{'':>12}"
    for a in ARMS:
        line += f"{'':>14}{sum(dov[a]) / len(dov[a]) if dov[a] else float('nan'):+12.3f}"
    print(line)

    # G2 / G3
    print("\n" + "-" * 96)
    print("G2/G3 判据")
    print("-" * 96)
    for a in ARMS:
        big = sum(1 for x in dov[a] if abs(x) > 0.03)
        print(f"  {a}: |Δov@100| > 0.03 的设计数 = {big}/8, 平均 Δ = "
              f"{sum(dov[a]) / len(dov[a]):+.3f}" if dov[a] else f"  {a}: 无数据")
    if dov.get("nshuf") and dov.get("npos"):
        ms = sum(dov["nshuf"]) / len(dov["nshuf"])
        mp = sum(dov["npos"]) / len(dov["npos"])
        print(f"  P1 安慰剂 Δov@100：nshuf {ms:+.3f} vs npos {mp:+.3f}, 差 {ms - mp:+.3f}"
              f"（阈值 ±0.03 → {'成立' if abs(ms - mp) <= 0.03 else '不成立'}）")
    for pos, neg, tag in (("gpos", "gneg", "G3 阶段1"), ("npos", "nneg", "H2 阶段2")):
        if dov.get(pos) and dov.get(neg):
            n_lower = sum(1 for p, n in zip(dov[pos], dov[neg]) if n < p)
            mp = sum(dov[pos]) / len(dov[pos])
            mn = sum(dov[neg]) / len(dov[neg])
            print(f"  {tag}: {neg} 的 ov@100 低于 {pos} 的设计数 = {n_lower}/8; "
                  f"平均偏移 {pos} {mp:+.3f} vs {neg} {mn:+.3f}, 差 {mn - mp:+.3f}")

    # G4: residual to the ramp frontier
    print("\n" + "-" * 96)
    print("G4 去混杂质量：到本设计斜坡前沿的残差（负 = 优于等迭代数的 center）")
    print("-" * 96)
    print(f"{'design':10}" + "".join(f"{a + ' wHPWL%':>13}{a + ' iters':>12}"
                                     f"{a + ' 残差':>12}" for a in ARMS))
    resid = {a: [] for a in ARMS}
    for d in DESIGNS:
        curve = []
        for ld, pat in RAMP:
            r = base[d] if ld is None else final(os.path.join(GP, ld, pat.format(d=d)))
            if r is None:
                continue
            curve.append(((r[1] / base[d][1] - 1) * 100,
                          (r[0] / base[d][0] - 1) * 100))
        curve.sort()
        line = f"{d:10}"
        for a, ld in ARMS.items():
            r = final(os.path.join(GP, ld, f"{d}.log"))
            if r is None or len(curve) < 2:
                line += f"{'--':>13}{'--':>12}{'--':>12}"
                continue
            q = (r[0] / base[d][0] - 1) * 100
            it = (r[1] / base[d][1] - 1) * 100
            res = q - interp(curve, it)
            resid[a].append(res)
            line += f"{q:+13.2f}{r[1]:12d}{res:+12.2f}"
        print(line)
    print("-" * 96)
    line = f"{'geomean':10}"
    for a in ARMS:
        if resid[a]:
            line += f"{'':>13}{'':>12}{geomean(resid[a]):+12.2f}"
        else:
            line += f"{'':>13}{'':>12}{'--':>12}"
    print(line)
    print("\n  判据：残差 < −0.5pp ⇒ 本项目第一个真正战胜等迭代数 center 的机制。")
    if resid.get("nshuf") and resid.get("npos"):
        gs, gp = geomean(resid["nshuf"]), geomean(resid["npos"])
        print(f"  P1 安慰剂残差：nshuf {gs:+.2f} vs npos {gp:+.2f}, 差 {gs - gp:+.2f}pp"
              f"（阈值 ±1.0pp → {'成立：损害由 γ 离散度驱动，与空间结构无关' if abs(gs - gp) <= 1.0 else '不成立：空间结构携带价值'}）")


if __name__ == "__main__":
    main()
