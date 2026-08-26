#!/usr/bin/env bash
# Foreground launcher for the eda-gp result web UI (systemd-friendly).
# Binds 127.0.0.1:8377 only; access through an ssh tunnel, e.g.
#   ssh -L 8377:localhost:8377 h200
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$HERE/../.." && pwd)"
# shellcheck source=/dev/null
source "$REPO_ROOT/env.sh"
exec "$REPO_ROOT/venv/bin/python" "$HERE/app.py"
