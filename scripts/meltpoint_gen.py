#!/usr/bin/env python3
"""Experiment 9 material: point-init shadow benchmarks at a parametrized
melt location (formalizing the accidental bottom-edge point melt).

Usage: meltpoint_gen.py <design> <loc> [<loc>...]
  loc in {center, bottom, top, left, right} or "fx,fy" fractions of die
  (e.g. "0.5,0.02" = bottom-center). Cells get N(0, 0.001*span) noise per
  axis around the point, exactly like random_center_init's geometry.
Writes <bench>_melt_<loc>/ shadow dirs; probe/run configs point aux_input
there with all init flags off (.pl-load path, zero code change).
"""
import os
import sys

import numpy as np

sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath("dreamplace"))
import Params  # noqa: E402
import PlaceDB  # noqa: E402

GP = "/public_data/sheruifeng/research/eda_gp/eda-gp"
NAMED = {"center": (0.5, 0.5), "bottom": (0.5, 0.02), "top": (0.5, 0.98),
         "left": (0.02, 0.5), "right": (0.98, 0.5)}

design = sys.argv[1]
locs = sys.argv[2:] or ["bottom", "top", "center"]

params = Params.Params()
params.load(f"{GP}/install/test/ispd2005/{design}.json")
params.verbose = 0
db = PlaceDB.PlaceDB()
db(params)
nm = db.num_movable_nodes
W, H = db.xh - db.xl, db.yh - db.yl
names = [db.node_names[i].decode() if isinstance(db.node_names[i], bytes)
         else str(db.node_names[i]) for i in range(db.num_physical_nodes)]
bench_src = os.path.dirname(os.path.join(GP, "install", params.aux_input))
aux_name = os.path.basename(params.aux_input)
aux = open(os.path.join(bench_src, aux_name)).read()
plname = [t for t in aux.split() if t.endswith(".pl")][0]

for loc in locs:
    fx, fy = NAMED[loc] if loc in NAMED else map(float, loc.split(","))
    tag = loc if loc in NAMED else loc.replace(",", "_").replace(".", "")
    rng = np.random.RandomState(int(params.random_seed))
    px = db.xl + fx * W + rng.normal(0, 0.001 * W, nm) - db.node_size_x[:nm] / 2
    py = db.yl + fy * H + rng.normal(0, 0.001 * H, nm) - db.node_size_y[:nm] / 2
    np.clip(px, db.xl, db.xh - db.node_size_x[:nm], out=px)
    np.clip(py, db.yl, db.yh - db.node_size_y[:nm], out=py)

    dst = f"{bench_src}_melt_{tag}"
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(bench_src):
        link = os.path.join(dst, f)
        if f.endswith(".pl") or f.endswith(".aux") or os.path.lexists(link):
            continue
        os.symlink(os.path.join(bench_src, f), link)
    open(os.path.join(dst, aux_name), "w").write(aux)
    with open(os.path.join(dst, plname), "w") as f:
        f.write("UCLA pl 1.0\n\n")
        for i in range(nm):
            f.write(f"{names[i]} {px[i]:.4f} {py[i]:.4f} : N\n")
        for i in range(nm, db.num_physical_nodes):
            f.write(f"{names[i]} {db.node_x[i]:.4f} {db.node_y[i]:.4f} : N /FIXED\n")
    print(f"WROTE {dst}/{plname} loc=({fx},{fy})")
