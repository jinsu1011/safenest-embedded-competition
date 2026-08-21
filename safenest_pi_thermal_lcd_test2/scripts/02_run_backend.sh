#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
[[ -x "${PYTHON_BIN}" ]] || { echo '먼저 bash scripts/01_install.sh를 실행하세요.' >&2; exit 1; }
if [[ -f "${ROOT_DIR}/.env" ]]; then set -a; source "${ROOT_DIR}/.env"; set +a; fi
cd "${ROOT_DIR}/RaspberryPi/Runtime"
"${PYTHON_BIN}" -m hil.preflight
exec "${PYTHON_BIN}" backend/run_backend.py --api-host 0.0.0.0 --api-port 8000 --sensor-host 0.0.0.0 --sensor-port 9000 --thermal-udp-host 0.0.0.0 --thermal-udp-port 5005 --evaluation-interval "${SAFENEST_EVALUATION_INTERVAL_SECONDS:-2.0}" --room "${SAFENEST_ROOM_NAME:-밀폐공간 A-01}"
