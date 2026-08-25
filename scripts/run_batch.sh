#!/bin/bash
# usage: run_batch.sh <exp_dir>   (expects <exp_dir>/configs/<design>.json)
GP=/home/ruifengshe/research/eda/gp
EXP=$1
cd $GP/install
export LD_LIBRARY_PATH=$GP/deps/local/lib:$GP/deps/cuda-11.8/lib64
for d in adaptec1 adaptec2 adaptec3 adaptec4 bigblue1 bigblue2 bigblue3 bigblue4; do
  $GP/venv/bin/python dreamplace/Placer.py $EXP/configs/$d.json > $EXP/logs/$d.log 2>&1
  echo "$d exit=$?" >> $EXP/logs/driver_status.txt
done
echo "ALL_DONE" >> $EXP/logs/driver_status.txt
