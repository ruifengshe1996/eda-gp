#!/usr/bin/env python3
"""Area-weighted centroid of the conn-grid SEED (before any GP iteration).

Completes the E4 displacement chain: anchor mass -> field seed -> field final
vs melt final. Run from install/, CPU-only.
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

for design in sys.argv[1:]:
    params = Params.Params()
    params.load(f"{GP}/experiments/conn_grid_init/configs/{design}.json")
    params.verbose = 0
    db = PlaceDB.PlaceDB()
    db(params)
    np.random.seed(int(params.random_seed))
    x, y = CGI.connectivity_grid_init(db, params)
    nm = db.num_movable_nodes
    cxm = x + db.node_size_x[:nm] / 2
    cym = y + db.node_size_y[:nm] / 2
    area = (db.node_size_x[:nm] * db.node_size_y[:nm]).astype(np.float64)
    cy_die = (db.yl + db.yh) / 2
    h = db.yh - db.yl
    aw_y = float((cym * area).sum() / area.sum())
    print(f"RESULT {design}: seed centroid y={cym.mean():.0f} "
          f"[dy {(cym.mean()-cy_die)/h*100:+.1f}% of h], "
          f"area-weighted y={aw_y:.0f} [dy {(aw_y-cy_die)/h*100:+.1f}%], "
          f"mean dist to centroid "
          f"{np.hypot(cxm-cxm.mean(), cym-cym.mean()).mean():.0f}",
          flush=True)
