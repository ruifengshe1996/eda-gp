#!/bin/bash
# Honors the agreed batch order without a reply channel:
#   e0 schedule_warmup (running) -> asus field_gate -> this session's gift_init.
# flock in run_all.sh is the hard guarantee; this watcher only preserves order.
GP=/public_data/sheruifeng/research/eda_gp/eda-gp
WLOG=$GP/experiments/gift_init/queue_watcher.log
log() { echo "$(date '+%F %T') $1" >> $WLOG; }

WARM=$GP/experiments/schedule_warmup/logs/driver_status.txt
log "waiting for schedule_warmup ALL_DONE"
for i in $(seq 1 180); do grep -q ALL_DONE $WARM 2>/dev/null && break; sleep 120; done
log "schedule_warmup done (or 6h timeout)"

# window for field_gate batch to appear, then to finish
FG=""
for i in $(seq 1 60); do
  FG=$(ls $GP/experiments/*gate*/logs/driver_status.txt 2>/dev/null | head -1)
  [ -n "$FG" ] && break
  sleep 120
done
if [ -n "$FG" ]; then
  log "field_gate status found: $FG; waiting for ALL_DONE"
  for i in $(seq 1 120); do grep -q ALL_DONE $FG 2>/dev/null && break; sleep 120; done
  log "field_gate done (or 4h timeout)"
else
  log "no field_gate batch appeared within 2h; proceeding (flock still serializes)"
fi

log "launching gift_init run_all.sh"
$GP/experiments/gift_init/run_all.sh
log "gift_init driver exited"
