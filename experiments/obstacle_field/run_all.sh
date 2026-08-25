#!/bin/bash
# Experiment 2 driver: obstacle-aware connectivity field (docs/INIT_SENSITIVITY_ANALYSIS.md D2).
# Reruns center / conn-grid / cap-spread references on this machine (GPU arch changed
# from sm_86 to sm_90, so committed numbers drift slightly), then the two new variants:
#   obsfield  = conn-grid snap + conn_obstacle_project_flag
#   obsspread = capacity spread + conn_obstacle_project_flag
# One run at a time on GPU 0 to keep footprint low (GPUs are shared).
set -u
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
source $GP/env.sh
cd $GP/install
EXP=$GP/experiments/obstacle_field
STATUS=$EXP/logs/driver_status.txt
mkdir -p $EXP/logs/{center,conn_grid,cap_spread,obsfield,obsspread}
: > $STATUS
export CUDA_VISIBLE_DEVICES=0

DESIGNS="adaptec1 adaptec2 adaptec3 adaptec4 bigblue1 bigblue2 bigblue3 bigblue4"

run() {  # run <config> <logfile> <tag>
  if grep -q "wHPWL" "$2" 2>/dev/null && grep -q "placement takes" "$2" 2>/dev/null; then
    echo "$3 skip (done)" >> $STATUS; return 0
  fi
  python dreamplace/Placer.py "$1" > "$2" 2>&1
  echo "$3 exit=$?" >> $STATUS
}

for d in $DESIGNS; do
  run test/ispd2005/$d.json                       $EXP/logs/center/${d}_run.log   center/$d
  run ../experiments/conn_grid_init/configs/$d.json $EXP/logs/conn_grid/$d.log    conn_grid/$d
  run ../experiments/capacity_snap/configs/$d.json  $EXP/logs/cap_spread/$d.log   cap_spread/$d
  run $EXP/configs/${d}_obsfield.json             $EXP/logs/obsfield/$d.log       obsfield/$d
  run $EXP/configs/${d}_obsspread.json            $EXP/logs/obsspread/$d.log      obsspread/$d
done
echo ALL_DONE >> $STATUS
