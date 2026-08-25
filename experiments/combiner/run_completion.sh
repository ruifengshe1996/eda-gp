#!/bin/bash
# Experiment 7 phase 1: complete the shrink-001 routing-table data
# (a3/b1/b2, sigma=0.001; exp 6 covered the other five designs).
set -u
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
source $GP/env.sh
cd $GP/install
EXP=$GP/experiments/combiner
STATUS=$EXP/logs/completion_status.txt
: > $STATUS
export CUDA_VISIBLE_DEVICES=0
exec 9>/public_data/sheruifeng/research/eda_gp/gpu0.lock
flock 9
for d in adaptec3 bigblue1 bigblue2; do
  python dreamplace/Placer.py ../experiments/conn_shrink/configs/${d}_s001.json > $EXP/logs/${d}_shrink001.log 2>&1
  echo "shrink001/$d exit=$?" >> $STATUS
  python ../scripts/movable_centroid.py $d \
    results/$d/$d.gp.pl shrink_results/s001/$d/$d.gp.pl 2>/dev/null \
    | grep -v '^\[' >> $EXP/logs/centroids.txt
done
echo ALL_DONE >> $STATUS
