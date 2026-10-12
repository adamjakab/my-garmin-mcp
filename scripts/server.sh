#!/usr/bin/env bash
# Background dev server control: scripts/server.sh start|stop|restart|status|logs
# No file watching: restart = pick up code changes.
set -euo pipefail
cd "$(dirname "$0")/.."

RUN_DIR=".run"
PID_FILE="$RUN_DIR/server.pid"
LOG_FILE="$RUN_DIR/server.log"
PORT="${PORT:-3334}"
mkdir -p "$RUN_DIR"

is_running() { [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; }

case "${1:-}" in
  start)
    if is_running; then echo "already running (pid $(cat "$PID_FILE"))"; exit 0; fi
    # exec so the recorded pid is the python process itself
    setsid bash -c 'echo $$ > "$0"; exec uv run --no-sync python -m my_garmin_mcp' "$PID_FILE" >"$LOG_FILE" 2>&1 < /dev/null &
    for _ in $(seq 1 100); do
      if curl -fs "http://127.0.0.1:$PORT/health" >/dev/null 2>&1; then echo "started (pid $(cat "$PID_FILE"))"; exit 0; fi
      sleep 0.2
    done
    echo "failed to start; log:" >&2; tail -20 "$LOG_FILE" >&2; exit 1 ;;
  stop)
    if is_running; then
      kill "$(cat "$PID_FILE")"
      for _ in $(seq 1 50); do is_running || break; sleep 0.1; done
      is_running && kill -9 "$(cat "$PID_FILE")"
      echo "stopped"
    else echo "not running"; fi
    rm -f "$PID_FILE" ;;
  restart) "$0" stop; "$0" start ;;
  status) if is_running; then echo "running (pid $(cat "$PID_FILE"))"; else echo "stopped"; exit 1; fi ;;
  logs) tail -n "${2:-50}" "$LOG_FILE" ;;
  *) echo "Usage: $0 start|stop|restart|status|logs" >&2; exit 2 ;;
esac
