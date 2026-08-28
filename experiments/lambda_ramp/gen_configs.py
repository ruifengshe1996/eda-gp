#!/usr/bin/env python3
"""Generate experiment 11 configs: center init x density_weight_ramp_scale.

Every config is byte-identical to the same-machine center baseline except for
`density_weight_ramp_scale` and `result_dir`, so the ramp rate is the only
manipulated variable.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGNS = {  # design -> num_bins (square), matching the center baseline runs
    "adaptec1": 512, "adaptec2": 1024, "adaptec3": 1024, "adaptec4": 1024,
    "bigblue1": 512, "bigblue2": 1024, "bigblue3": 2048, "bigblue4": 2048,
}
ARMS = {"s070": 0.70, "s143": 1.43, "s200": 2.00}


def config(design, bins, arm, scale):
    return {
        "aux_input": f"benchmarks/ispd2005/{design}/{design}.aux",
        "gpu": 1,
        "num_bins_x": bins,
        "num_bins_y": bins,
        "global_place_stages": [{
            "num_bins_x": bins, "num_bins_y": bins, "iteration": 2000,
            "learning_rate": 0.01, "wirelength": "weighted_average",
            "optimizer": "nesterov", "Llambda_density_weight_iteration": 1,
            "Lsub_iteration": 1,
        }],
        "target_density": 1.0,
        "density_weight": 8e-05,
        "gamma": 4.0,
        "random_seed": 1000,
        "scale_factor": 1.0,
        "ignore_net_degree": 100,
        "enable_fillers": 1,
        "gp_noise_ratio": 0.025,
        "global_place_flag": 1,
        "legalize_flag": 1,
        "detailed_place_flag": 1,
        "detailed_place_engine": "",
        "detailed_place_command": "",
        "stop_overflow": 0.07,
        "dtype": "float32",
        "plot_flag": 1,
        "plot_iteration_interval": 40,
        "random_center_init_flag": 1,
        "gift_init_flag": 0,
        "sort_nets_by_degree": 0,
        "num_threads": 8,
        "deterministic_flag": 1,
        "result_dir": f"lambdaramp_results/{arm}",
        "density_weight_ramp_scale": scale,
    }


if __name__ == "__main__":
    out = os.path.join(HERE, "configs")
    os.makedirs(out, exist_ok=True)
    n = 0
    for arm, scale in ARMS.items():
        for design, bins in DESIGNS.items():
            path = os.path.join(out, f"{design}_{arm}.json")
            with open(path, "w") as f:
                json.dump(config(design, bins, arm, scale), f, indent=2)
            n += 1
    print(f"wrote {n} configs to {out}")
