#!/bin/bash
# Experiment 4 driver, part B: seed sensitivity of capacity spreading on
# collapsed fields. Is the bigblue3/bigblue4 spread damage structural, or
# chaotic "luck of the cuts"? obsspread x {bigblue3,bigblue4,adaptec2} x
# seeds {2000,3000} + obsfield x bigblue3 x 2000 as a stability control.
# Seed-1000 references come from experiments/obstacle_field/logs (same
# machine, unchanged code). Serializes on the shared GPU-0 lock.
set -u
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
LOCK=/public_data/sheruifeng/research/eda_gp/gpu0.lock
source $GP/env.sh
cd $GP/install
EXP=$GP/experiments/field_gate
STATUS=$EXP/logs/driver_status.txt
mkdir -p $EXP/logs/seedvar
: > $STATUS
export CUDA_VISIBLE_DEVICES=0

RUNS="bigblue3_obsspread_s2000 bigblue3_obsspread_s3000 \
      bigblue4_obsspread_s2000 bigblue4_obsspread_s3000 \
      adaptec2_obsspread_s2000 adaptec2_obsspread_s3000 \
      bigblue3_obsfield_s2000"

for r in $RUNS; do
  log=$EXP/logs/seedvar/$r.log
  if grep -q "wHPWL" "$log" 2>/dev/null && grep -q "placement takes" "$log" 2>/dev/null; then
    echo "$r skip (done)" >> $STATUS; continue
  fi
  flock "$LOCK" python dreamplace/Placer.py $EXP/configs/$r.json > "$log" 2>&1
  echo "$r exit=$?" >> $STATUS
done
echo ALL_DONE >> $STATUS
