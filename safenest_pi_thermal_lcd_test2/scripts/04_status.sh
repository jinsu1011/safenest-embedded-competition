#!/usr/bin/env bash
set -u
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"; [[ -x "$PYTHON_BIN" ]] || PYTHON_BIN=python3
ss -ltnp 'sport = :8000 or sport = :9000' 2>/dev/null || true
ss -lunp 'sport = :5005' 2>/dev/null || true
curl -fsS http://127.0.0.1:8000/health | "$PYTHON_BIN" -m json.tool || exit 1
curl -fsS http://127.0.0.1:8000/api/lcd/thermal | "$PYTHON_BIN" -m json.tool
IP="$(hostname -I | awk '{print $1}')"
printf 'LCD: http://%s:8000/display\nDashboard: http://%s:8000/dashboard\n' "$IP" "$IP"
printf 'Admin: http://%s:8000/admin\nGuest Thermal: http://%s:8000/guest/dashboard/A01\n' "$IP" "$IP"
