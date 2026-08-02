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
- Thermal-44, CO2, mmWave INT8 TFLite 추론과 PIR 센서 어댑터
- V4 가중치 융합 위험도 엔진, 보수적 fallback 및 통합 노드
- Raspberry Pi 규칙 기반 위험도 엔진과 단위·통합 테스트
- Rich 기반 실시간 터미널 모니터

상세 진행 상황과 실패 이력은 [`docs/operations/PROJECT_PROGRESS.md`](docs/operations/PROJECT_PROGRESS.md), 재현 절차는 [`docs/ai/MR60_INTEGRATION.md`](docs/ai/MR60_INTEGRATION.md)를 참고하세요.

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
firmware/                                ESP32-C6 센서 노드 펌웨어·실측·분석
src/sensors/                             센서 드라이버와 데이터 어댑터
src/inference/                           TFLite interpreter와 모델 registry
src/risk/                                V4 멀티센서 위험도·fallback
src/integrated_node/                     Raspberry Pi 통합 실행 노드
models/                                  TFLite 모델 3종과 메타데이터
datasets/                                전처리 NPZ와 수집 매니페스트
hardware/3d_print/                       최신 STL CAD 4종
config/                                  센서·모델·위험도 설정
docs/                                    운용·AI·구조·기획 문서
tests/                                   Python 단위·통합·benchmark 테스트
archive/                                 구형 prototype과 폐기 설정 보존
```

각 최상위 디렉터리의 `README.md`에 입력·출력, 허용 파일, 실행법, 버전과 원본 브랜치가 기록돼 있습니다. 전체 이관 근거는 [`docs/architecture/BRANCH_PROVENANCE.md`](docs/architecture/BRANCH_PROVENANCE.md)를 확인하세요.

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

## Python setup and tests

macOS에서는 저장소 루트에서 다음과 같이 독립 환경을 만듭니다.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-mac.txt
.venv/bin/python -m unittest discover -s tests -p "test_*.py"
```

Raspberry Pi에서는 `requirements-pi.txt`를 사용합니다. 모델 파일과 매니페스트 경로는 항상 저장소 루트를 기준으로 해석합니다.

## Team workflow

팀 협업 규칙은 [`CONTRIBUTING.md`](CONTRIBUTING.md)를 따릅니다. 기능 변경은 별도 브랜치와 Pull Request로 공유하고, 실측 원본과 분석 결과를 함께 제출합니다.

### 내 코드 커밋 과정

`main`은 통합된 안정 상태이므로 직접 수정하거나 direct push하지 않습니다. 먼저 최신 상태에서 작업 목적에 맞는 브랜치를 만듭니다.

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/<sensor-or-feature>
```

브랜치 이름은 기능은 `feature/<topic>`, 버그 수정은 `fix/<issue>`, 실험은 `experiment/<topic>`, 구조 변경은 `refactor/<topic>` 규칙을 사용합니다. 예: `feature/co2-alert`, `fix/mmwave-timeout`, `refactor/integrated-v4-architecture`.

수정 후에는 내가 바꾼 범위와 테스트 결과를 확인하고 관련 파일만 stage합니다.

```bash
git status --short
git diff --check
python3 -m unittest discover -s tests -p "test_*.py"
git add <내가-수정한-파일>
git diff --cached
git commit -m "feat(sensor): add validated sensor behavior"
git push -u origin feature/<sensor-or-feature>
```

커밋 메시지는 `feat`, `fix`, `refactor`, `test`, `docs`, `chore` 같은 변경 유형과 짧은 scope를 사용합니다. 원본 데이터·모델·CAD를 변경했다면 출처와 SHA-256도 PR에 기록합니다.

### Pull Request란 무엇이며 어떻게 만드는가

Pull Request(PR)는 작업 브랜치의 변경을 `main`에 반영해 달라고 요청하는 검토 단위입니다. 팀원은 PR에서 diff, 테스트 근거, 위험과 되돌리기 방법을 확인하고 의견을 남길 수 있으며, 승인과 필수 검사가 끝난 뒤에만 병합합니다.

1. GitHub 저장소의 **Compare & pull request**를 선택합니다.
2. base는 `main`, compare는 방금 push한 작업 브랜치로 지정합니다.
3. 제목에는 변경 목적을, 본문에는 변경 파일·실행한 테스트·결과·원본 로그/자산·남은 위험·롤백 방법을 씁니다.
4. 관련 담당자를 reviewer로 지정하고 CI 및 리뷰 수정 사항을 반영합니다.
5. 승인 후 팀 규칙에 맞게 merge하며, 원격 브랜치 삭제나 force push는 팀장 승인 없이 하지 않습니다.

GitHub CLI를 사용하는 경우 `gh pr create --base main --head feature/<sensor-or-feature> --fill`로 생성할 수 있습니다.
