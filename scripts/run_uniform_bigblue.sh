#!/bin/bash
# standalone driver: uniform-init runs for bigblue3/4, survives parent death
GP=/home/ruifengshe/research/eda/gp
cd $GP/install
export LD_LIBRARY_PATH=$GP/deps/local/lib:$GP/deps/cuda-11.8/lib64
for d in bigblue3 bigblue4; do
  rm -rf uniform_results/$d
  $GP/venv/bin/python dreamplace/Placer.py $GP/experiments/uniform_init/configs/$d.json \
      > $GP/experiments/uniform_init/logs/$d.log 2>&1
  echo "$d exit=$?" >> $GP/experiments/uniform_init/logs/driver_status.txt
done
echo "ALL_DONE" >> $GP/experiments/uniform_init/logs/driver_status.txt
