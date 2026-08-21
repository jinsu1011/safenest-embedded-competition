#!/usr/bin/env bash
set -Eeuo pipefail
BASE="${SAFENEST_BASE_URL:-http://127.0.0.1:8000}"
TMP="$(mktemp --suffix=.jpg)"; trap 'rm -f "$TMP"' EXIT
curl -fsS "${BASE}/health" >/dev/null
curl -fsS "${BASE}/display" | grep -q thermal
curl -fsS "${BASE}/admin" >/dev/null
curl -fsS "${BASE}/guest/dashboard/A01" >/dev/null
curl -fsS "${BASE}/api/thermal/A01" >/dev/null
curl -fsS "${BASE}/api/lcd/thermal" | python3 -m json.tool >/dev/null
STATUS="$(curl -sS -o "$TMP" -w '%{http_code}' "${BASE}/api/lcd/thermal/image.jpg")"
[[ "$STATUS" == 200 ]] && echo '[PASS] 열화상 JPEG' || { [[ "$STATUS" == 503 ]] && echo '[WAIT] 첫 열화상 프레임 대기' || exit 1; }
echo '[PASS] Admin/Guest/Dashboard/LCD API'
