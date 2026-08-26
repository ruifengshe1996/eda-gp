#!/bin/bash
# Keep the results webUI alive: single-instance guard + respawn on crash.
# Start detached (survives ssh logout; rerun after a server reboot):
#   setsid nohup /public_data/sheruifeng/research/eda_gp/eda-gp/tools/webui/daemon.sh \
#     > /dev/null 2>&1 < /dev/null &
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
LOCK=$GP/tools/webui/.daemon.lock
LOG=$GP/tools/webui/webui.log

exec 9>"$LOCK"
flock -n 9 || { echo "webui daemon already running"; exit 0; }

while true; do
  "$GP/tools/webui/run.sh" >> "$LOG" 2>&1
  echo "[daemon] $(date +%FT%T) webui exited (rc=$?), restarting in 5s" >> "$LOG"
  sleep 5
done
