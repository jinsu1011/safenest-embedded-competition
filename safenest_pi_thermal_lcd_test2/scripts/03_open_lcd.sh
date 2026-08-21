#!/usr/bin/env bash
set -Eeuo pipefail
URL="${SAFENEST_LCD_URL:-http://127.0.0.1:8000/display}"
if command -v chromium >/dev/null; then BROWSER="$(command -v chromium)"; elif command -v chromium-browser >/dev/null; then BROWSER="$(command -v chromium-browser)"; else echo 'Chromium이 없습니다.' >&2; exit 1; fi
for _ in $(seq 1 40); do curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1 && break; sleep 0.5; done
curl -fsS http://127.0.0.1:8000/health >/dev/null || { echo '백엔드 준비 실패' >&2; exit 1; }
export DISPLAY="${DISPLAY:-:0}"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
[[ -S "${XDG_RUNTIME_DIR}/bus" ]] && export DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-unix:path=${XDG_RUNTIME_DIR}/bus}"
exec "${BROWSER}" --kiosk --app="${URL}" --noerrdialogs --disable-infobars --disable-session-crashed-bubble --ozone-platform-hint=auto
