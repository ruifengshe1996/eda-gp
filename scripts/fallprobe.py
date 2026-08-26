#!/usr/bin/env python3
"""Fall-risk probe: run the real WA+Nesterov flow for a few dozen iterations
on CPU from a given init, then report the movable-mass centroid drift.

Usage: fallprobe.py <design> <tag> <base_config> [key=json_value ...]
Writes probe config + runs Placer on CPU (gpu:0, no LG/DP/plot), then prints
the area-weighted centroid offset of the resulting .gp.pl in % of die H/W.
"""
import copy
import json
import os
import subprocess
import sys

GP = "/public_data/sheruifeng/research/eda_gp/eda-gp"
SCRATCH = "/public_data/sheruifeng/research/eda_gp/scratch"
ITERS = int(os.environ.get("PROBE_ITERS", 60))

design, tag, base_cfg = sys.argv[1], sys.argv[2], sys.argv[3]
overrides = dict(kv.split("=", 1) for kv in sys.argv[4:])

cfg = json.load(open(base_cfg))
cfg["gpu"] = 0
cfg["global_place_stages"] = copy.deepcopy(cfg["global_place_stages"])
cfg["global_place_stages"][0]["iteration"] = ITERS
cfg["legalize_flag"] = 0
cfg["detailed_place_flag"] = 0
cfg["plot_flag"] = 0
cfg["num_threads"] = 8
cfg["result_dir"] = f"fallprobe_results/{tag}"
for k, v in overrides.items():
    cfg[k] = json.loads(v)

probe_cfg = f"{SCRATCH}/fallprobe_{design}_{tag}.json"
json.dump(cfg, open(probe_cfg, "w"), indent=2)

log = f"{SCRATCH}/fallprobe_{design}_{tag}.log"
with open(log, "w") as f:
    subprocess.run(["python", "dreamplace/Placer.py", probe_cfg],
                   cwd=f"{GP}/install", stdout=f, stderr=subprocess.STDOUT,
                   check=True)

pl = f"{GP}/install/fallprobe_results/{tag}/{design}/{design}.gp.pl"
out = subprocess.run(
    ["python", f"{GP}/scripts/movable_centroid.py", design, pl],
    cwd=f"{GP}/install", capture_output=True, text=True)
for line in out.stdout.splitlines():
    if design in line and "centroid" in line:
        print(f"PROBE {tag}: {line.strip()}")
