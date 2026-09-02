#!/bin/bash
# Experiment 13 driver: per-net gamma sign test, 2 arms x 8 designs.
set -u
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
LOCK=/public_data/sheruifeng/research/eda_gp/gpu0.lock
source $GP/env.sh
cd $GP/install
EXP=$GP/experiments/gamma_local
STATUS=$EXP/logs/driver_status.txt
mkdir -p $EXP/logs/{gpos,gneg}

pick_gpu() {
  nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits \
    | sort -t, -k2 -n | head -1 | cut -d, -f1 | tr -d ' '
}

for arm in gneg gpos; do   # the open question (gneg) runs first
  for d in adaptec1 adaptec2 adaptec3 adaptec4 bigblue1 bigblue2 bigblue3 bigblue4; do
    log=$EXP/logs/$arm/$d.log
    if grep -q "placement takes" "$log" 2>/dev/null; then
      echo "$arm/$d skip (done)" >> $STATUS; continue
    fi
    gpu=$(pick_gpu)
    echo "$arm/$d start gpu=$gpu $(date +%H:%M:%S)" >> $STATUS
    CUDA_VISIBLE_DEVICES=$gpu flock "$LOCK" \
      python dreamplace/Placer.py $EXP/configs/${d}_${arm}.json > "$log" 2>&1
    echo "$arm/$d exit=$? $(date +%H:%M:%S)" >> $STATUS
  done
  echo "ARM_${arm}_DONE" >> $STATUS
done
echo ALL_DONE >> $STATUS
