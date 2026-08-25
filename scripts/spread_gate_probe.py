#!/usr/bin/env python3
"""Measure the init-HPWL inflation of capacity spreading per design (CPU-only).

Reproduces the connectivity field -> capacity spread pipeline exactly as the
obsspread runs do (same seed, same params, same installed functions; nothing
is modified), and reports net HPWL of the initial placement before vs. after
spreading. The ratio calibrates the conn_spread_hpwl_gate threshold.

Usage (from install/): python ../scripts/spread_gate_probe.py <config.json>...
"""
import logging
import os
import sys

import numpy as np

_install = os.path.abspath(os.path.dirname(__file__) + "/../install")
sys.path.insert(0, _install)
sys.path.insert(0, os.path.join(_install, "dreamplace"))
import Params
import PlaceDB
import ConnectivityGridInit as CGI

logging.basicConfig(level=logging.WARNING)


def net_hpwl(placedb, centers_x, centers_y):
    """Total HPWL over all nets from cell centers + pin offsets."""
    pin_node = placedb.pin2node_map.astype(np.int64)
    pin_net = placedb.pin2net_map.astype(np.int64)
    num_nets = len(placedb.flat_net2pin_start_map) - 1
    total = 0.0
    for centers, size, off in (
            (centers_x, placedb.node_size_x, placedb.pin_offset_x),
            (centers_y, placedb.node_size_y, placedb.pin_offset_y)):
        # node_size arrays include fillers; centers cover physical nodes only
        pin_pos = (centers - size[:len(centers)] / 2)[pin_node] + off
        lo = np.full(num_nets, np.inf)
        hi = np.full(num_nets, -np.inf)
        np.minimum.at(lo, pin_net, pin_pos)
        np.maximum.at(hi, pin_net, pin_pos)
        span = hi - lo
        total += span[np.isfinite(span)].sum()
    return total


def probe(config):
    params = Params.Params()
    params.load(config)
    np.random.seed(params.random_seed)
    placedb = PlaceDB.PlaceDB()
    placedb(params)

    num_movable = placedb.num_movable_nodes
    num_phys = placedb.num_physical_nodes
    rng_x = np.random.uniform(placedb.xl, placedb.xh, num_movable).astype(placedb.dtype)
    rng_y = np.random.uniform(placedb.yl, placedb.yh, num_movable).astype(placedb.dtype)
    centers_x = np.concatenate([
        rng_x, placedb.node_x[num_movable:num_phys] +
        placedb.node_size_x[num_movable:num_phys] / 2])
    centers_y = np.concatenate([
        rng_y, placedb.node_y[num_movable:num_phys] +
        placedb.node_size_y[num_movable:num_phys] / 2])

    project = None
    if getattr(params, "conn_obstacle_project_flag", 0):
        occupied, bw2, bh2 = CGI._occupancy_raster(placedb)
        project = CGI._make_obstacle_projector(placedb, occupied, bw2, bh2)
    centers_x, centers_y = CGI._jacobi_sweeps(
        placedb, centers_x, centers_y,
        int(getattr(params, "conn_init_sweeps", 32)),
        float(getattr(params, "conn_init_damping", 0.7)),
        int(params.ignore_net_degree), project=project)

    hpwl_field = net_hpwl(placedb, centers_x, centers_y)

    sx, sy = CGI._capacity_spread(
        placedb, centers_x, centers_y,
        int(getattr(params, "conn_spread_leaf_size", 16)),
        float(getattr(params, "conn_spread_density_slack", 1.5)))
    spread_x = centers_x.copy()
    spread_y = centers_y.copy()
    spread_x[:num_movable] = sx
    spread_y[:num_movable] = sy
    hpwl_spread = net_hpwl(placedb, spread_x, spread_y)

    # candidate gate statistics, std cells only (the spread moves only them)
    is_std = (placedb.node_size_y[:num_movable] <= placedb.row_height * 1.5)
    fx, fy = centers_x[:num_movable][is_std], centers_y[:num_movable][is_std]
    W, H = placedb.xh - placedb.xl, placedb.yh - placedb.yl
    span_x = np.quantile(fx, 0.95) - np.quantile(fx, 0.05)
    span_y = np.quantile(fy, 0.95) - np.quantile(fy, 0.05)
    span_frac = (span_x * span_y) / (W * H)
    disp = np.hypot(sx[is_std] - fx, sy[is_std] - fy)
    disp_med = np.median(disp)
    disp_frac = disp_med / np.hypot(W, H)
    disp_over_span = disp_med / max(np.sqrt(span_x * span_y), 1e-12)

    # snapped variants = the actual optimizer start states (matches run logs)
    kx, ky = CGI._nearest_snap(placedb, centers_x, centers_y)
    snap_f_x, snap_f_y = centers_x.copy(), centers_y.copy()
    snap_f_x[:num_movable], snap_f_y[:num_movable] = kx, ky
    hpwl_snap_field = net_hpwl(placedb, snap_f_x, snap_f_y)
    kx, ky = CGI._nearest_snap(placedb, spread_x, spread_y)
    snap_s_x, snap_s_y = spread_x.copy(), spread_y.copy()
    snap_s_x[:num_movable], snap_s_y[:num_movable] = kx, ky
    hpwl_snap_spread = net_hpwl(placedb, snap_s_x, snap_s_y)

    # centroid offsets from the layout center, as fractions of W/H:
    # field embedding (std cells), spread state, and the fixed-pin anchor mass
    cxm, cym = (placedb.xl + placedb.xh) / 2, (placedb.yl + placedb.yh) / 2
    cen_dx, cen_dy = (fx.mean() - cxm) / W, (fy.mean() - cym) / H
    spr_dx = (sx[is_std].mean() - cxm) / W
    spr_dy = (sy[is_std].mean() - cym) / H
    fixed_mask = placedb.pin2node_map >= num_movable
    fp_nodes = placedb.pin2node_map[fixed_mask]
    fp_dx = ((placedb.node_x[fp_nodes] +
              placedb.pin_offset_x[fixed_mask]).mean() - cxm) / W
    fp_dy = ((placedb.node_y[fp_nodes] +
              placedb.pin_offset_y[fixed_mask]).mean() - cym) / H

    design = os.path.basename(config).split("_")[0].split(".")[0]
    print("%-10s span_frac %.4f  disp_frac %.4f  disp/span %.3f  "
          "raw_ratio %.2f  snap_ratio %.2f  cen(%+.3f,%+.3f)  "
          "spr(%+.3f,%+.3f)  fp(%+.3f,%+.3f)  (field %.3e spread %.3e "
          "snapF %.3e snapS %.3e)"
          % (design, span_frac, disp_frac, disp_over_span,
             hpwl_spread / hpwl_field, hpwl_snap_spread / hpwl_snap_field,
             cen_dx, cen_dy, spr_dx, spr_dy, fp_dx, fp_dy,
             hpwl_field, hpwl_spread, hpwl_snap_field, hpwl_snap_spread),
          flush=True)


if __name__ == "__main__":
    for config in sys.argv[1:]:
        probe(config)
