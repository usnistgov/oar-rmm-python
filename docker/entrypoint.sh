#! /bin/bash
set -euo pipefail

host="${HOST:-0.0.0.0}"
port="${PORT:-8083}"
timeout="${TIMEOUT:-120}"
keep_alive="${KEEP_ALIVE:-5}"
log_level="${LOG_LEVEL:-info}"
app_module="app.main:app"

[ -n "${OAR_WORKING_DIR:-}" ] || OAR_WORKING_DIR="$(mktemp -d -t _oar-rmm-python.XXXXXX)"
[ -d "$OAR_WORKING_DIR" ] || { echo "oar-rmm-python: ${OAR_WORKING_DIR}: working directory does not exist"; exit 10; }
[ -n "${OAR_LOG_DIR:-}" ] || export OAR_LOG_DIR="$OAR_WORKING_DIR"

echo
echo "Working Dir: $OAR_WORKING_DIR"
echo "Access the RMM API at http://localhost:$port/"
echo

exec gunicorn -k uvicorn.workers.UvicornWorker "$app_module" \
  --bind "$host:$port" \
  --timeout "$timeout" \
  --keep-alive "$keep_alive" \
  --access-logfile - \
  --error-logfile - \
  --log-level "$log_level" \
  ${WEB_CONCURRENCY:+-w "$WEB_CONCURRENCY"}