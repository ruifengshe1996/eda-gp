#!/usr/bin/env python3
"""Parse DREAMPlace logs for an A/B experiment and emit metrics + convergence curves.

A = baseline (random_center_init), logs in docs/logs/<design>_run.log
B = experiment variant, logs given by --b-logs directory (<design>.log)

Outputs into the experiment directory:
  metrics.csv, metrics.md (summary table),
  curves_hpwl.png, curves_overflow.png (per-design A/B overlays)
"""
import argparse
import csv
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DESIGNS = ["adaptec1", "adaptec2", "adaptec3", "adaptec4",
           "bigblue1", "bigblue2", "bigblue3", "bigblue4"]

# full GP iteration line (has Obj/DensityWeight/Overflow)
ITER_RE = re.compile(
    r"iteration\s+(\d+), \([^)]*\), Obj (\S+), DensityWeight \S+, "
    r"wHPWL (\S+), Overflow (\S+),")
# final summary line printed after legalization/detailed placement
FINAL_RE = re.compile(r"iteration\s+(\d+), wHPWL (\S+), time")
NLP_TIME_RE = re.compile(r"non-linear placement takes (\S+) seconds")
TOTAL_TIME_RE = re.compile(r"placement takes (\S+) seconds")
LEGAL_RE = re.compile(r"legal flag = 1")
# plotting overhead (only present in plot_flag=1 runs) — subtracted from times
PLOT_TIME_RE = re.compile(r"\[INFO.*plotting to \S+ takes (\S+) seconds")

# reference palette, categorical slots 1 and 2 (validated, light mode)
COLOR_A = "#2a78d6"
COLOR_B = "#eb6834"
INK = "#0b0b0b"
INK2 = "#52514e"


def parse_log(path):
    iters, hpwl, overflow = [], [], []
    final_hpwl = final_iter = nlp_time = total_time = None
    plot_time = 0.0
    legal = False
    with open(path) as f:
        for line in f:
            m = ITER_RE.search(line)
            if m:
                iters.append(int(m.group(1)))
                hpwl.append(float(m.group(3)))
                overflow.append(float(m.group(4)))
                continue
            m = FINAL_RE.search(line)
            if m:
                final_iter, final_hpwl = int(m.group(1)), float(m.group(2))
            m = NLP_TIME_RE.search(line)
            if m:
                nlp_time = float(m.group(1))
            m = TOTAL_TIME_RE.search(line)
            if m:
                total_time = float(m.group(1))  # last match wins = whole flow
            m = PLOT_TIME_RE.search(line)
            if m:
                plot_time += float(m.group(1))
            if LEGAL_RE.search(line):
                legal = True
    if nlp_time is not None:
        nlp_time -= plot_time
    if total_time is not None:
        total_time -= plot_time
    return {"iters": iters, "hpwl": hpwl, "overflow": overflow,
            "gp_iters": max(iters) if iters else None,
            "final_iter": final_iter, "final_hpwl": final_hpwl,
            "nlp_time": nlp_time, "total_time": total_time, "legal": legal}


def style_axis(ax):
    ax.grid(True, color="#e6e5e1", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#c9c8c2")
    ax.tick_params(colors=INK2, labelsize=8)


def plot_grid(data, key, ylabel, out_path, logy=False):
    fig, axes = plt.subplots(2, 4, figsize=(14, 6.5), facecolor="white")
    for ax, design in zip(axes.flat, DESIGNS):
        a, b = data[design]["A"], data[design]["B"]
        ax.plot(a["iters"], a[key], color=COLOR_A, linewidth=2, label="center init (baseline)")
        ax.plot(b["iters"], b[key], color=COLOR_B, linewidth=2, label="uniform init")
        if logy:
            ax.set_yscale("log")
        ax.set_title(design, fontsize=10, color=INK)
        style_axis(ax)
    for ax in axes[-1]:
        ax.set_xlabel("GP iteration", fontsize=9, color=INK2)
    for ax in axes[:, 0]:
        ax.set_ylabel(ylabel, fontsize=9, color=INK2)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, frameon=False,
               fontsize=10, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[I] wrote {out_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--a-logs", default="docs/logs", help="baseline logs dir (<d>_run.log)")
    p.add_argument("--b-logs", required=True, help="variant logs dir (<d>.log)")
    p.add_argument("--out", required=True, help="experiment output dir")
    args = p.parse_args()

    data = {}
    for d in DESIGNS:
        data[d] = {
            "A": parse_log(os.path.join(args.a_logs, f"{d}_run.log")),
            "B": parse_log(os.path.join(args.b_logs, f"{d}.log")),
        }

    os.makedirs(args.out, exist_ok=True)
    csv_path = os.path.join(args.out, "metrics.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["design", "variant", "final_wHPWL", "gp_iters",
                    "nlp_time_s", "total_time_s", "legal"])
        for d in DESIGNS:
            for v in ("A", "B"):
                r = data[d][v]
                w.writerow([d, "center" if v == "A" else "uniform",
                            r["final_hpwl"], r["gp_iters"],
                            r["nlp_time"], r["total_time"], int(r["legal"])])
    print(f"[I] wrote {csv_path}")

    md_path = os.path.join(args.out, "metrics.md")
    with open(md_path, "w") as f:
        f.write("| Design | wHPWL center (x1e6) | wHPWL uniform (x1e6) | delta | "
                "GP iters (C/U) | flow time s (C/U) | legal (C/U) |\n")
        f.write("|---|---|---|---|---|---|---|\n")
        for d in DESIGNS:
            a, b = data[d]["A"], data[d]["B"]
            delta = (b["final_hpwl"] - a["final_hpwl"]) / a["final_hpwl"] * 100
            f.write(f"| {d} | {a['final_hpwl']/1e6:.2f} | {b['final_hpwl']/1e6:.2f} | "
                    f"{delta:+.2f}% | {a['gp_iters']}/{b['gp_iters']} | "
                    f"{a['total_time']:.1f}/{b['total_time']:.1f} | "
                    f"{int(a['legal'])}/{int(b['legal'])} |\n")
    print(f"[I] wrote {md_path}")
    print(open(md_path).read())

    plot_grid(data, "hpwl", "wHPWL (log)", os.path.join(args.out, "curves_hpwl.png"), logy=True)
    plot_grid(data, "overflow", "density overflow",
              os.path.join(args.out, "curves_overflow.png"))


if __name__ == "__main__":
    main()
