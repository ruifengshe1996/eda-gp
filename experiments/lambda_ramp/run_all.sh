#!/bin/bash
# Experiment 11 driver: center init x lambda ramp scale, 3 arms x 8 designs.
# Serialized against other eda-gp sessions via flock on gpu0.lock. The GPU is
# chosen at launch time as the one with the least memory in use, so we stay out
# of the way of the other users on this shared machine.
set -u
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
LOCK=/public_data/sheruifeng/research/eda_gp/gpu0.lock
source $GP/env.sh
cd $GP/install
EXP=$GP/experiments/lambda_ramp
STATUS=$EXP/logs/driver_status.txt
mkdir -p $EXP/logs/{s070,s143,s200}

pick_gpu() {
  nvidia-smi --query-gpu=index,memory.used --format=csv,noheader,nounits \
    | sort -t, -k2 -n | head -1 | cut -d, -f1 | tr -d ' '
}

run() {  # $1=design $2=arm
  local log=$EXP/logs/$2/$1.log
  if grep -q "placement takes" "$log" 2>/dev/null; then
    echo "$2/$1 skip (done)" >> $STATUS; return 0
  fi
  local gpu; gpu=$(pick_gpu)
  echo "$2/$1 start gpu=$gpu $(date +%H:%M:%S)" >> $STATUS
  CUDA_VISIBLE_DEVICES=$gpu flock "$LOCK" \
    python dreamplace/Placer.py $EXP/configs/$1_$2.json > "$log" 2>&1
  echo "$2/$1 exit=$? $(date +%H:%M:%S)" >> $STATUS
}

# Arm order: the two decisive arms first (R2 needs s143, R4 needs s070),
# s200 last since it only extends the frontier.
for arm in s143 s070 s200; do
  for d in adaptec1 adaptec2 adaptec3 adaptec4 bigblue1 bigblue2 bigblue3 bigblue4; do
    run $d $arm
  done
  echo "ARM_${arm}_DONE" >> $STATUS
done
echo ALL_DONE >> $STATUS
