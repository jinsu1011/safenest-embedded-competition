#!/usr/bin/env bash
set -u
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AFTER_INSTALL="${1:-}"
failures=0
pass() { printf '[PASS] %s\n' "$1"; }
warn() { printf '[WARN] %s\n' "$1"; }
fail() { printf '[FAIL] %s\n' "$1"; failures=$((failures + 1)); }

[[ "$(uname -s)" == Linux ]] && pass "Linux" || fail "Raspberry Pi Linux에서 실행해야 합니다."
[[ "$(uname -m)" == aarch64 ]] && pass "64비트 ARM" || warn "Raspberry Pi OS 64-bit를 권장합니다: $(uname -m)"
if command -v python3 >/dev/null && python3 -c 'import sys; raise SystemExit(sys.version_info < (3,10))'; then pass "$(python3 --version)"; else fail "Python 3.10 이상 필요"; fi
for cmd in curl ss hostname; do command -v "$cmd" >/dev/null && pass "$cmd" || fail "필수 명령 없음: $cmd"; done
printf 'Pi IP: %s\n' "$(hostname -I 2>/dev/null || true)"

if command -v ss >/dev/null; then
  for port in 8000 9000; do ss -ltnH "sport = :${port}" 2>/dev/null | grep -q . && fail "TCP ${port} 사용 중" || pass "TCP ${port} 사용 가능"; done
  ss -lunH 'sport = :5005' 2>/dev/null | grep -q . && fail "UDP 5005 사용 중" || pass "UDP 5005 사용 가능"
fi

PYTHONDONTWRITEBYTECODE=1 python3 "${ROOT_DIR}/scripts/check_runtime_package.py" >/tmp/safenest_package_check.json 2>&1 && pass "필수 파일과 모델 SHA-256" || fail "패키지 검사 실패: /tmp/safenest_package_check.json"
if command -v chromium >/dev/null 2>&1 || command -v chromium-browser >/dev/null 2>&1; then pass "Chromium"; else warn "설치 스크립트가 Chromium 설치를 시도합니다."; fi
if [[ "${AFTER_INSTALL}" == --after-install || -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  [[ -x "${ROOT_DIR}/.venv/bin/python" ]] && "${ROOT_DIR}/.venv/bin/python" -c 'import fastapi,uvicorn,numpy,cv2,qrcode,ai_edge_litert' >/dev/null 2>&1 && pass "Python 필수 라이브러리" || fail "Python 라이브러리 import 실패"
fi
printf '실패: %d\n' "$failures"
(( failures == 0 ))
