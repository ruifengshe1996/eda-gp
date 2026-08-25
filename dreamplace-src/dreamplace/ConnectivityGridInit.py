##
# @file   ConnectivityGridInit.py
# @brief  Connectivity-aware seed placement on the bin lattice.
#
# 1) Estimate a connectivity-aware position field: damped Jacobi sweeps that move
#    each movable cell toward the mean position of its net neighbors (fixed
#    cells/IO act as boundary anchors), i.e. an approximate quadratic placement.
# 2) Map cells onto *feasible* anchors, where anchors are bin-grid vertices and
#    bin-edge midpoints, and anchors inside fixed-node bounding boxes (or
#    outside the layout) are masked out. Two modes:
#      - nearest-anchor snapping (default): preserves the field, allows stacking;
#      - capacity spreading (conn_capacity_spread_flag): order-preserving
#        recursive bisection that balances movable cell area against free area
#        (fixed-node area excluded), bounding local density before snapping.
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


def _make_obstacle_projector(placedb, occupied, bw2, bh2):
    """Map any position inside a fixed-node region to the nearest free raster
    point (nearest-free indices precomputed once via an EDT)."""
    from scipy import ndimage
    _, (near_i, near_j) = ndimage.distance_transform_edt(
        occupied, return_indices=True)

    def project(centers_x, centers_y, num_movable):
        i = np.clip(np.rint((centers_x[:num_movable] - placedb.xl) / bw2),
                    0, occupied.shape[0] - 1).astype(np.int64)
        j = np.clip(np.rint((centers_y[:num_movable] - placedb.yl) / bh2),
                    0, occupied.shape[1] - 1).astype(np.int64)
        inside = occupied[i, j]
        if inside.any():
            ii, jj = i[inside], j[inside]
            centers_x[:num_movable][inside] = placedb.xl + near_i[ii, jj] * bw2
            centers_y[:num_movable][inside] = placedb.yl + near_j[ii, jj] * bh2
    return project


def _jacobi_sweeps(placedb, centers_x, centers_y, num_sweeps, damping,
                   ignore_net_degree, project=None):
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
        if project is not None:
            project(centers_x, centers_y, num_movable)
    return centers_x, centers_y


def _occupancy_raster(placedb):
    """Half-step raster over the layout; True where fixed nodes cover a point.

    Raster point (i, j) sits at (xl + i*bw/2, yl + j*bh/2). Lattice anchors are
    the points with not both i, j odd (bin centers excluded).
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
    return occupied, bw2, bh2


def _lattice_mask(shape):
    ii, jj = np.meshgrid(np.arange(shape[0]), np.arange(shape[1]), indexing="ij")
    return ~((ii % 2 == 1) & (jj % 2 == 1))  # exclude bin centers


def _feasible_anchor_coords(placedb, occupied, bw2, bh2):
    keep = _lattice_mask(occupied.shape) & ~occupied
    ii, jj = np.nonzero(keep)
    ax = placedb.xl + ii * bw2
    ay = placedb.yl + jj * bh2
    return np.stack([ax, ay], axis=1)


def _nearest_snap(placedb, centers_x, centers_y):
    occupied, bw2, bh2 = _occupancy_raster(placedb)
    anchors = _feasible_anchor_coords(placedb, occupied, bw2, bh2)
    logging.info("connectivity grid init: %d feasible anchors" % (len(anchors)))
    tree = cKDTree(anchors)
    num_movable = placedb.num_movable_nodes
    _, idx = tree.query(
        np.stack([centers_x[:num_movable], centers_y[:num_movable]], axis=1),
        workers=-1)
    return anchors[idx][:, 0], anchors[idx][:, 1]


def _capacity_spread(placedb, centers_x, centers_y, leaf_size=16, slack=1.5):
    """Capacity-clipped, geometry-respecting recursive bisection.

    Cuts follow the connectivity field (area-weighted median of cell
    coordinates); cells cross a cut only when one side would exceed
    `slack x average fill` of its free capacity (fixed-node area excluded).
    Leaves clip their cells into the leaf rect, keeping field positions.
    Where capacity never binds this reduces to plain nearest-anchor snapping;
    it spreads only overloaded clumps, preserving relative order.
    """
    num_movable = placedb.num_movable_nodes
    occupied, bw2, bh2 = _occupancy_raster(placedb)
    free = _lattice_mask(occupied.shape) & ~occupied
    # 2D prefix sum of free anchors for O(1) rectangle counts
    P = np.zeros((free.shape[0] + 1, free.shape[1] + 1), dtype=np.int64)
    np.cumsum(np.cumsum(free, axis=0), axis=1, out=P[1:, 1:])

    def free_count(i0, j0, i1, j1):  # inclusive rect
        return P[i1 + 1, j1 + 1] - P[i0, j1 + 1] - P[i1 + 1, j0] + P[i0, j0]

    cx = centers_x[:num_movable].astype(np.float64)
    cy = centers_y[:num_movable].astype(np.float64)
    area = (placedb.node_size_x[:num_movable] *
            placedb.node_size_y[:num_movable]).astype(np.float64)
    out_x = np.empty(num_movable, dtype=placedb.dtype)
    out_y = np.empty(num_movable, dtype=placedb.dtype)

    anchor_area = 4.0 / 3.0 * bw2 * bh2  # 3 anchors per bin of area 4*bw2*bh2
    total_free = free_count(0, 0, free.shape[0] - 1, free.shape[1] - 1)
    fill = area.sum() / max(total_free * anchor_area, 1e-12)
    cap_frac = min(1.0, fill * slack)  # capacity fraction of free area per rect
    # movable macros keep their field position (spreading reorders them too
    # aggressively); only standard cells are spread. Macro area still counts
    # into `fill` above so the capacity budget stays conservative.
    is_std = (placedb.node_size_y[:num_movable] <= placedb.row_height * 1.5)
    std_cells = np.nonzero(is_std)[0]
    macro_cells = np.nonzero(~is_std)[0]
    out_x[macro_cells] = cx[macro_cells]
    out_y[macro_cells] = cy[macro_cells]
    logging.info(
        "connectivity grid init: capacity spread, fill %.3f, cap_frac %.3f, "
        "%d free anchors, %d std cells, %d movable macros kept at field"
        % (fill, cap_frac, int(total_free), len(std_cells), len(macro_cells)))

    stack = [(std_cells, 0, 0, free.shape[0] - 1, free.shape[1] - 1)]
    while stack:
        cells, i0, j0, i1, j1 = stack.pop()
        if len(cells) == 0:
            continue
        if len(cells) <= leaf_size or (i1 - i0 <= 1 and j1 - j0 <= 1):
            # leaf: keep field positions, clipped into the leaf rect
            out_x[cells] = np.clip(cx[cells], placedb.xl + i0 * bw2,
                                   placedb.xl + i1 * bw2)
            out_y[cells] = np.clip(cy[cells], placedb.yl + j0 * bh2,
                                   placedb.yl + j1 * bh2)
            continue
        wide = (i1 - i0) * bw2 >= (j1 - j0) * bh2
        coord = cx[cells] if wide else cy[cells]
        lo_edge = (placedb.xl + i0 * bw2) if wide else (placedb.yl + j0 * bh2)
        step = bw2 if wide else bh2
        r0, r1 = (i0, i1) if wide else (j0, j1)
        order = np.argsort(coord, kind="stable")
        carea = np.cumsum(area[cells[order]])
        total = carea[-1]
        # split index at the area-weighted median coordinate, in raster units
        med_coord = coord[order[int(np.searchsorted(carea, total / 2.0))]]
        s = int((med_coord - lo_edge) / step)
        s = min(max(r0 + s, r0), r1 - 1)
        boundary = lo_edge + (s - r0 + 1) * step
        nat = int(np.searchsorted(coord[order], boundary))
        if wide:
            fL = free_count(i0, j0, s, j1)
            fR = free_count(s + 1, j0, i1, j1)
        else:
            fL = free_count(i0, j0, i1, s)
            fR = free_count(i0, s + 1, i1, j1)
        capL = cap_frac * fL * anchor_area
        capR = cap_frac * fR * anchor_area
        if capL + capR < total:
            # rect overloaded as a whole: split proportionally to capacity
            cut = int(np.searchsorted(carea, total * capL / max(capL + capR, 1e-12)))
        else:
            cut_max = int(np.searchsorted(carea, capL))
            cut_min = int(np.searchsorted(carea, total - capR))
            cut = min(max(nat, cut_min), cut_max)
        cut = min(max(cut, 0), len(cells))
        lo, hi = cells[order[:cut]], cells[order[cut:]]
        if wide:
            stack.append((lo, i0, j0, s, j1))
            stack.append((hi, s + 1, j0, i1, j1))
        else:
            stack.append((lo, i0, j0, i1, s))
            stack.append((hi, i0, s + 1, i1, j1))

    return out_x, out_y


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

    project = None
    if getattr(params, "conn_obstacle_project_flag", 0):
        occupied, bw2, bh2 = _occupancy_raster(placedb)
        project = _make_obstacle_projector(placedb, occupied, bw2, bh2)
        logging.info("connectivity grid init: obstacle projection enabled")
    centers_x, centers_y = _jacobi_sweeps(
        placedb, centers_x, centers_y, num_sweeps, damping,
        int(params.ignore_net_degree), project=project)
    logging.info("connectivity grid init: %d sweeps done" % (num_sweeps))

    if getattr(params, "conn_capacity_spread_flag", 0):
        sx, sy = _capacity_spread(placedb, centers_x, centers_y,
                                  int(getattr(params, "conn_spread_leaf_size", 16)),
                                  float(getattr(params, "conn_spread_density_slack", 1.5)))
        centers_x[:num_movable] = sx
        centers_y[:num_movable] = sy
        sx, sy = _nearest_snap(placedb, centers_x, centers_y)
    else:
        sx, sy = _nearest_snap(placedb, centers_x, centers_y)

    x = sx - placedb.node_size_x[:num_movable] / 2
    y = sy - placedb.node_size_y[:num_movable] / 2
    np.clip(x, placedb.xl, placedb.xh - placedb.node_size_x[:num_movable], out=x)
    np.clip(y, placedb.yl, placedb.yh - placedb.node_size_y[:num_movable], out=y)
    return x.astype(placedb.dtype), y.astype(placedb.dtype)
