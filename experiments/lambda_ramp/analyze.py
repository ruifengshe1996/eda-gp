#!/usr/bin/env python3
"""Experiment 11 analysis: the lambda-ramp frontier and the de-confounded
initialization effect.

For every design we have four points on a curve that holds initialization fixed
(center) and moves only the lambda ramp rate: s = 0.70 / 1.00 / 1.43 / 2.00.
That curve is the honest control for "init X saves N% iterations".

The de-confounded effect of an init variant on a design is its vertical
residual to that curve: the quality it delivers minus the quality plain center
init delivers when forced (by the ramp knob) to spend the same number of
iterations. Positive residual = the variant is worse than just ramping.
"""
import math
import os
import re

GP = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HERE = os.path.dirname(os.path.abspath(__file__))
DESIGNS = ["adaptec1", "adaptec2", "adaptec3", "adaptec4",
           "bigblue1", "bigblue2", "bigblue3", "bigblue4"]
FINAL_RE = re.compile(r"iteration\s+(\d+), wHPWL (\S+), time")

BASE = ("experiments/obstacle_field/logs/center", "{d}_run.log")
# ramp arms: label -> (scale, logdir)
ARMS = [("s070", 0.70, "experiments/lambda_ramp/logs/s070"),
        ("base", 1.00, None),  # reuses BASE
        ("s143", 1.43, "experiments/lambda_ramp/logs/s143"),
        ("s200", 2.00, "experiments/lambda_ramp/logs/s200")]
# init variants to de-confound (same sources as experiments/combiner/make_table.py)
VARIANTS = {
    "conn-grid": ("experiments/conn_rebuild/logs/conngrid", "{d}.log"),
    "obsfield":  ("experiments/conn_rebuild/logs/obsfield", "{d}.log"),
    "obsspread": ("experiments/conn_rebuild/logs/obsspread", "{d}.log"),
    "gift":      ("experiments/gift_init/logs", "{d}.log"),
    "shrink001": ("experiments/conn_rebuild/logs/shrink001", "{d}.log"),
}


DIVERGE_RE = re.compile(r"Divergence detected")
ILLEGAL_RE = re.compile(r"legal flag = 0")


def parse(path):
    """Return (final wHPWL, GP iterations) or None."""
    try:
        with open(path) as f:
            hits = FINAL_RE.findall(f.read())
    except FileNotFoundError:
        return None
    return (float(hits[-1][1]), int(hits[-1][0])) if hits else None


def health(path):
    """Flags that would make an iteration count dishonest: a divergence
    rollback ends GP early, and an illegal result is not comparable at all."""
    try:
        with open(path) as f:
            txt = f.read()
    except FileNotFoundError:
        return ""
    return ("D" if DIVERGE_RE.search(txt) else "") + ("!" if ILLEGAL_RE.search(txt) else "")


def geomean(vals):
    return (math.exp(sum(math.log(1 + v / 100) for v in vals) / len(vals)) - 1) * 100


def interp(curve, x):
    """Piecewise-linear interpolation of the ramp curve at iteration-delta x.

    curve: list of (iter_delta%, wHPWL_delta%) sorted by iter_delta.
    Outside the measured range we extrapolate from the nearest segment and flag
    it, so an extrapolated residual is never silently reported as measured.
    """
    xs = [p[0] for p in curve]
    extrap = not (xs[0] <= x <= xs[-1])
    if x <= xs[0]:
        (x0, y0), (x1, y1) = curve[0], curve[1]
    elif x >= xs[-1]:
        (x0, y0), (x1, y1) = curve[-2], curve[-1]
    else:
        i = max(j for j in range(len(curve) - 1) if curve[j][0] <= x)
        (x0, y0), (x1, y1) = curve[i], curve[i + 1]
    return y0 + (y1 - y0) * (x - x0) / (x1 - x0), extrap


def main():
    base = {d: parse(os.path.join(GP, BASE[0], BASE[1].format(d=d))) for d in DESIGNS}
    missing = [d for d, v in base.items() if v is None]
    if missing:
        raise SystemExit(f"missing center baseline for {missing}")

    # ---- ramp arms -------------------------------------------------------
    arm_rows = {}   # label -> design -> (wHPWL delta%, iters, iter delta%)
    flags = {}      # (label, design) -> health flags
    for label, _scale, logdir in ARMS:
        rows = {}
        for d in DESIGNS:
            path = (os.path.join(GP, BASE[0], BASE[1].format(d=d)) if logdir is None
                    else os.path.join(GP, logdir, f"{d}.log"))
            r = parse(path)
            if r is None:
                continue
            hp, it = r
            bhp, bit = base[d]
            rows[d] = ((hp / bhp - 1) * 100, it, (it / bit - 1) * 100)
            flags[(label, d)] = health(path)
        arm_rows[label] = rows

    print("=" * 78)
    print("实验 11：λ 斜坡率前沿（center 初始化固定，只改斜坡）")
    print("=" * 78)
    hdr = f"{'design':10}" + "".join(f"{l:>17}" for l, _, _ in ARMS)
    print(hdr)
    print(f"{'':10}" + "".join(f"{'wHPWL%  iters':>17}" for _ in ARMS))
    for d in DESIGNS:
        line = f"{d:10}"
        for label, _, _ in ARMS:
            r = arm_rows[label].get(d)
            if r is None:
                line += f"{'      --      ':>17}"
            else:
                line += f"{r[0]:+8.2f}{r[1]:7d}{flags.get((label, d), ''):<2}"
        print(line)
    bad = sorted(k for k, v in flags.items() if v)
    if bad:
        print("\n  健康标记：D = 触发发散回滚（迭代数因提前终止而不可比），"
              "! = 合法性检查失败")
        for label, d in bad:
            print(f"    {label}/{d}: {flags[(label, d)]}")
    line = f"{'geomean':10}"
    curve_pts = []
    for label, scale, _ in ARMS:
        rows = arm_rows[label]
        if len(rows) < len(DESIGNS):
            line += f"{'  (incomplete) ':>17}"
            continue
        gq = geomean([v[0] for v in rows.values()])
        gi = geomean([v[2] for v in rows.values()])
        curve_pts.append((label, scale, gi, gq))
        line += f"{gq:+8.2f}{gi:+7.1f}% "
    print(line)
    print(f"{'':10}" + "  （下行为迭代数几何平均变化）")

    if len(curve_pts) < len(ARMS):
        print("\n[未完成] 部分臂缺少运行，前沿与残差待全部完成后计算。")
        return

    # ---- R2: does the ramp dominate the init variants? -------------------
    print("\n" + "-" * 78)
    print("R2 主判据：同等迭代节省下，λ 斜坡 vs 铺开系初始化")
    print("-" * 78)
    for label, scale, gi, gq in curve_pts:
        print(f"  s={scale:<5} 迭代 {gi:+6.1f}%   wHPWL {gq:+6.2f}%")
    print("  参照 obsspread  迭代  -26.0%   wHPWL  +1.82%")
    print("  参照 GiFt       迭代  -30.0%   wHPWL  +1.86%")

    # ---- R3: de-confounded init effect (per design) ----------------------
    print("\n" + "-" * 78)
    print("R3 去混杂的初始化效应：各变体到本设计斜坡曲线的垂直残差")
    print("（正 = 比「单纯把 λ 斜坡调到同样迭代数」更差；* = 曲线外插）")
    print("-" * 78)
    print(f"{'design':10}" + "".join(f"{n:>12}" for n in VARIANTS))
    resid = {n: [] for n in VARIANTS}
    for d in DESIGNS:
        curve = sorted((arm_rows[l][d][2], arm_rows[l][d][0]) for l, _, _ in ARMS)
        line = f"{d:10}"
        for name, (logdir, pat) in VARIANTS.items():
            r = parse(os.path.join(GP, logdir, pat.format(d=d)))
            if r is None:
                line += f"{'--':>12}"
                continue
            hp, it = r
            bhp, bit = base[d]
            q, idelta = (hp / bhp - 1) * 100, (it / bit - 1) * 100
            pred, ex = interp(curve, idelta)
            resid[name].append(q - pred)
            line += f"{q - pred:+11.2f}{'*' if ex else ' '}"
        print(line)
    line = f"{'geomean':10}"
    for name in VARIANTS:
        line += f"{geomean(resid[name]):+11.2f} " if resid[name] else f"{'--':>12}"
    print(line)
    print("\n  判据：|残差| < 0.5pp（本项目种子噪声上限）⇒ 该变体相对"
          "「等迭代数的 center」无可测效应。")

    # ---- plot ------------------------------------------------------------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    # NOTE: no CJK font is installed on this machine, so all figure text is
    # English on purpose; the prose analysis above and the README stay Chinese.
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    xs = [p[2] for p in curve_pts]
    ys = [p[3] for p in curve_pts]
    ax.plot(xs, ys, "o-", color="#1f77b4", lw=2, ms=7,
            label="center init, lambda ramp swept (exp 11)")
    for label, scale, gi, gq in curve_pts:
        ax.annotate(f"s={scale}", (gi, gq), textcoords="offset points",
                    xytext=(6, 6), fontsize=9, color="#1f77b4")
    vgeo = {}
    for name, (logdir, pat) in VARIANTS.items():
        qs, its = [], []
        for d in DESIGNS:
            r = parse(os.path.join(GP, logdir, pat.format(d=d)))
            if r is None:
                continue
            bhp, bit = base[d]
            qs.append((r[0] / bhp - 1) * 100)
            its.append((r[1] / bit - 1) * 100)
        if len(qs) == len(DESIGNS):
            vgeo[name] = (geomean(its), geomean(qs))
    for name, (gi, gq) in vgeo.items():
        ax.plot(gi, gq, "s", ms=8, color="#d62728")
        ax.annotate(name, (gi, gq), textcoords="offset points",
                    xytext=(6, -12), fontsize=9, color="#d62728")
    ax.axhline(0, color="k", lw=0.8, ls=":")
    ax.axvline(0, color="k", lw=0.8, ls=":")
    ax.set_xlabel("GP iterations vs center baseline (%, geomean)")
    ax.set_ylabel("wHPWL vs center baseline (%, geomean)")
    ax.set_title("Exp 11: lambda-ramp frontier vs init variants (ISPD2005, n=8)")
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(alpha=0.3)
    out = os.path.join(HERE, "viz", "frontier.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
