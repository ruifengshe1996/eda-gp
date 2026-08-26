#!/usr/bin/env python3
"""Replicate Placer.place() exactly up to NonLinearPlace construction for two
configs and diff their init_pos (movable x/y) statistics."""
import os
import sys

import numpy as np

sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath("dreamplace"))
import Params  # noqa: E402
import PlaceDB  # noqa: E402
import NonLinearPlace  # noqa: E402

GP = "/public_data/sheruifeng/research/eda_gp/eda-gp"


def build(cfg, overrides):
    params = Params.Params()
    params.load(cfg)
    params.verbose = 0
    for k, v in overrides.items():
        setattr(params, k, v)
    np.random.seed(params.random_seed)
    db = PlaceDB.PlaceDB()
    db(params)
    placer = NonLinearPlace.NonLinearPlace(params, db, None)
    nm = db.num_movable_nodes
    nn = db.num_nodes
    ip = placer.init_pos
    x = ip[0:nm] + db.node_size_x[:nm] / 2
    y = ip[nn:nn + nm] + db.node_size_y[:nm] / 2
    H = db.yh - db.yl
    W = db.xh - db.xl
    print(f"[{os.path.basename(cfg)} {overrides}] movable: "
          f"centroid=({x.mean():.0f},{y.mean():.0f}) "
          f"std/W,H=({x.std()/W:.5f},{y.std()/H:.5f}) "
          f"min_y={y.min():.0f} max_y={y.max():.0f}")
    # fillers
    fx = ip[db.num_physical_nodes:nn]
    fy = ip[nn + db.num_physical_nodes:2 * nn]
    if len(fx):
        print(f"  fillers: centroid=({fx.mean():.0f},{fy.mean():.0f}) "
              f"std=({fx.std():.0f},{fy.std():.0f}) n={len(fx)}")
    return x, y


x1, y1 = build(f"{GP}/experiments/conn_shrink/configs/adaptec1_s001.json", {})
x0, y0 = build(f"{GP}/experiments/conn_grid_init/configs/adaptec1.json",
               {"connectivity_grid_init_flag": 0,
                "aux_input": "benchmarks/ispd2005/adaptec1_shrinkblob/adaptec1.aux"})
d = np.hypot(x1 - x0, y1 - y0)
print(f"pairwise |pos1-pos0|: mean={d.mean():.1f} max={d.max():.1f} "
      f"(die H={y1.max()-y1.min():.0f}-ish)")
