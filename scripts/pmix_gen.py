#!/usr/bin/env python3
"""Generate p-mix init benchmarks for the fall dose-response experiment.

For a design and mix fraction p, place every movable cell at
  center + p * (field_offset_normalized) + (1-p) * (random_offset),
where field_offset_normalized is the connectivity-field solution rescaled to
sigma = 0.001 * die span per axis (the E6 shrink state) and random_offset is
N(0, (0.001*span)^2) — so p=1 reproduces conn-shrink and p=0 reproduces
center init, with identical geometry at every p.

Writes a sibling benchmark dir <bench>/<design>_pmix_<tag>/ with symlinks to
the original files and a rewritten .aux + .pl, then a probe config can point
aux_input at it with all init flags off.
"""
import os
import sys

import numpy as np

sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath("dreamplace"))
import Params  # noqa: E402
import PlaceDB  # noqa: E402
import ConnectivityGridInit as CGI  # noqa: E402

GP = "/public_data/sheruifeng/research/eda_gp/eda-gp"
SIGMA = 0.001

design = sys.argv[1]
ps = [float(v) for v in sys.argv[2:]] or [0.0, 0.03, 0.1, 0.3, 1.0]

params = Params.Params()
params.load(f"{GP}/experiments/conn_grid_init/configs/{design}.json")
params.verbose = 0
db = PlaceDB.PlaceDB()
db(params)
nm = db.num_movable_nodes
W, H = db.xh - db.xl, db.yh - db.yl
cx, cy = (db.xl + db.xh) / 2, (db.yl + db.yh) / 2

np.random.seed(int(params.random_seed))
fx, fy = CGI.connectivity_grid_init(db, params)  # lower-left, unshrunk field
fcx = fx + db.node_size_x[:nm] / 2
fcy = fy + db.node_size_y[:nm] / 2
area = (db.node_size_x[:nm] * db.node_size_y[:nm]).astype(np.float64)


def normed(v, span):
    c = float((v * area).sum() / area.sum())
    std = float(np.sqrt((((v - c) ** 2) * area).sum() / area.sum()))
    return (v - c) * (SIGMA * span / max(std, 1e-12))


ox, oy = normed(fcx, W), normed(fcy, H)
rng = np.random.RandomState(int(params.random_seed) + 7)
rx = rng.normal(0, SIGMA * W, nm)
ry = rng.normal(0, SIGMA * H, nm)

bench_src = os.path.dirname(os.path.join(GP, "install", params.aux_input))
aux_name = os.path.basename(params.aux_input)

# node name order for the .pl: use the raw bookshelf names
names = [db.node_names[i].decode() if isinstance(db.node_names[i], bytes)
         else str(db.node_names[i]) for i in range(db.num_physical_nodes)]

for p in ps:
    tag = ("%.3f" % p).replace(".", "")
    mixx = cx + p * ox + (1 - p) * rx - db.node_size_x[:nm] / 2
    mixy = cy + p * oy + (1 - p) * ry - db.node_size_y[:nm] / 2
    np.clip(mixx, db.xl, db.xh - db.node_size_x[:nm], out=mixx)
    np.clip(mixy, db.yl, db.yh - db.node_size_y[:nm], out=mixy)

    dst = f"{bench_src}_pmix_{tag}"
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(bench_src):
        link = os.path.join(dst, f)
        if f.endswith(".pl") or f.endswith(".aux") or os.path.lexists(link):
            continue
        os.symlink(os.path.join(bench_src, f), link)
    # rewrite aux (same file list; .pl name kept)
    aux = open(os.path.join(bench_src, aux_name)).read()
    open(os.path.join(dst, aux_name), "w").write(aux)
    plname = [t for t in aux.split() if t.endswith(".pl")][0]
    with open(os.path.join(dst, plname), "w") as f:
        f.write("UCLA pl 1.0\n\n")
        for i in range(nm):
            f.write(f"{names[i]} {mixx[i]:.4f} {mixy[i]:.4f} : N\n")
        for i in range(nm, db.num_physical_nodes):
            f.write(f"{names[i]} {db.node_x[i]:.4f} {db.node_y[i]:.4f} : N /FIXED\n")
    print(f"WROTE {dst}/{plname} (p={p})")
