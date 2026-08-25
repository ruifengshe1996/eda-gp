#!/bin/bash
# Experiment 3 driver: schedule warm-up (D1) pilot + adaptec4 seed variance (S1).
# Queue discipline on the shared GPU 0:
#   1. wait for the replot batch (experiments/obstacle_field/logs/plot_status.txt)
#      to finish or go quiet;
#   2. hold flock on ../gpu0.lock for the whole batch, so concurrent session
#      batches serialize instead of stacking on the GPU.
set -u
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
source $GP/env.sh
cd $GP/install
EXP=$GP/experiments/schedule_warmup
STATUS=$EXP/logs/driver_status.txt
LOCK=/public_data/sheruifeng/research/eda_gp/gpu0.lock
mkdir -p $EXP/logs
: > $STATUS
export CUDA_VISIBLE_DEVICES=0

PLOT_STATUS=$GP/experiments/obstacle_field/logs/plot_status.txt
quiet=0
while true; do
  if grep -q ALL_DONE "$PLOT_STATUS" 2>/dev/null; then
    echo "replot batch ALL_DONE, proceeding" >> $STATUS; break
  fi
  if pgrep -f "dreamplace/Placer.py" > /dev/null; then
    quiet=0
  else
    quiet=$((quiet + 1))
    if [ $quiet -ge 5 ]; then
      echo "no Placer running for 5 checks, proceeding" >> $STATUS; break
    fi
  fi
  sleep 60
done

run() {  # run <config> <logfile> <tag>
  if grep -q "wHPWL" "$2" 2>/dev/null && grep -q "placement takes" "$2" 2>/dev/null; then
    echo "$3 skip (done)" >> $STATUS; return 0
  fi
  python dreamplace/Placer.py "$1" > "$2" 2>&1
  echo "$3 exit=$?" >> $STATUS
}

exec 9>"$LOCK"
flock 9
echo "acquired gpu0.lock" >> $STATUS

for d in adaptec1 adaptec2 adaptec4 bigblue3; do
  for v in gmono warm warmmono; do
    run $EXP/configs/${d}_${v}.json $EXP/logs/${d}_${v}.log ${v}/${d}
  done
done
for s in 2000 3000; do
  run $EXP/configs/adaptec4_seed_center_${s}.json   $EXP/logs/adaptec4_seed_center_${s}.log   seed_center_${s}
  run $EXP/configs/adaptec4_seed_conngrid_${s}.json $EXP/logs/adaptec4_seed_conngrid_${s}.log seed_conngrid_${s}
done
echo ALL_DONE >> $STATUS
