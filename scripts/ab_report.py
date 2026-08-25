#!/usr/bin/env python3
"""Parse DREAMPlace logs for init-strategy experiments and emit metrics + curves.

Baseline A = random_center_init, logs in --a-logs (<design>_run.log).
Any number of variants via repeated --variant name=logdir (<design>.log each).

Outputs into --out: metrics.csv, metrics.md, curves_hpwl.png, curves_overflow.png.
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

ITER_RE = re.compile(
    r"iteration\s+(\d+), \([^)]*\), Obj (\S+), DensityWeight \S+, "
    r"wHPWL (\S+), Overflow (\S+),")
FINAL_RE = re.compile(r"iteration\s+(\d+), wHPWL (\S+), time")
NLP_TIME_RE = re.compile(r"non-linear placement takes (\S+) seconds")
TOTAL_TIME_RE = re.compile(r"placement takes (\S+) seconds")
LEGAL_RE = re.compile(r"legal flag = 1")
# plotting overhead (only present in plot_flag=1 runs) — subtracted from times
PLOT_TIME_RE = re.compile(r"\[INFO.*plotting to \S+ takes (\S+) seconds")

# reference palette, categorical slots in fixed order (validated, light mode);
# slot 1 (blue) is always the baseline, variants take the following slots
PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100"]
INK = "#0b0b0b"
INK2 = "#52514e"


def parse_log(path):
    # tolerate partial experiments: a missing log drops the design from the
    # report instead of crashing
    if not os.path.exists(path):
        return None
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


def plot_grid(data, variants, key, ylabel, out_path, designs=None, logy=False):
    designs = designs if designs is not None else DESIGNS
    fig, axes = plt.subplots(2, 4, figsize=(14, 6.5), facecolor="white")
    for ax in axes.flat[len(designs):]:
        ax.set_visible(False)
    for ax, design in zip(axes.flat, designs):
        for (name, _), color in zip(variants, PALETTE):
            r = data[design][name]
            ax.plot(r["iters"], r[key], color=color, linewidth=2, label=name)
        if logy:
            ax.set_yscale("log")
        ax.set_title(design, fontsize=10, color=INK)
        style_axis(ax)
    for ax in axes[-1]:
        ax.set_xlabel("GP iteration", fontsize=9, color=INK2)
    for ax in axes[:, 0]:
        ax.set_ylabel(ylabel, fontsize=9, color=INK2)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=len(variants),
               frameon=False, fontsize=10, bbox_to_anchor=(0.5, 1.0))
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"[I] wrote {out_path}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--a-logs", default="docs/logs", help="baseline logs dir (<d>_run.log)")
    p.add_argument("--a-name", default="center (baseline)")
    p.add_argument("--variant", action="append", required=True,
                   metavar="NAME=LOGDIR", help="variant logs dir (<d>.log)")
    p.add_argument("--out", required=True, help="output dir")
    args = p.parse_args()

    variants = [(args.a_name, None)]
    for v in args.variant:
        name, logdir = v.split("=", 1)
        variants.append((name, logdir))

    data = {}
    for d in DESIGNS:
        data[d] = {args.a_name: parse_log(os.path.join(args.a_logs, f"{d}_run.log"))}
        for name, logdir in variants[1:]:
            data[d][name] = parse_log(os.path.join(logdir, f"{d}.log"))
    # keep only designs for which every variant has a log
    active = [d for d in DESIGNS if all(data[d][n] is not None for n, _ in variants)]
    dropped = [d for d in DESIGNS if d not in active]
    if dropped:
        print(f"[W] dropped designs with missing logs: {', '.join(dropped)}")

    os.makedirs(args.out, exist_ok=True)
    csv_path = os.path.join(args.out, "metrics.csv")
    with open(csv_path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["design", "variant", "final_wHPWL", "gp_iters",
                    "nlp_time_s", "total_time_s", "legal"])
        for d in active:
            for name, _ in variants:
                r = data[d][name]
                w.writerow([d, name, r["final_hpwl"], r["gp_iters"],
                            r["nlp_time"], r["total_time"], int(r["legal"])])
    print(f"[I] wrote {csv_path}")

    names = [n for n, _ in variants]
    md_path = os.path.join(args.out, "metrics.md")
    with open(md_path, "w") as f:
        cols = " | ".join(f"{n} wHPWL (x1e6)" for n in names)
        deltas = " | ".join(f"{n} delta" for n in names[1:])
        f.write(f"| Design | {cols} | {deltas} | GP iters ({'/'.join(names)}) |\n")
        f.write("|" + "---|" * (1 + len(names) + len(names) - 1 + 1) + "\n")
        for d in active:
            base = data[d][names[0]]["final_hpwl"]
            vals = " | ".join(f"{data[d][n]['final_hpwl']/1e6:.2f}" for n in names)
            dl = " | ".join(
                f"{(data[d][n]['final_hpwl'] - base) / base * 100:+.2f}%"
                for n in names[1:])
            its = "/".join(str(data[d][n]["gp_iters"]) for n in names)
            f.write(f"| {d} | {vals} | {dl} | {its} |\n")
        # geomean deltas
        for n in names[1:]:
            prod, cnt = 1.0, 0
            for d in active:
                prod *= data[d][n]["final_hpwl"] / data[d][names[0]]["final_hpwl"]
                cnt += 1
            f.write(f"\ngeomean wHPWL delta {n}: {(prod ** (1 / cnt) - 1) * 100:+.2f}%")
        f.write("\n")
    print(f"[I] wrote {md_path}")
    print(open(md_path).read())

    plot_grid(data, variants, "hpwl", "wHPWL (log)",
              os.path.join(args.out, "curves_hpwl.png"), designs=active, logy=True)
    plot_grid(data, variants, "overflow", "density overflow",
              os.path.join(args.out, "curves_overflow.png"), designs=active)


if __name__ == "__main__":
    main()
