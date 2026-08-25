#!/bin/bash
# Experiment 5 driver: GiFt spectral initialization A/B (gift_init_flag=1 on
# default center configs; the GiFt op transforms init_pos at GP start).
# Center baseline is reused from experiments/obstacle_field/logs/center.
# Holds the shared GPU-0 lock: one batch runs at a time across sessions.
set -u
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
LOCK=/public_data/sheruifeng/research/eda_gp/gpu0.lock
source $GP/env.sh
cd $GP/install
EXP=$GP/experiments/gift_init
STATUS=$EXP/logs/driver_status.txt
: > $STATUS
export CUDA_VISIBLE_DEVICES=0

exec 9>$LOCK
flock 9

# discriminative designs first (per e0's S2 rationale), so an interrupted
# batch still answers the hypothesis: adaptec4 (the immune design), adaptec2
# (obstacle-sensitive), bigblue3 (field collapse), adaptec1 (benign control)
for d in adaptec4 adaptec2 bigblue3 adaptec1 adaptec3 bigblue1 bigblue2 bigblue4; do
  if grep -q "wHPWL" $EXP/logs/$d.log 2>/dev/null && grep -q "placement takes" $EXP/logs/$d.log 2>/dev/null; then
    echo "gift/$d skip (done)" >> $STATUS; continue
  fi
  python dreamplace/Placer.py $EXP/configs/$d.json > $EXP/logs/$d.log 2>&1
  echo "gift/$d exit=$?" >> $STATUS
  # E4 anchor-drag prediction: record final movable centroid (gift vs center)
  python ../scripts/movable_centroid.py $d \
    results/$d/$d.gp.pl gift_results/$d/$d.gp.pl 2>/dev/null \
    | grep -v '^\[' >> $EXP/logs/centroids.txt
done
echo ALL_DONE >> $STATUS
