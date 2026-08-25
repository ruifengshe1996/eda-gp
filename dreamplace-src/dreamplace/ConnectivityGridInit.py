##
# @file   ConnectivityGridInit.py
# @brief  Connectivity-aware seed placement on the bin lattice.
#
# 1) Estimate a connectivity-aware position field: damped Jacobi sweeps that move
#    each movable cell toward the mean position of its net neighbors (fixed
#    cells/IO act as boundary anchors), i.e. an approximate quadratic placement.
# 2) Snap every movable cell to the nearest *feasible* anchor, where anchors are
#    bin-grid vertices and bin-edge midpoints, and anchors inside fixed-node
#    bounding boxes (or outside the layout) are masked out.
#

import logging
import numpy as np
from scipy.spatial import cKDTree


def _net_structures(placedb, ignore_net_degree):
    net_start = placedb.flat_net2pin_start_map
    net_degree = (net_start[1:] - net_start[:-1]).astype(np.int64)
    num_nets = len(net_degree)
    net_ok = (net_degree >= 2) & (net_degree <= ignore_net_degree)
    pin_net = placedb.pin2net_map.astype(np.int64)
    pin_node = placedb.pin2node_map.astype(np.int64)
    pin_ok = net_ok[pin_net]
    return num_nets, net_degree, pin_net, pin_node, pin_ok


def _jacobi_sweeps(placedb, centers_x, centers_y, num_sweeps, damping,
                   ignore_net_degree):
    """Damped Jacobi sweeps toward net-neighbor averages (movable cells only)."""
    num_nodes = placedb.num_physical_nodes
    num_movable = placedb.num_movable_nodes
    num_nets, net_degree, pin_net, pin_node, pin_ok = _net_structures(
        placedb, ignore_net_degree)
    deg = net_degree[pin_net].astype(placedb.dtype)  # per-pin net degree

    for _ in range(num_sweeps):
        for centers in (centers_x, centers_y):
            pin_pos = centers[pin_node]
            net_sum = np.zeros(num_nets, dtype=placedb.dtype)
            np.add.at(net_sum, pin_net, pin_pos)
            # average of the *other* pins in the net
            neighbor_avg = (net_sum[pin_net] - pin_pos) / np.maximum(deg - 1, 1)
            cell_sum = np.zeros(num_nodes, dtype=placedb.dtype)
            cell_cnt = np.zeros(num_nodes, dtype=placedb.dtype)
            np.add.at(cell_sum, pin_node, np.where(pin_ok, neighbor_avg, 0))
            np.add.at(cell_cnt, pin_node, pin_ok.astype(placedb.dtype))
            target = cell_sum / np.maximum(cell_cnt, 1)
            has_net = cell_cnt[:num_movable] > 0
            centers[:num_movable] = np.where(
                has_net,
                (1 - damping) * centers[:num_movable] + damping * target[:num_movable],
                centers[:num_movable])
    return centers_x, centers_y


def _feasible_anchors(placedb):
    """Bin-grid vertices + edge midpoints, minus points covered by fixed nodes.

    Anchors live on the half-step lattice (i*bw/2, j*bh/2); vertices are
    (even, even), edge midpoints are (odd, even)/(even, odd); bin centers
    (odd, odd) are excluded by construction.
    """
    xl, yl, xh, yh = placedb.xl, placedb.yl, placedb.xh, placedb.yh
    nx2 = 2 * int(placedb.num_bins_x)
    ny2 = 2 * int(placedb.num_bins_y)
    bw2 = (xh - xl) / nx2
    bh2 = (yh - yl) / ny2

    occupied = np.zeros((nx2 + 1, ny2 + 1), dtype=bool)
    beg, end = placedb.num_movable_nodes, placedb.num_physical_nodes
    for i in range(beg, end):
        i0 = int(np.ceil((placedb.node_x[i] - xl) / bw2))
        i1 = int(np.floor((placedb.node_x[i] + placedb.node_size_x[i] - xl) / bw2))
        j0 = int(np.ceil((placedb.node_y[i] - yl) / bh2))
        j1 = int(np.floor((placedb.node_y[i] + placedb.node_size_y[i] - yl) / bh2))
        if i1 < i0 or j1 < j0:
            continue
        occupied[max(i0, 0):min(i1, nx2) + 1, max(j0, 0):min(j1, ny2) + 1] = True

    ii, jj = np.meshgrid(np.arange(nx2 + 1), np.arange(ny2 + 1), indexing="ij")
    on_lattice = ~((ii % 2 == 1) & (jj % 2 == 1))  # exclude bin centers
    keep = on_lattice & ~occupied
    ax = xl + ii[keep] * bw2
    ay = yl + jj[keep] * bh2
    return np.stack([ax, ay], axis=1)


def connectivity_grid_init(placedb, params):
    """Return (x, y) lower-left positions for all movable nodes."""
    num_movable = placedb.num_movable_nodes
    num_sweeps = int(getattr(params, "conn_init_sweeps", 32))
    damping = float(getattr(params, "conn_init_damping", 0.7))

    # start from a uniform scatter so the harmonic field is not degenerate
    rng_x = np.random.uniform(placedb.xl, placedb.xh, num_movable).astype(placedb.dtype)
    rng_y = np.random.uniform(placedb.yl, placedb.yh, num_movable).astype(placedb.dtype)
    centers_x = np.concatenate([
        rng_x, (placedb.node_x[num_movable:placedb.num_physical_nodes] +
                placedb.node_size_x[num_movable:placedb.num_physical_nodes] / 2)])
    centers_y = np.concatenate([
        rng_y, (placedb.node_y[num_movable:placedb.num_physical_nodes] +
                placedb.node_size_y[num_movable:placedb.num_physical_nodes] / 2)])

    centers_x, centers_y = _jacobi_sweeps(
        placedb, centers_x, centers_y, num_sweeps, damping,
        int(params.ignore_net_degree))

    anchors = _feasible_anchors(placedb)
    logging.info("connectivity grid init: %d sweeps, %d feasible anchors"
                 % (num_sweeps, len(anchors)))
    tree = cKDTree(anchors)
    _, idx = tree.query(
        np.stack([centers_x[:num_movable], centers_y[:num_movable]], axis=1),
        workers=-1)
    snapped = anchors[idx]

    x = snapped[:, 0] - placedb.node_size_x[:num_movable] / 2
    y = snapped[:, 1] - placedb.node_size_y[:num_movable] / 2
    np.clip(x, placedb.xl, placedb.xh - placedb.node_size_x[:num_movable], out=x)
    np.clip(y, placedb.yl, placedb.yh - placedb.node_size_y[:num_movable], out=y)
    return x.astype(placedb.dtype), y.astype(placedb.dtype)
