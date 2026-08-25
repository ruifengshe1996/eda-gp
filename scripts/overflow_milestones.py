#!/usr/bin/env python3
"""Overflow-aligned trajectory comparison.

For each variant log, parse per-iteration (iter, wHPWL, overflow) and report
wHPWL at the first iteration where overflow drops below each milestone.
Comparing variants at equal overflow removes the "spread starts lower" bias:
if the +3.5% gap is already present at overflow 0.5, it was locked in early
(ordering/init); if it opens late, it is a convergence/schedule effect.
"""
import re
import sys

LOG = "/public_data/sheruifeng/research/eda_gp/eda-gp/experiments/obstacle_field/logs"
ITER_RE = re.compile(
    r"iteration\s+(\d+), \([^)]*\), Obj \S+, DensityWeight (\S+), "
    r"wHPWL (\S+), Overflow (\S+), MaxDensity \S+, gamma ([0-9.Ee+-]+)")
MILESTONES = [0.60, 0.50, 0.40, 0.30, 0.20, 0.15, 0.10, 0.07]


def parse(path):
    rows = []
    with open(path) as f:
        for line in f:
            m = ITER_RE.search(line)
            if m:
                rows.append((int(m.group(1)), float(m.group(2)),
                             float(m.group(3)), float(m.group(4)),
                             float(m.group(5))))
    return rows


def milestone_table(rows):
    out = {}
    for ms in MILESTONES:
        for it, dw, hp, ov, gm in rows:
            if ov <= ms:
                out[ms] = (it, hp, dw, gm)
                break
    return out


def main(design):
    variants = {
        "center":    f"{LOG}/center/{design}_run.log",
        "conn_grid": f"{LOG}/conn_grid/{design}.log",
        "cap_spread": f"{LOG}/cap_spread/{design}.log",
        "obsfield":  f"{LOG}/obsfield/{design}.log",
        "obsspread": f"{LOG}/obsspread/{design}.log",
    }
    data = {v: parse(p) for v, p in variants.items()}
    ref = milestone_table(data["center"])
    print(f"== {design}: wHPWL at first crossing of each overflow milestone ==")
    print("milestone | " + " | ".join(f"{v} (iter, wHPWL, d-vs-center)"
                                      for v in variants))
    for ms in MILESTONES:
        cells = []
        for v in variants:
            t = milestone_table(data[v]).get(ms)
            if t is None:
                cells.append("--")
                continue
            it, hp, dw, gm = t
            if v == "center":
                cells.append(f"it{it} {hp:.3e}")
            else:
                r = ref.get(ms)
                d = (hp / r[1] - 1) * 100 if r else float("nan")
                cells.append(f"it{it} {hp:.3e} {d:+.1f}%")
        print(f"ov<={ms:.2f} | " + " | ".join(cells))
    # non-monotonic overflow (re-spreading) episodes
    for v, rows in data.items():
        ups = sum(1 for a, b in zip(rows, rows[1:]) if b[3] > a[3] + 0.02)
        peak_after_min = 0.0
        mn = 10.0
        for it, dw, hp, ov, gm in rows:
            mn = min(mn, ov)
            peak_after_min = max(peak_after_min, ov - mn)
        print(f"[traj] {v}: iters={len(rows)}, overflow +0.02 upticks={ups}, "
              f"max overflow rebound above running min={peak_after_min:.3f}")


if __name__ == "__main__":
    for d in sys.argv[1:] or ["adaptec4", "adaptec1"]:
        main(d)
        print()
