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

상세 진행 상황과 실패 이력은 [`docs/operations/PROJECT_PROGRESS.md`](docs/operations/PROJECT_PROGRESS.md), 재현 절차는 [`ondevice_ai/docs/MR60_INTEGRATION.md`](ondevice_ai/docs/MR60_INTEGRATION.md)를 참고하세요.

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

저장소는 **파일 종류가 아니라 기기와 책임 영역**을 기준으로 나눕니다. 사용자명 디렉터리는 만들지 않습니다.

```text
devices/                                 기기 담당자가 단독 책임지는 영역
├── co2/                                 CO2 드라이버·어댑터·배선          @yuseungha
├── pir/                                 PIR 어댑터·배선                   @yuname121
├── mmwave/                              MR60 펌웨어·어댑터·실측·설정      @jinsu1011
│   ├── firmware/                        ESP PlatformIO 프로젝트, logs/, analysis/
│   ├── src/                             Python 어댑터와 mock
│   ├── config/, tests/
├── thermal/                             Thermal-44 드라이버·프레임 파서    @rla1729
└── esp32_node/                          4센서 수집 노드 ESP32 펌웨어      @yuseungha
    └── firmware/                        esp32_sensor_node.ino, secrets.example.h

integration/                             Pi 수신·표시·경보 실행 계층       @yuseungha
├── pi_lcd/                              TCP 수신, LCD·열화상 화면, 부저, 테스트
├── web/                                 Express 통합 웹(관리자·방문자), QR
└── install_raspberry_pi.sh, start_all.sh   설치·일괄 기동

ondevice_ai/                             SafeNest V4 온디바이스 AI 전체    @sheepmeat @jinsu1011
├── config/                              센서·모델·위험도 설정
├── datasets/                            전처리 NPZ와 수집 매니페스트
├── models/                              TFLite 모델 3종과 메타데이터
├── src/
│   ├── sensors/                         V4 센서 registry·orchestration
│   ├── inference/                       TFLite interpreter와 모델 registry
│   ├── risk/                            멀티센서 위험도·fallback
│   ├── integrated_node/                 Raspberry Pi 통합 실행 노드
│   ├── training/                        학습·전처리
│   └── tools/                           아카이브·가이드·플로터
├── benchmarks/                          추론 지연 측정과 기준 결과
├── tests/                               V4 단위·통합 테스트
└── docs/                                V4 연동·인수인계 문서

hardware/3d_models/                      외함 STL CAD 4종                  @yuname121
shared/contracts/                        여러 영역이 공유하는 센서 계약    @sheepmeat @jinsu1011
docs/                                    사람이 읽는 문서
├── mmwave/                              MR60 인수인계·튜닝·검증 보고      @jinsu1011
├── esp32_node/                          ESP32 셋업·통신규격·통합 검증 기록 @yuseungha
├── operations/, architecture/, planning/, dashboard/   공통 운용·구조·기획
archive/                                 구형 prototype과 폐기 설정 보존   @jinsu1011
```

**코드는 `devices/<sensor>/`, 읽을 문서는 `docs/<sensor>/`** 로 나눕니다. 원본 로그와 분석 산출물은 문서가 아니므로 `devices/<sensor>/` 아래에 둡니다. 새 센서 문서를 추가할 때는 [`CONTRIBUTING.md`](CONTRIBUTING.md)의 배치 표를 따르고 `.github/CODEOWNERS`에 담당자를 한 줄 추가합니다.

의존 방향은 한쪽입니다. `devices/`가 `shared/contracts/`의 계약을 구현하고, `ondevice_ai/`가 그 계약과 기기 구현을 소비합니다. 반대로 `devices/`가 `ondevice_ai/`를 import하지 않습니다. `integration/`은 `devices/esp32_node/`가 보내는 텔레메트리를 소비하는 실행 계층이며 펌웨어를 import하지 않습니다.

각 최상위 디렉터리의 `README.md`에 목적, 허용·금지 파일, 입력·출력, 실행법, 담당자와 원본 브랜치·커밋이 기록돼 있습니다. 리뷰어 지정은 [`.github/CODEOWNERS`](.github/CODEOWNERS), 전체 이관 근거는 [`docs/architecture/BRANCH_PROVENANCE.md`](docs/architecture/BRANCH_PROVENANCE.md)를 확인하세요.

## ESP firmware

```bash
cd devices/mmwave/firmware
platformio run
platformio run --target upload
```

MR60 펌웨어 업데이트는 벽돌 위험이 있으므로 승인 없이 수행하지 않습니다.

## Terminal dashboard

```bash
cd devices/mmwave/firmware
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
.venv/bin/python -m pip install -r ondevice_ai/requirements-mac.txt
```

테스트는 책임 영역별로 나뉘어 있으며 둘 다 저장소 루트에서 실행합니다.

```bash
.venv/bin/python -m unittest discover -s ondevice_ai/tests -p "test_*.py"
.venv/bin/python -m unittest discover -s devices/mmwave/tests -p "test_*.py"
```

`integration/pi_lcd`의 테스트는 `server.py`를 직접 import하므로 해당 디렉터리에서 실행합니다. 표준 라이브러리만 사용하므로 가상환경이 없어도 됩니다.

```bash
cd integration/pi_lcd
PYTHONPATH=. python3 -m unittest discover -s tests -p "test_*.py"
```

통합 노드 실행은 다음과 같습니다.

```bash
.venv/bin/python -m ondevice_ai.src.integrated_node.run_demo
.venv/bin/python -m ondevice_ai.src.integrated_node.run_node --mode mock
```

Raspberry Pi에서는 `ondevice_ai/requirements-pi.txt`를 사용합니다. 모든 명령은 저장소 루트에서 실행하며, 모델·데이터셋·설정 경로는 `ondevice_ai/` 패키지를 기준으로 해석합니다.

## Team workflow

팀 협업 규칙은 [`CONTRIBUTING.md`](CONTRIBUTING.md)를 따릅니다. 기능 변경은 별도 브랜치와 Pull Request로 공유하고, 실측 원본과 분석 결과를 함께 제출합니다.

### 내 코드 커밋 과정

`main`은 통합된 안정 상태이므로 직접 수정하거나 direct push하지 않습니다. 먼저 최신 상태에서 작업 목적에 맞는 브랜치를 만듭니다.

```bash
git switch main
git pull --ff-only origin main
git switch -c '<type>/<device-or-topic>-<short-description>'
```

브랜치 이름은 기능은 `feature/`, 버그 수정은 `fix/`, 실험은 `experiment/`, 구조 변경은 `refactor/`, 문서는 `docs/`를 접두어로 씁니다.

- `feature/co2-calibration`
- `fix/mmwave-serial-parser`
- `refactor/ondevice-ai-model-registry`
- `docs/hardware-assembly-guide`

수정 후에는 내가 바꾼 범위와 테스트 결과를 확인하고 관련 파일만 stage합니다. `git add .`는 쓰지 않습니다.

```bash
git status --short
git diff --check
python3 -m unittest discover -s ondevice_ai/tests -p "test_*.py"
python3 -m unittest discover -s devices/mmwave/tests -p "test_*.py"
git add <내가-수정한-파일>
git diff --cached
git commit -m "feat(co2): add validated sensor behavior"
git push -u origin '<branch-name>'
```

커밋 메시지는 `feat`, `fix`, `refactor`, `test`, `docs`, `chore` 같은 변경 유형과 짧은 scope를 사용합니다. 원본 데이터·모델·CAD를 변경했다면 출처와 SHA-256도 PR에 기록합니다.

### 내 담당 영역이 어디인지

본인 코드는 담당 기기 디렉터리 안에 둡니다. 사람 이름 폴더를 만들지 않습니다.

| 담당 | GitHub handle | 주 작업 경로 |
|---|---|---|
| Jinsu | `@jinsu1011` | `devices/mmwave/`, 통합, `docs/` |
| Junwoo | `@sheepmeat` | `ondevice_ai/`, `shared/contracts/` |
| Seungha | `@yuseungha` | `devices/co2/`, `devices/esp32_node/`, `integration/` |
| Taegyun | `@rla1729` | `devices/thermal/` |
| Yuna | `@yuname121` | `devices/pir/`, `hardware/3d_models/` |

[`.github/CODEOWNERS`](.github/CODEOWNERS)에 따라 해당 경로를 건드리는 PR에는 담당자가 자동으로 reviewer로 요청됩니다.

### Pull Request란 무엇이며 어떻게 만드는가

Pull Request(PR)는 작업 브랜치의 변경을 `main`에 반영해 달라고 요청하는 검토 단위입니다. 팀원은 PR에서 diff, 테스트 근거, 위험과 되돌리기 방법을 확인하고 의견을 남길 수 있으며, 승인과 필수 검사가 끝난 뒤에만 병합합니다.

1. GitHub 저장소의 **Compare & pull request**를 선택합니다.
2. base는 `main`, compare는 방금 push한 작업 브랜치로 지정합니다.
3. 제목에는 변경 목적을, 본문에는 아래를 씁니다.
   - 변경 목적과 변경 범위
   - 실행한 검증 명령과 **실제 출력** (통과한 테스트 수, skip, 실패)
   - 하드웨어에 미치는 영향
   - 남은 위험과 롤백 방법
   - reviewer
4. CODEOWNERS가 지정한 담당자가 reviewer로 요청됩니다. 다른 영역을 함께 건드렸다면 그 담당자도 직접 추가합니다.
5. CI와 리뷰 지적 사항을 반영합니다.
6. 승인 후 팀 규칙에 맞게 merge하며, `main` direct push, force push, 다른 사람의 원격 브랜치 삭제는 하지 않습니다.

PR을 올리기 전에 두 테스트 수트를 모두 실행하고 결과를 그대로 적습니다. 실행하지 않은 테스트를 통과했다고 쓰지 않습니다.

GitHub CLI를 사용하는 경우 `gh pr create --base main --head '<branch-name>' --fill`로 생성할 수 있습니다.
