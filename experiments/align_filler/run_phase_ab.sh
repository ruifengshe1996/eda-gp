#!/bin/bash
# Revised driver: phase A = N2 arm on remaining designs (adaptec2 last so the
# orphan in-flight run is skipped once complete); phase B = lambda force-ratio
# probe on adaptec1 (density_weight 8e-4 / 8e-3). N1-v1 lookup arms abandoned
# after falsification on adaptec1 (+22.5%).
set -u
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
LOCK=/public_data/sheruifeng/research/eda_gp/gpu0.lock
source $GP/env.sh
cd $GP/install
EXP=$GP/experiments/align_filler
STATUS=$EXP/logs/driver_status.txt
mkdir -p $EXP/logs/{n2,probe}
export CUDA_VISIBLE_DEVICES=0
run() {
  log=$EXP/logs/$2/$1.log
  if grep -q "wHPWL" "$log" 2>/dev/null && grep -q "placement takes" "$log" 2>/dev/null; then
    echo "$2/$1 skip (done)" >> $STATUS; return 0
  fi
  flock "$LOCK" python dreamplace/Placer.py $EXP/configs/$1_$3.json > "$log" 2>&1
  echo "$2/$1 exit=$?" >> $STATUS
}
for d in adaptec3 adaptec4 bigblue1 bigblue2 bigblue3 bigblue4 adaptec2; do run $d n2 n2; done
log=$EXP/logs/probe/adaptec1_c8em4.log
grep -q "placement takes" "$log" 2>/dev/null || { flock "$LOCK" python dreamplace/Placer.py $EXP/configs/adaptec1_c8em4.json > "$log" 2>&1; echo "probe/c8em4 exit=$?" >> $STATUS; }
log=$EXP/logs/probe/adaptec1_c8em3.log
grep -q "placement takes" "$log" 2>/dev/null || { flock "$LOCK" python dreamplace/Placer.py $EXP/configs/adaptec1_c8em3.json > "$log" 2>&1; echo "probe/c8em3 exit=$?" >> $STATUS; }
echo PHASE_AB_DONE >> $STATUS
