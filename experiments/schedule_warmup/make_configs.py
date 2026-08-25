#!/usr/bin/env python3
"""Generate configs for experiment 3: schedule warm-up (D1) pilot + seed variance (S1).

Warm-up variants start from the conn-grid init configs (experiment 0) and only
add the schedule knobs committed in a80a934; seed runs replicate the center and
conn-grid references with different random seeds.
"""
import copy
import json
import os

GP = "/public_data/sheruifeng/research/eda_gp/eda-gp"
OUT = os.path.join(GP, "experiments/schedule_warmup/configs")
os.makedirs(OUT, exist_ok=True)

PILOT = ["adaptec1", "adaptec2", "adaptec4", "bigblue3"]
VARIANTS = {
    # isolate the gamma-swing fix (M3)
    "gmono": {"gamma_monotone_flag": 1},
    # deliberate re-melt: smooth-WL gamma ramp + frozen-then-renormalized lambda
    "warm": {"gamma_warmup_iters": 100, "density_weight_warmup_iters": 50},
    # composed
    "warmmono": {"gamma_warmup_iters": 100, "density_weight_warmup_iters": 50,
                 "gamma_monotone_flag": 1},
}
SEEDS = [2000, 3000]  # existing seed-1000 runs are the references


def emit(path, cfg):
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2)
    print("wrote", path)


for d in PILOT:
    base = json.load(open(f"{GP}/experiments/conn_grid_init/configs/{d}.json"))
    for v, knobs in VARIANTS.items():
        cfg = copy.deepcopy(base)
        cfg.update(knobs)
        cfg["result_dir"] = f"warmup_results/{v}"
        emit(f"{OUT}/{d}_{v}.json", cfg)

# S1 seed variance on the decisive design
for seed in SEEDS:
    for name, src in (("center", f"{GP}/install/test/ispd2005/adaptec4.json"),
                      ("conngrid", f"{GP}/experiments/conn_grid_init/configs/adaptec4.json")):
        cfg = json.load(open(src))
        cfg["random_seed"] = seed
        cfg["result_dir"] = f"warmup_results/seed_{name}_{seed}"
        emit(f"{OUT}/adaptec4_seed_{name}_{seed}.json", cfg)
