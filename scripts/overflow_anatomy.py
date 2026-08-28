#!/usr/bin/env python3
"""Overflow-only anatomy of every post-fix variant.

The project's quality metric has always been wHPWL. This probe ignores it
entirely and asks what the *density* side of the run actually does:

  ov0        overflow at iteration 0 (what the initialization handed over)
  ov_min_e   lowest overflow reached in the first 100 iterations
  ov_peak    highest overflow reached after iteration 0 (the rebound), and when
  rebound    ov_peak - ov0  (how much of the pre-spread head start was undone)
  it@0.4/0.2/0.1  first iteration crossing each milestone
  ov_end     overflow at the last GP iteration
  maxd_end   MaxDensity at the last GP iteration (bin-level legality, which the
             scalar overflow average hides)

Usage: overflow_anatomy.py [--designs a,b,...]
"""
import argparse
import math
import os
import re

GP = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DESIGNS = ["adaptec1", "adaptec2", "adaptec3", "adaptec4",
           "bigblue1", "bigblue2", "bigblue3", "bigblue4"]

ITER_RE = re.compile(
    r"iteration\s+(\d+), \([^)]*\), Obj \S+, DensityWeight (\S+), "
    r"wHPWL (\S+), Overflow (\S+), MaxDensity (\S+), gamma ([0-9.Ee+-]+)")

VARIANTS = {
    "center":    ("experiments/obstacle_field/logs/center", "{d}_run.log"),
    "conn-grid": ("experiments/conn_rebuild/logs/conngrid", "{d}.log"),
    "obsfield":  ("experiments/conn_rebuild/logs/obsfield", "{d}.log"),
    "obsspread": ("experiments/conn_rebuild/logs/obsspread", "{d}.log"),
    "shrink001": ("experiments/conn_rebuild/logs/shrink001", "{d}.log"),
    "gift":      ("experiments/gift_init/logs", "{d}.log"),
    "ramp1.43":  ("experiments/lambda_ramp/logs/s143", "{d}.log"),
}


def parse(path):
    """Return list of (iter, lambda, wHPWL, overflow, maxdensity, gamma).

    Designs with movable macros run two global-placement stages; the iteration
    counter is continuous across them, so the raw list is the whole run.
    """
    try:
        with open(path) as f:
            txt = f.read()
    except FileNotFoundError:
        return None
    rows = [(int(m[0]), float(m[1]), float(m[2]), float(m[3]),
             float(m[4]), float(m[5])) for m in ITER_RE.findall(txt)]
    return rows or None


def milestone(rows, thr):
    for r in rows:
        if r[3] <= thr:
            return r[0]
    return None


def anatomy(rows):
    ov = [r[3] for r in rows]
    ov0 = ov[0]
    early = ov[:100] if len(ov) > 100 else ov
    peak_i = max(range(1, len(ov)), key=lambda i: ov[i]) if len(ov) > 1 else 0
    return {
        "ov0": ov0,
        "ov_min_e": min(early),
        "ov_peak": ov[peak_i],
        "peak_at": rows[peak_i][0],
        "rebound": ov[peak_i] - ov0,
        "m40": milestone(rows, 0.40),
        "m20": milestone(rows, 0.20),
        "m10": milestone(rows, 0.10),
        "ov_end": ov[-1],
        "maxd_end": rows[-1][4],
        "iters": rows[-1][0],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--designs", default=",".join(DESIGNS))
    args = ap.parse_args()
    designs = args.designs.split(",")

    print("=" * 108)
    print("overflow 解剖：初始化交付的低溢出起点，会被前期动力学还回去多少？")
    print("=" * 108)
    hdr = (f"{'design':10}{'variant':11}{'ov0':>7}{'ov_min':>8}{'ov_peak':>9}"
           f"{'@it':>6}{'rebound':>9}{'it@.4':>7}{'it@.2':>7}{'it@.1':>7}"
           f"{'ov_end':>8}{'maxD':>7}{'iters':>7}")
    agg = {}
    for d in designs:
        print("-" * 108)
        print(hdr if d == designs[0] else "")
        for name, (logdir, pat) in VARIANTS.items():
            rows = parse(os.path.join(GP, logdir, pat.format(d=d)))
            if rows is None:
                continue
            a = anatomy(rows)
            agg.setdefault(name, []).append(a)
            print(f"{d:10}{name:11}{a['ov0']:7.3f}{a['ov_min_e']:8.3f}"
                  f"{a['ov_peak']:9.3f}{a['peak_at']:6d}{a['rebound']:+9.3f}"
                  f"{str(a['m40']):>7}{str(a['m20']):>7}{str(a['m10']):>7}"
                  f"{a['ov_end']:8.4f}{a['maxd_end']:7.2f}{a['iters']:7d}")

    print("=" * 108)
    print("均值（算术，跨设计）")
    print(f"{'variant':11}{'ov0':>7}{'ov_min':>8}{'ov_peak':>9}{'rebound':>9}"
          f"{'it@.4':>7}{'it@.2':>7}{'it@.1':>7}{'ov_end':>8}{'maxD':>7}{'iters':>7}")
    for name, lst in agg.items():
        def mean(k):
            vals = [a[k] for a in lst if a[k] is not None]
            return sum(vals) / len(vals) if vals else float("nan")
        print(f"{name:11}{mean('ov0'):7.3f}{mean('ov_min_e'):8.3f}"
              f"{mean('ov_peak'):9.3f}{mean('rebound'):+9.3f}"
              f"{mean('m40'):7.0f}{mean('m20'):7.0f}{mean('m10'):7.0f}"
              f"{mean('ov_end'):8.4f}{mean('maxd_end'):7.2f}{mean('iters'):7.0f}")


if __name__ == "__main__":
    main()
