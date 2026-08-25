#!/bin/bash
# Experiment 6 driver: conn-shrink. Same queue discipline as experiment 3:
# wait for quiet, then hold flock on ../gpu0.lock for the whole batch.
set -u
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
source $GP/env.sh
cd $GP/install
EXP=$GP/experiments/conn_shrink
STATUS=$EXP/logs/driver_status.txt
LOCK=/public_data/sheruifeng/research/eda_gp/gpu0.lock
mkdir -p $EXP/logs
: > $STATUS
export CUDA_VISIBLE_DEVICES=0

quiet=0
while true; do
  if pgrep -f "dreamplace/Placer[.]py" > /dev/null; then
    quiet=0
  else
    quiet=$((quiet + 1))
    [ $quiet -ge 3 ] && { echo "quiet, proceeding" >> $STATUS; break; }
  fi
  sleep 60
done

run() {
  if grep -q "wHPWL" "$2" 2>/dev/null && grep -q "placement takes" "$2" 2>/dev/null; then
    echo "$3 skip (done)" >> $STATUS; return 0
  fi
  python dreamplace/Placer.py "$1" > "$2" 2>&1
  echo "$3 exit=$?" >> $STATUS
}

exec 9>"$LOCK"
flock 9
echo "acquired gpu0.lock" >> $STATUS

for d in adaptec1 adaptec2 adaptec4 bigblue3 bigblue4; do
  for s in s001 s010; do
    run $EXP/configs/${d}_${s}.json $EXP/logs/${d}_${s}.log ${s}/${d}
  done
done
echo ALL_DONE >> $STATUS
