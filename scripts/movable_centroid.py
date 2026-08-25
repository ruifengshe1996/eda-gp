#!/usr/bin/env python3
"""Movable-cell centroid of one or more placements (companion to
fixed_mass_centroid.py, for the anchor-drag prediction of E4).

Usage (from install/): python ../scripts/movable_centroid.py <design> <pl> [<pl>...]
Prints, per .pl: area-weighted movable centroid, its offset from the die
center in % of die height, and mean distance to centroid (compactness).
"""
import os
import sys
import numpy as np

sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath("dreamplace"))
import Params  # noqa: E402
import PlaceDB  # noqa: E402

design = sys.argv[1]
pls = sys.argv[2:]
params = Params.Params()
params.load(f"test/ispd2005/{design}.json")
params.verbose = 0
db = PlaceDB.PlaceDB()
db(params)
nm = db.num_movable_nodes
cx, cy = (db.xl + db.xh) / 2, (db.yl + db.yh) / 2
h = db.yh - db.yl
area = (db.node_size_x[:nm] * db.node_size_y[:nm]).astype(np.float64)


def read_pl(path):
    x = np.array(db.node_x, copy=True)
    y = np.array(db.node_y, copy=True)
    with open(path) as f:
        for line in f:
            t = line.split()
            if len(t) < 3 or t[0].startswith("#") or t[0] == "UCLA":
                continue
            i = db.node_name2id_map.get(t[0])
            if i is not None and i < nm:
                x[i], y[i] = float(t[1]), float(t[2])
    return x[:nm], y[:nm]


for pl in pls:
    x, y = read_pl(pl)
    mx = x + db.node_size_x[:nm] / 2
    my = y + db.node_size_y[:nm] / 2
    ax = (mx * area).sum() / area.sum()
    ay = (my * area).sum() / area.sum()
    ux, uy = mx.mean(), my.mean()
    d = np.sqrt((mx - ux) ** 2 + (my - uy) ** 2).mean()
    print(f"{design} {pl}: centroid ({ux:.0f},{uy:.0f}) "
          f"[dy {(uy - cy) / h * 100:+.1f}% of h], "
          f"area-weighted ({ax:.0f},{ay:.0f}) [dy {(ay - cy) / h * 100:+.1f}%], "
          f"mean dist {d:.0f}")
