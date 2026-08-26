#!/bin/bash
# conn-y bug rebuild driver: rerun the conn-family variants on the fixed
# init path (434fa96). Order: shrink_adaptec4 scout first (most likely
# surprise point), then conn-grid x8 (foundation), shrink x7, obsfield x8,
# obsspread x8. Results go to fix_* result dirs (pre-fix dirs preserved).
# Serializes on the shared GPU-0 lock.
set -u
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
LOCK=/public_data/sheruifeng/research/eda_gp/gpu0.lock
source $GP/env.sh
cd $GP/install
EXP=$GP/experiments/conn_rebuild
STATUS=$EXP/logs/driver_status.txt
mkdir -p $EXP/logs/{conngrid,shrink001,obsfield,obsspread}
: > $STATUS
export CUDA_VISIBLE_DEVICES=0

run() {  # run <config-name> <logfile> <tag>
  if grep -q "wHPWL" "$2" 2>/dev/null && grep -q "placement takes" "$2" 2>/dev/null; then
    echo "$3 skip (done)" >> $STATUS; return 0
  fi
  flock "$LOCK" python dreamplace/Placer.py $EXP/configs/$1 > "$2" 2>&1
  echo "$3 exit=$?" >> $STATUS
}

DESIGNS="adaptec1 adaptec2 adaptec3 adaptec4 bigblue1 bigblue2 bigblue3 bigblue4"

run adaptec4_shrink001.json $EXP/logs/shrink001/adaptec4.log shrink001/adaptec4

for d in $DESIGNS; do run ${d}_conngrid.json  $EXP/logs/conngrid/$d.log  conngrid/$d;  done
for d in $DESIGNS; do run ${d}_shrink001.json $EXP/logs/shrink001/$d.log shrink001/$d; done
for d in $DESIGNS; do run ${d}_obsfield.json  $EXP/logs/obsfield/$d.log  obsfield/$d;  done
for d in $DESIGNS; do run ${d}_obsspread.json $EXP/logs/obsspread/$d.log obsspread/$d; done
echo ALL_DONE >> $STATUS
