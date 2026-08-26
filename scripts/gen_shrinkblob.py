#!/usr/bin/env python3
"""Write a shadow benchmark whose .pl is the EXACT shrink init (CGI with
conn_shrink_scale active), for probing via the flag=0 (.pl-load) path.
Decouples 'positions/order' from 'init code path' in the first-iteration
step-explosion investigation. Usage: gen_shrinkblob.py <design>
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
design = sys.argv[1]

params = Params.Params()
params.load(f"{GP}/experiments/conn_shrink/configs/{design}_s001.json")
params.verbose = 0
db = PlaceDB.PlaceDB()
db(params)
nm = db.num_movable_nodes

np.random.seed(int(params.random_seed))
x, y = CGI.connectivity_grid_init(db, params)  # shrink active in this config
print("blob check: std_y/H=%.5f centroid_y=%.0f (die center %.0f)" % (
    np.std(y + db.node_size_y[:nm] / 2) / (db.yh - db.yl),
    np.mean(y + db.node_size_y[:nm] / 2), (db.yl + db.yh) / 2))

names = [db.node_names[i].decode() if isinstance(db.node_names[i], bytes)
         else str(db.node_names[i]) for i in range(db.num_physical_nodes)]
bench_src = os.path.dirname(os.path.join(GP, "install", params.aux_input))
aux_name = os.path.basename(params.aux_input)
dst = f"{bench_src}_shrinkblob"
os.makedirs(dst, exist_ok=True)
for f in os.listdir(bench_src):
    link = os.path.join(dst, f)
    if f.endswith(".pl") or f.endswith(".aux") or os.path.lexists(link):
        continue
    os.symlink(os.path.join(bench_src, f), link)
aux = open(os.path.join(bench_src, aux_name)).read()
open(os.path.join(dst, aux_name), "w").write(aux)
plname = [t for t in aux.split() if t.endswith(".pl")][0]
with open(os.path.join(dst, plname), "w") as f:
    f.write("UCLA pl 1.0\n\n")
    for i in range(nm):
        f.write(f"{names[i]} {x[i]:.4f} {y[i]:.4f} : N\n")
    for i in range(nm, db.num_physical_nodes):
        f.write(f"{names[i]} {db.node_x[i]:.4f} {db.node_y[i]:.4f} : N /FIXED\n")
print(f"WROTE {dst}/{plname}")
