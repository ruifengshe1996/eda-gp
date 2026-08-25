#!/usr/bin/env python3
"""Per-net HPWL attribution between two placements.

Loads the benchmark once, then reads two .gp.pl files and compares per-net
HPWL: is the gap concentrated in a few long nets (global misplacement of
clusters -> ordering problem) or diffuse across many nets?
Runs CPU-only from the install dir.
"""
import os
import sys
import numpy as np

sys.path.append(os.path.abspath("."))
sys.path.append(os.path.abspath("dreamplace"))
import Params  # noqa: E402
import PlaceDB  # noqa: E402

DESIGN = sys.argv[1] if len(sys.argv) > 1 else "adaptec4"
PL_A = sys.argv[2] if len(sys.argv) > 2 else f"results/{DESIGN}/{DESIGN}.gp.pl"
PL_B = sys.argv[3] if len(sys.argv) > 3 else f"conn_results/{DESIGN}/{DESIGN}.gp.pl"
NAME_A = os.path.basename(os.path.dirname(os.path.dirname(PL_A))) or "A"
NAME_B = os.path.basename(os.path.dirname(os.path.dirname(PL_B))) or "B"

params = Params.Params()
params.load(f"test/ispd2005/{DESIGN}.json")
params.verbose = 0
placedb = PlaceDB.PlaceDB()
placedb(params)

start = placedb.flat_net2pin_start_map.astype(np.int64)
flat = placedb.flat_net2pin_map.astype(np.int64)
pin_node = placedb.pin2node_map.astype(np.int64)
num_nets = len(start) - 1
degree = (start[1:] - start[:-1]).astype(np.int64)
red_idx = start[:-1]


def net_hpwl(node_x, node_y):
    px = node_x[pin_node] + placedb.pin_offset_x
    py = node_y[pin_node] + placedb.pin_offset_y
    spans = []
    for p in (px, py):
        v = p[flat]
        mx = np.maximum.reduceat(v, red_idx)
        mn = np.minimum.reduceat(v, red_idx)
        spans.append(mx - mn)
    return spans[0] + spans[1]


def load(pl):
    placedb.read_pl(params, pl)
    return placedb.node_x.copy(), placedb.node_y.copy()


xa, ya = load(PL_A)
xb, yb = load(PL_B)
ha, hb = net_hpwl(xa, ya), net_hpwl(xb, yb)
w = getattr(placedb, "net_weights", None)
if w is not None and len(w) == num_nets:
    ha, hb = ha * w, hb * w

tot_a, tot_b = ha.sum(), hb.sum()
gap = tot_b - tot_a
print(f"{DESIGN}: total per-net HPWL {NAME_A}={tot_a:.4e} {NAME_B}={tot_b:.4e} "
      f"gap={gap:+.4e} ({gap/tot_a*+100:+.2f}%)")

d = hb - ha
order = np.argsort(d)[::-1]
pos = d[d > 0].sum()
neg = d[d < 0].sum()
print(f"sum positive deltas {pos:.4e}, sum negative {neg:.4e} "
      f"(churn ratio {(pos - neg)/abs(gap):.1f}x of net gap)")
for k in (10, 100, 1000, 10000, 100000):
    if k <= num_nets:
        print(f"top {k:>6} nets by delta: {d[order[:k]].sum()/gap*100:6.1f}% of gap, "
              f"mean degree {degree[order[:k]].mean():6.1f}")
print(f"num nets {num_nets}, mean degree {degree.mean():.2f}")

# degree-band attribution
for lo, hi in ((2, 3), (4, 10), (11, 100), (101, 100000)):
    m = (degree >= lo) & (degree <= hi)
    print(f"degree {lo:>3}-{hi:<6}: nets {m.sum():>7}, gap share "
          f"{d[m].sum()/gap*100:6.1f}%, wl share ({NAME_A}) {ha[m].sum()/tot_a*100:5.1f}%")

# spatial attribution: net center (variant A) on an 8x8 grid, positive deltas
px = xa[pin_node] + placedb.pin_offset_x
py = ya[pin_node] + placedb.pin_offset_y
vx, vy = px[flat], py[flat]
cx = (np.maximum.reduceat(vx, red_idx) + np.minimum.reduceat(vx, red_idx)) / 2
cy = (np.maximum.reduceat(vy, red_idx) + np.minimum.reduceat(vy, red_idx)) / 2
gx = np.clip(((cx - placedb.xl) / (placedb.xh - placedb.xl) * 8).astype(int), 0, 7)
gy = np.clip(((cy - placedb.yl) / (placedb.yh - placedb.yl) * 8).astype(int), 0, 7)
grid = np.zeros((8, 8))
np.add.at(grid, (gy, gx), d)
print("spatial gap share %, rows top(y high)->bottom, cols left->right:")
for r in range(7, -1, -1):
    print("  " + " ".join(f"{grid[r, c]/gap*100:6.1f}" for c in range(8)))

# compactness of movable cells
nm = placedb.num_movable_nodes
for name, (x, y) in (("A:" + NAME_A, (xa, ya)), ("B:" + NAME_B, (xb, yb))):
    mx, my = x[:nm], y[:nm]
    print(f"{name}: movable centroid ({mx.mean():.0f},{my.mean():.0f}), "
          f"std ({mx.std():.0f},{my.std():.0f}), "
          f"mean dist to centroid {np.hypot(mx-mx.mean(), my-my.mean()).mean():.0f}")
