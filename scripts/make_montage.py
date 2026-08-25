#!/usr/bin/env python3
"""Combine the 10 iteration slices of each design into one montage image.

Usage: make_montage.py <viz_dir> [more viz_dirs...]
For every <viz_dir>/<design>/sliceNN_iterMMMM.png set, writes
<viz_dir>/<design>_all.png (2x5 grid, iteration-labeled).
"""
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

CELL = 400          # cell width/height for each slice
LABEL_H = 26        # label strip under each cell
COLS, ROWS = 5, 2


def load_font(size=16):
    try:
        import matplotlib
        path = os.path.join(os.path.dirname(matplotlib.__file__),
                            "mpl-data", "fonts", "ttf", "DejaVuSans.ttf")
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def montage_design(design_dir, out_path, font):
    slices = sorted(
        (f, int(m.group(1)))
        for f in os.listdir(design_dir)
        if (m := re.search(r"slice\d+_iter(\d+)\.png", f)))
    if not slices:
        return False
    n = len(slices)
    cols = COLS if n > COLS else n
    rows = (n + cols - 1) // cols
    W, H = cols * CELL, rows * (CELL + LABEL_H)
    canvas = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(canvas)
    for k, (fname, it) in enumerate(slices):
        img = Image.open(os.path.join(design_dir, fname)).convert("RGB")
        img.thumbnail((CELL, CELL), Image.LANCZOS)
        r, c = divmod(k, cols)
        x = c * CELL + (CELL - img.width) // 2
        y = r * (CELL + LABEL_H)
        canvas.paste(img, (x, y))
        label = "iter %d" % it
        if k == n - 1:
            label += " (final)"
        tw = draw.textlength(label, font=font)
        draw.text((c * CELL + (CELL - tw) / 2, y + CELL + 4), label,
                  fill="#333333", font=font)
    canvas = canvas.convert("P", palette=Image.ADAPTIVE, colors=128)
    canvas.save(out_path, optimize=True)
    return True


def main():
    font = load_font()
    for viz_dir in sys.argv[1:]:
        for design in sorted(os.listdir(viz_dir)):
            ddir = os.path.join(viz_dir, design)
            if not os.path.isdir(ddir):
                continue
            out = os.path.join(viz_dir, design + "_all.png")
            if montage_design(ddir, out, font):
                print("[I] wrote", out)


if __name__ == "__main__":
    main()
