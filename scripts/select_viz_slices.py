#!/usr/bin/env python3
"""Select 10 evenly spaced iteration snapshots per design from viz_results.

For each design, DREAMPlace (with plot_flag=1) dumps a frame every
`plot_iteration_interval` GP iterations plus final frames after global
placement and legalization/detailed placement. We keep:
  - 9 frames evenly spaced over the global placement trajectory
    (always including iteration 0), and
  - the very last frame (final legalized/detailed placement),
renamed to viz/<design>/slice<K>_iter<NNNN>.png (K = 01..10).
"""
import os
import re
import sys

from PIL import Image

import argparse

GP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_ap = argparse.ArgumentParser()
_ap.add_argument("--src", default=os.path.join(GP_ROOT, "install", "viz_results"),
                 help="dir with <design>/plot/iterNNNN.png frames")
_ap.add_argument("--dst", default=os.path.join(GP_ROOT, "viz"),
                 help="output dir for <design>/sliceKK_iterNNNN.png")
_args = _ap.parse_args()
SRC = _args.src
DST = _args.dst
NUM_SLICES = 10


def save_compact(src_path, dst_path):
    # adaptive 128-color palette shrinks these few-color plots ~4x, visually lossless
    img = Image.open(src_path).convert("P", palette=Image.ADAPTIVE, colors=128)
    img.save(dst_path, optimize=True)

def main():
    designs = sorted(d for d in os.listdir(SRC)
                     if os.path.isdir(os.path.join(SRC, d, "plot")))
    for design in designs:
        plot_dir = os.path.join(SRC, design, "plot")
        frames = sorted(
            (int(m.group(1)), os.path.join(plot_dir, f))
            for f in os.listdir(plot_dir)
            if (m := re.fullmatch(r"iter(\d+)\.png", f))
        )
        if len(frames) < NUM_SLICES:
            print(f"[W] {design}: only {len(frames)} frames, keeping all")
            picked = frames
        else:
            # evenly spaced target iterations from 0 to the final (legalized) frame;
            # for each target take the nearest not-yet-used frame
            final_it = frames[-1][0]
            picked = []
            for i in range(NUM_SLICES):
                target = final_it * i / (NUM_SLICES - 1)
                cand = min((f for f in frames if f not in picked),
                           key=lambda f: abs(f[0] - target))
                picked.append(cand)
            picked.sort()
        out_dir = os.path.join(DST, design)
        os.makedirs(out_dir, exist_ok=True)
        for k, (it, path) in enumerate(picked, 1):
            save_compact(path, os.path.join(out_dir, f"slice{k:02d}_iter{it:04d}.png"))
        print(f"[I] {design}: {len(picked)} slices -> viz/{design}/ "
              f"(iters {', '.join(str(it) for it, _ in picked)})")

if __name__ == "__main__":
    sys.exit(main())
