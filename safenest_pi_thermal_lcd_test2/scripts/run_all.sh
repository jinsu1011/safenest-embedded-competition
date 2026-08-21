#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="${ROOT_DIR}/logs"; mkdir -p "$LOG_DIR"
NO_KIOSK=false; [[ "${1:-}" == --no-kiosk ]] && NO_KIOSK=true
BACKEND_PID=''; KIOSK_PID=''
cleanup() { trap - EXIT INT TERM; [[ -n "$KIOSK_PID" ]] && kill "$KIOSK_PID" 2>/dev/null || true; [[ -n "$BACKEND_PID" ]] && kill "$BACKEND_PID" 2>/dev/null || true; }
trap cleanup EXIT INT TERM
bash "${ROOT_DIR}/scripts/02_run_backend.sh" > >(tee "${LOG_DIR}/backend.log") 2>&1 & BACKEND_PID=$!
for _ in $(seq 1 60); do curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 && break; kill -0 "$BACKEND_PID" 2>/dev/null || wait "$BACKEND_PID"; sleep 0.5; done
curl -fsS http://127.0.0.1:8000/health >/dev/null || { echo '백엔드 시작 실패' >&2; exit 1; }
IP="$(hostname -I | awk '{print $1}')"
printf 'TCP 9000 / UDP 5005 수신 시작\nLCD: http://%s:8000/display\nDashboard: http://%s:8000/dashboard\nAdmin: http://%s:8000/admin\nGuest Thermal: http://%s:8000/guest/dashboard/A01\n종료: Ctrl+C\n' "${IP:-127.0.0.1}" "${IP:-127.0.0.1}" "${IP:-127.0.0.1}" "${IP:-127.0.0.1}"
if [[ "$NO_KIOSK" == false ]]; then bash "${ROOT_DIR}/scripts/03_open_lcd.sh" >"${LOG_DIR}/kiosk.log" 2>&1 & KIOSK_PID=$!; fi
wait "$BACKEND_PID"
