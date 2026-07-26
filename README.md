# SafeNest

SafeNest는 mmWave 레이더, 열화상, PIR, CO2 센서를 Raspberry Pi 5에서 융합해 밀폐공간·차량 내부의 정지 인체와 위험 상태를 감지하는 엣지 안전 시스템입니다.

## Architecture

```text
MR60BHA2 ─UART─> ESP32 ─telemetry─> Raspberry Pi 5
                                       ├─ sensor fusion
Thermal / PIR / CO2 ───────────────────┤
                                       ├─ risk engine
                                       ├─ SQLite
                                       └─ alarm / display / dashboard
```

- ESP32: 센서 수집, UART 검증, 유효성 판정, 최소 필터, 패킷화
- Raspberry Pi 5: 센서융합, AI, 정상·주의·위험 판정, 저장 및 경보
- 결측·0·NaN·timeout은 정상값이나 무호흡으로 변환하지 않습니다.

## Current scope

- ESP-WROOM-32 + MR60BHA2 UART 수집 및 체크섬/파싱 계측
- 재실·거리·호흡·심박·phase 원시 텔레메트리
- 무필터 기준선·진입/퇴장 실측 로그 및 분석 도구
- Raspberry Pi 규칙 기반 위험도 엔진과 단위 테스트
- Rich 기반 실시간 터미널 모니터

상세 진행 상황과 실패 이력은 [`PROJECT_PROGRESS.md`](PROJECT_PROGRESS.md), 재현 절차는 [`MMWAVE_HANDOFF.md`](MMWAVE_HANDOFF.md)를 참고하세요.

## Hardware wiring

| MR60BHA2 | ESP-WROOM-32 DevKit |
|---|---|
| 5V | VIN/5V |
| GND | GND |
| TX | GPIO16/RX2 |
| RX | GPIO17/TX2 |

- UART: 115200bps
- RX0/TX0은 사용하지 않습니다.
- Mac USB 하나로 ESP와 MR60에 전원을 공급하며 별도 5V를 동시에 연결하지 않습니다.

## Repository layout

```text
config/                                  Pi 위험도 규칙
firmware/esp_wroom32_mr60_monitor/       ESP 펌웨어·수집·분석·실측 로그
pi/                                      Raspberry Pi 위험도 엔진·테스트
HARDWARE_RUNBOOK.md                      배선·복구·실행 절차
MMWAVE_TUNING.md                         mmWave 측정·튜닝 원칙
PROJECT_PROGRESS.md                      날짜별 진행·실패·검증 기록
TEAM_OPERATING_MODEL.md                  팀 역할과 협업 원칙
```

## ESP firmware

```bash
cd firmware/esp_wroom32_mr60_monitor
platformio run
platformio run --target upload
```

MR60 펌웨어 업데이트는 벽돌 위험이 있으므로 승인 없이 수행하지 않습니다.

## Terminal dashboard

```bash
cd firmware/esp_wroom32_mr60_monitor
python3 -m venv .venv
.venv/bin/pip install -r requirements-dashboard.txt
.venv/bin/python mmwave_dashboard.py --port /dev/cu.usbserial-XXX --baud 115200
```

현재 포트는 재연결할 때 달라질 수 있습니다.

```bash
find /dev -maxdepth 1 -name 'cu.usb*' -print
```

## Validation principles

- 원본 JSONL 로그를 수정하지 않습니다.
- 기준선 없이 필터나 임계값을 확정하지 않습니다.
- 한 번에 필터 또는 임계값 하나만 변경합니다.
- 동일 원본 로그로 변경 전후 성능을 비교합니다.
- 환경 오탐을 긴 시간 필터로 숨기지 않습니다.
- 위험한 숨참기, 과호흡, 밀폐공간, 가스 주입 시험을 하지 않습니다.

## Target KPIs

- 30분 동안 ESP 재부팅 0회
- UART 프레임·체크섬·파싱 오류율 계측
- 안정된 정지 1인 재실 감지율 95% 이상 목표
- 워밍업 이후 재실 상태 전달 지연 2초 이하
- 필터 전후 표준편차·결측률·유효률·응답 지연 비교
- 설정·펌웨어·라이브러리 버전 재현 가능하게 기록

## Team workflow

팀 협업 규칙은 [`CONTRIBUTING.md`](CONTRIBUTING.md)를 따릅니다. 기능 변경은 별도 브랜치와 Pull Request로 공유하고, 실측 원본과 분석 결과를 함께 제출합니다.

