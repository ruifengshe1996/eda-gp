#!/bin/bash
# Experiment 12 driver: center init + obsspread's lambda0, 8 designs.
# Serialized against other eda-gp sessions via flock on gpu0.lock; picks the
# least-loaded GPU at launch to stay out of the way of other users.
set -u
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
LOCK=/public_data/sheruifeng/research/eda_gp/gpu0.lock
source $GP/env.sh
cd $GP/install
EXP=$GP/experiments/lambda_entry
STATUS=$EXP/logs/driver_status.txt
mkdir -p $EXP/logs

pick_gpu() {
  nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits \
    | sort -t, -k2 -n | head -1 | cut -d, -f1 | tr -d ' '
}

for d in adaptec1 adaptec2 adaptec3 adaptec4 bigblue1 bigblue2 bigblue3 bigblue4; do
  log=$EXP/logs/$d.log
  if grep -q "placement takes" "$log" 2>/dev/null; then
    echo "$d skip (done)" >> $STATUS; continue
  fi
  gpu=$(pick_gpu)
  echo "$d start gpu=$gpu $(date +%H:%M:%S)" >> $STATUS
  CUDA_VISIBLE_DEVICES=$gpu flock "$LOCK" \
    python dreamplace/Placer.py $EXP/configs/${d}_entry.json > "$log" 2>&1
  echo "$d exit=$? $(date +%H:%M:%S)" >> $STATUS
done
echo ALL_DONE >> $STATUS
