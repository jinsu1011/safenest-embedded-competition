#!/usr/bin/env bash
# SafeNest single-command entry point for the Raspberry Pi.
#
#   ./run_safenest.sh --install   # first time only: create .venv and install deps
#   ./run_safenest.sh             # start the whole SafeNest runtime
#
# Starts, in one process tree:
#   - SafeNest TCP v1 gateway            (scalar mmWave / CO2 / PIR telemetry, :9000)
#   - SafeNest Thermal UDP v1 receiver   (chunked 80x62 thermal frames, :5005)
#   - Sensor State Manager               (freshness, validity, device health)
#   - On-device AI pipeline              (RaspberryPi/Ondevice_AI TFLite adapters)
#   - Rule / Risk engine                 (frozen V4 risk contract)
#   - SQLite persistence                 (RaspberryPi/Runtime/data/safenest.db)
#   - FastAPI backend + WebSocket        (:8000)
#   - Real-time web dashboard            (http://<pi>:8000/dashboard)
set -euo pipefail

REPOSITORY_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${REPOSITORY_ROOT}/RaspberryPi/Runtime/deployment/run_pi.sh" "$@"
