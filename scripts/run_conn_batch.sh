#!/bin/bash
GP=/home/ruifengshe/research/eda/gp
cd $GP/install
export LD_LIBRARY_PATH=$GP/deps/local/lib:$GP/deps/cuda-11.8/lib64
for d in adaptec1 adaptec2 adaptec3 adaptec4 bigblue1 bigblue2 bigblue3 bigblue4; do
  rm -rf conn_results/$d
  $GP/venv/bin/python dreamplace/Placer.py $GP/experiments/conn_grid_init/configs/$d.json \
      > $GP/experiments/conn_grid_init/logs/$d.log 2>&1
  echo "$d exit=$?" >> $GP/experiments/conn_grid_init/logs/driver_status.txt
done
echo "ALL_DONE" >> $GP/experiments/conn_grid_init/logs/driver_status.txt
