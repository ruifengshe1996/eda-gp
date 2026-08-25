#!/usr/bin/env python3
"""Generate configs for experiment 6: conn-shrink (order-content vs
trajectory-history discriminator, docs/ADAPTEC4_DIAGNOSIS.md E5b)."""
import copy
import json
import os

GP = "/public_data/sheruifeng/research/eda_gp/eda-gp"
OUT = os.path.join(GP, "experiments/conn_shrink/configs")
os.makedirs(OUT, exist_ok=True)

DESIGNS = ["adaptec1", "adaptec2", "adaptec4", "bigblue3", "bigblue4"]
SCALES = {"s001": 0.001, "s010": 0.01}  # sigma as fraction of die span

for d in DESIGNS:
    base = json.load(open(f"{GP}/experiments/conn_grid_init/configs/{d}.json"))
    for tag, scale in SCALES.items():
        cfg = copy.deepcopy(base)
        cfg["conn_shrink_scale"] = scale
        cfg["result_dir"] = f"shrink_results/{tag}"
        path = f"{OUT}/{d}_{tag}.json"
        json.dump(cfg, open(path, "w"), indent=2)
        print("wrote", path)
