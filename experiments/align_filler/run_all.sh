#!/bin/bash
# Experiment 10 driver: N1 (schedule state-alignment) x N2 (inverse-density
# filler seeding) 2x2 ablation on the obsspread base. The (off,off) arm is
# reused from experiments/conn_rebuild/logs/obsspread. adaptec1's three arms
# run first for an early signal. Serializes on the shared GPU-0 lock.
set -u
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
LOCK=/public_data/sheruifeng/research/eda_gp/gpu0.lock
source $GP/env.sh
cd $GP/install
EXP=$GP/experiments/align_filler
STATUS=$EXP/logs/driver_status.txt
mkdir -p $EXP/logs/{n1,n2,n1n2}
: > $STATUS
export CUDA_VISIBLE_DEVICES=0

run() {  # run <design> <arm>
  log=$EXP/logs/$2/$1.log
  if grep -q "wHPWL" "$log" 2>/dev/null && grep -q "placement takes" "$log" 2>/dev/null; then
    echo "$2/$1 skip (done)" >> $STATUS; return 0
  fi
  flock "$LOCK" python dreamplace/Placer.py $EXP/configs/$1_$2.json > "$log" 2>&1
  echo "$2/$1 exit=$?" >> $STATUS
}

for arm in n1 n2 n1n2; do run adaptec1 $arm; done
for d in adaptec2 adaptec3 adaptec4 bigblue1 bigblue2 bigblue3 bigblue4; do
  for arm in n1 n2 n1n2; do run $d $arm; done
done
echo ALL_DONE >> $STATUS
