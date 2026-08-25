#!/usr/bin/env python3
"""Where is the fixed-pin mass? Quick check of the anchor-drag hypothesis:
if adaptec4's fixed pins sit below the die center, a quadratic (star-model)
field is pulled down linearly with distance, while the WA-HPWL gradient
saturates — explaining the downward centroid shift of every field variant.
"""
import os
import sys
import numpy as np

sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath("dreamplace"))
import Params  # noqa: E402
import PlaceDB  # noqa: E402

for design in sys.argv[1:] or ["adaptec4", "adaptec3"]:
    params = Params.Params()
    params.load(f"test/ispd2005/{design}.json")
    params.verbose = 0
    db = PlaceDB.PlaceDB()
    db(params)
    nm, np_ = db.num_movable_nodes, db.num_physical_nodes
    cx, cy = (db.xl + db.xh) / 2, (db.yl + db.yh) / 2
    h = db.yh - db.yl
    pin_node = db.pin2node_map.astype(np.int64)
    fixed_pin = pin_node >= nm
    fy = db.node_y[pin_node[fixed_pin]] + db.pin_offset_y[fixed_pin]
    fx = db.node_x[pin_node[fixed_pin]] + db.pin_offset_x[fixed_pin]
    area = (db.node_size_x[nm:np_] * db.node_size_y[nm:np_])
    ay = ((db.node_y[nm:np_] + db.node_size_y[nm:np_] / 2) * area).sum() / area.sum()
    print(f"{design}: die center y={cy:.0f} (h={h:.0f}); "
          f"fixed PIN centroid y={fy.mean():.0f} ({(fy.mean()-cy)/h*100:+.1f}% of h), "
          f"x={fx.mean():.0f} ({(fx.mean()-cx)/h*100:+.1f}%); "
          f"fixed AREA centroid y={ay:.0f} ({(ay-cy)/h*100:+.1f}%); "
          f"fixed pins={fixed_pin.sum()}")
