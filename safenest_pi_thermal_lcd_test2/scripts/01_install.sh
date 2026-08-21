#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
[[ "$(uname -s)" == Linux ]] || { echo 'Pi Linux에서 실행하세요.' >&2; exit 1; }
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip python3-dev build-essential curl iproute2 ca-certificates
if ! command -v chromium >/dev/null 2>&1 && ! command -v chromium-browser >/dev/null 2>&1; then sudo apt-get install -y chromium || sudo apt-get install -y chromium-browser; fi
python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/python" -m pip install --upgrade pip setuptools wheel
"${VENV_DIR}/bin/python" -m pip install -r "${ROOT_DIR}/RaspberryPi/Ondevice_AI/requirements-pi.txt" -r "${ROOT_DIR}/RaspberryPi/Runtime/requirements-backend.txt"
"${VENV_DIR}/bin/python" -c 'import fastapi,uvicorn,numpy,cv2,qrcode,ai_edge_litert; print("Python imports: OK")'
PYTHONDONTWRITEBYTECODE=1 python3 "${ROOT_DIR}/scripts/check_runtime_package.py"
chmod +x "${ROOT_DIR}/run_safenest.sh" "${ROOT_DIR}"/scripts/*.sh
