#!/usr/bin/env python3
"""Blue-pixel centroid per iteration frame: when does the melt migrate?

Scans <results>/<design>/plot/iterNNNN.png, masks movable-cell blue
(B >> R, B >> G), and prints the mass centroid per frame in % of frame
height from the frame center (positive = up, to match die coordinates).
Pairs each frame with overflow/DensityWeight from the run log when given.
"""
import glob
import os
import re
import sys

import numpy as np
from PIL import Image

ITER_RE = re.compile(
    r"iteration\s+(\d+), \([^)]*\), Obj \S+, DensityWeight (\S+), "
    r"wHPWL (\S+), Overflow (\S+),")


def log_table(path):
    tab = {}
    if path and os.path.exists(path):
        for line in open(path):
            m = ITER_RE.search(line)
            if m:
                tab[int(m.group(1))] = (float(m.group(2)), float(m.group(4)))
    return tab


def frame_centroid(png):
    im = np.asarray(Image.open(png).convert("RGB")).astype(np.int16)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    mask = (b - r > 60) & (b - g > 60)
    if mask.sum() < 100:
        return None
    ys, xs = np.nonzero(mask)
    h, w = mask.shape
    # image y grows downward; flip so positive = up (die coordinates)
    return (h / 2 - ys.mean()) / h * 100, (xs.mean() - w / 2) / w * 100


def main(plot_dir, log_path):
    tab = log_table(log_path)
    frames = sorted(glob.glob(os.path.join(plot_dir, "*iter*.png")))
    print(f"== {plot_dir} ({len(frames)} frames)")
    print("iter | dy% (up+) | dx% | overflow | density_weight")
    for f in frames:
        it = int(re.search(r"iter(\d+)", f).group(1))
        c = frame_centroid(f)
        if c is None:
            continue
        ov, dw = ("-", "-")
        if it in tab:
            dw, ov = f"{tab[it][0]:.2e}", f"{tab[it][1]:.3f}"
        print(f"{it:5d} | {c[0]:+6.2f} | {c[1]:+6.2f} | {ov} | {dw}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)

def frame_spread(png):
    im = np.asarray(Image.open(png).convert("RGB")).astype(np.int16)
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    mask = (b - r > 60) & (b - g > 60)
    if mask.sum() < 100:
        return None
    ys, xs = np.nonzero(mask)
    h, w = mask.shape
    d = np.hypot(xs - xs.mean(), ys - ys.mean())
    return d.mean() / h * 100, mask.sum() / (h * w) * 100
