# SafeNest

밀폐공간 작업자 안전을 위한 엣지 AI 모니터링 시스템입니다. ESP32 센서 노드가 mmWave·Thermal·CO₂·PIR을 측정해 Raspberry Pi로 보내고, Pi가 On-device AI와 Rule Engine으로 위험도를 판정해 실시간 웹 대시보드에 표시합니다.

이 저장소는 여러 팀 저장소를 통합한 **canonical 통합 저장소**입니다. 각 컴포넌트의 상류 저장소와 정확한 commit SHA는 [`COMPONENT_SOURCES.json`](COMPONENT_SOURCES.json)에 기록되어 있습니다.

---

## 한 줄 실행

Raspberry Pi에서 아래 한 명령으로 전체 SafeNest 런타임이 기동됩니다.

```bash
./run_safenest.sh
```

최초 1회만 의존성을 설치합니다.

```bash
./run_safenest.sh --install
```

이 한 명령이 하나의 프로세스 트리 안에서 다음을 모두 띄웁니다.

| 구성 요소 | 역할 |
| --- | --- |
| SafeNest TCP v1 게이트웨이 (`:9000`) | mmWave·CO₂·PIR scalar telemetry 수신 |
| SafeNest Thermal UDP v1 수신기 (`:5005`) | 80×62 열화상 프레임 chunk 재조립 |
| Sensor State Manager | 센서별 최신값·freshness·유효성·device health |
| On-device AI 파이프라인 | `RaspberryPi/Ondevice_AI`의 TFLite 어댑터 지연 로드 |
| Rule / Risk Engine | 동결된 V4 risk 계약으로 `NORMAL/WARNING/DANGER` 판정 |
| SQLite | `RaspberryPi/Runtime/data/safenest.db` 스냅샷·이벤트 영속화 |
| FastAPI + WebSocket (`:8000`) | 통합 상태 API와 실시간 push |
| 실시간 웹 대시보드 | `http://<pi-주소>:8000/dashboard` |

여러 터미널을 열 필요가 없습니다. `Ctrl+C` 한 번으로 전체가 정상 종료됩니다.

### 접속 주소

| 대상 | URL |
| --- | --- |
| 관리자 웹 | `http://<pi-주소>:8000/admin` |
| A01 방문자 열화상 | `http://<pi-주소>:8000/guest/dashboard/A01` |
| 실시간 대시보드 | `http://<pi-주소>:8000/dashboard` |
| 통합 상태 API | `http://<pi-주소>:8000/api/status` |
| 센서 상세 | `http://<pi-주소>:8000/api/sensors` |
| 이력 / 이벤트 | `/api/history`, `/api/events` |
| 헬스체크 | `http://<pi-주소>:8000/health` |
| WebSocket | `ws://<pi-주소>:8000/ws` |

포트를 바꾸려면 인자를 그대로 전달합니다: `./run_safenest.sh --api-port 8080 --sensor-port 9100`

### 웹과 열화상 빠른 확인

Raspberry Pi OS에서 최초 1회 OS 패키지를 설치한 뒤 SafeNest를 시작합니다.

```bash
sudo apt update
sudo apt install -y python3-venv python3-pip python3-dev build-essential
./run_safenest.sh --install
```

`--install`은 가상환경과 Python 의존성을 설치한 다음 사전 점검을 거쳐 런타임까지 시작합니다. 이후 실행은 `./run_safenest.sh`만 사용합니다. 방화벽을 사용하면 브라우저용 TCP `8000`, scalar telemetry용 TCP `9000`, Thermal UDP `5005`를 허용합니다.

ESP32의 `secrets.h`에는 Pi의 실제 IP를 `RPI_HOST`로 넣고, 펌웨어의 `THERMAL_UDP_PORT`와 Pi의 `SAFENEST_THERMAL_UDP_PORT`를 동일한 `5005`로 유지합니다. 프레임 수신 여부는 다음처럼 확인합니다.

```bash
curl -fsS http://127.0.0.1:8000/health | python3 -m json.tool
curl -sS -D - -o /dev/null http://127.0.0.1:8000/api/thermal/A01
```

열화상 API가 `200`과 `application/octet-stream`을 반환하면 웹이 그릴 수 있는 완성 프레임이 있습니다. 아직 프레임이 없으면 `204`가 정상적으로 반환됩니다. 자세한 순서는 [`RaspberryPi/Runtime/docs/WEB_THERMAL_RUNBOOK_KO.md`](RaspberryPi/Runtime/docs/WEB_THERMAL_RUNBOOK_KO.md)를 따릅니다.

---

## 저장소 구조

```
ESP32/
├── Arduino/esp32_sensor_node/    canonical 플래시 소스 (4개 센서 통합 노드)
├── docs/COMMUNICATION_PROTOCOL.md  ESP32 ↔ Pi 프로토콜 계약
├── reference/mmwave_platformio/  mmWave 단독 PlatformIO 참조 펌웨어
└── secret.h.example              Wi-Fi/Pi 주소 템플릿 (실제 값은 커밋 금지)

RaspberryPi/
├── Ondevice_AI/                  On-device AI 상류 권위 소스 (sheepmeat/test)
├── LCD/                          Pi LCD 키오스크 (레거시 독립 경로, 아래 주의)
├── Web/                          실시간 관제 대시보드 정적 자산
└── Runtime/                      Pi 런타임 (게이트웨이·상태·AI·risk·backend·DB)

research/
├── thermal_ai/                   Thermal 오프라인 데이터셋/모델 연구 (런타임 아님)
└── co2_validation/               CO₂ 측정·검증 도구와 세션 fixture (런타임 아님)

archive/                          과거 구현·측정 증거 보존 (런타임이 참조하지 않음)
hardware/                         하우징 3D 모델
COMPONENT_SOURCES.json            컴포넌트별 상류 저장소와 commit SHA
run_safenest.sh                   단일 실행 진입점
```

### 구조 예외 (STRUCTURE_EXCEPTION)

기본 목표 구조는 `RaspberryPi/{Ondevice_AI, LCD, Web}`였지만, 기술적으로 다음 디렉터리를 추가했습니다.

| 디렉터리 | 책임 | 왜 필요한가 |
| --- | --- | --- |
| `RaspberryPi/Runtime/` | 게이트웨이, 센서 상태, AI 오케스트레이션, Risk, FastAPI, SQLite, 서비스, 배포 | 이 코드는 특정 센서나 UI가 아니라 **셋을 연결하는 런타임**입니다. `Ondevice_AI`에 넣으면 상류 저장소를 오염시키고, `Web`에 넣으면 UI가 게이트웨이를 소유하게 됩니다. 이게 없으면 단일 명령 실행 자체가 성립하지 않습니다. |
| `research/` | Thermal·CO₂ 오프라인 모델/데이터 연구 워크스페이스 | 두 상류 저장소가 스스로 "펌웨어 통합·위험도 판단은 범위 밖"이라고 명시합니다. 런타임에 섞으면 미검증 모델이 배포 경로로 오해됩니다. |
| `ESP32/docs`, `ESP32/reference` | 프로토콜 계약 문서, mmWave 참조 펌웨어 | 계약 테스트가 이 파일들을 읽습니다. `archive/`에 두면 활성 테스트가 archive에 의존하게 되어 금지된 구조가 됩니다. |
| `hardware/` | 하우징 STL | ESP32도 Pi도 소유하지 않는 물리 설계 자산입니다. |

---

## 데이터 흐름

```
ESP32 센서 노드
  ├─ mmWave (MR60BHA2, UART)  ─┐
  ├─ CO₂ (SCD4x, I2C)          ├─ JSON telemetry ─→ SafeNest TCP v1 :9000 ─┐
  └─ PIR (GPIO)               ─┘                                            │
  └─ Thermal (MI48xx, SPI) ─ 80×62 uint16 ─→ Thermal UDP v1 :5005 ─────────┤
                                                                            ▼
                                                     RaspberryPi/Runtime/gateway
                                                                            │
                                                     state/manager.py (freshness·유효성)
                                                                            │
                                              ai/pipeline.py ──→ Ondevice_AI TFLite
                                                                            │
                                              risk/engine.py (V4 가중치·임계값)
                                                                            │
                                     backend/store.py → database/ (SQLite)  │
                                                                            ▼
                                            backend/app.py (FastAPI + /ws)
                                                                            │
                                                          RaspberryPi/Web 대시보드
```

활성 진입점은 하나뿐입니다: `RaspberryPi/Runtime/backend/run_backend.py`. 컴포넌트 간 경로는 전부 `RaspberryPi/Runtime/paths.py`가 해석합니다.

---

## 설치와 실행

### 1. ESP32 펌웨어 플래시

1. Arduino IDE에서 `ESP32/Arduino/esp32_sensor_node/esp32_sensor_node.ino`를 엽니다.
2. 자격증명 파일을 스케치 폴더에 만듭니다. **이 파일은 Git에 커밋되지 않습니다.**
   ```bash
   cp ESP32/secret.h.example ESP32/Arduino/esp32_sensor_node/secrets.h
   ```
3. `secrets.h`를 열어 2.4 GHz Wi-Fi SSID/비밀번호와 Raspberry Pi의 IP를 채웁니다.
4. 보드를 `ESP32 Dev Module`로 선택하고 업로드합니다.
5. 필요한 라이브러리: `SensirionI2cScd4x`, `Seeed_Arduino_mmWave`.

배선과 패킷 형식은 [`ESP32/docs/COMMUNICATION_PROTOCOL.md`](ESP32/docs/COMMUNICATION_PROTOCOL.md)를 따릅니다.

### 2. Raspberry Pi 준비

```bash
git clone https://github.com/jinsu1011/safenest-embedded-competition.git
cd safenest-embedded-competition
./run_safenest.sh --install   # .venv 생성 + 의존성 설치
./run_safenest.sh             # 실행
```

의존성은 `RaspberryPi/Runtime/requirements-backend.txt`(FastAPI/uvicorn)와 `RaspberryPi/Ondevice_AI/requirements-pi.txt`(ai-edge-litert, numpy 등)에서 옵니다.

### 3. 선택: 비상 대응 설정

SMS·부저를 쓰려면 저장소 루트에 `.env`를 만듭니다. 템플릿은 [`RaspberryPi/Runtime/.env.example`](RaspberryPi/Runtime/.env.example)입니다. `.env`는 Git에 올라가지 않습니다.

---

## 실패 동작

시스템은 **fail-closed**입니다. 값을 지어내지 않습니다.

| 상황 | 동작 |
| --- | --- |
| 센서 패킷이 끊김 | 해당 센서가 `STALE` → `DISCONNECTED`. 마지막 값을 현재값으로 쓰지 않음 |
| 잘못된 패킷 수신 | 해당 연결만 끊고 `protocol_errors` 증가. 서비스는 계속 동작 |
| 모델 로드 실패 | 해당 센서만 `MODEL_RUNTIME_UNAVAILABLE`, 나머지는 계속 평가 |
| 전 컴포넌트 불가 | `risk_level = null` + `ALL_RISK_COMPONENTS_UNAVAILABLE`. 임의 점수를 만들지 않음 |
| 필수 설정 누락 | 기동 시 명시적 오류 |

`system_health`가 `DEGRADED`/`FAILED`인데 `risk_level`이 `NORMAL`이면, 그것은 "안전 확인"이 아니라 "판정 근거 부족"입니다.

---

## AI 모델 상태

**중요: 이 저장소의 어떤 모델도 실기기에서 검증되지 않았습니다.** 통합 과정에서 모델을 자동 승격하지 않았습니다.

| 센서 | 런타임 모델 | 상태 |
| --- | --- | --- |
| Thermal | `thermal_fall_int8_v0.1.0` | candidate, `CONFIRMED_SYNTHETIC_ONLY` |
| CO₂ | `co2_occupancy_int8_v0.1.0` | candidate, `CONFIRMED_SYNTHETIC_ONLY` |
| mmWave | `mmwave_resp_int8_v0.1.0` | **배포 차단** (`deployment_allowed: false`, `CLASS_COLLAPSE_ON_REPOSITORY_NPZ`) |
| mmWave v0.2.0 | `mmwave_resp_int8_v0.2.0_candidate` | candidate, `SYNTHETIC_SMOKE_ONLY`, 하드웨어 검증 `BLOCKED_HARDWARE` — 런타임 기본값으로 승격하지 않음 |
| PIR | 없음 | AI 모델 없음. Rule 전용 센서 |

용어를 구분합니다: 새 모델 파일 ≠ 검증된 모델, offline candidate ≠ 런타임 기본값, 런타임 기본값 ≠ 실기기 검증 완료.

권위 있는 상태는 [`RaspberryPi/Ondevice_AI/models/model_manifest.json`](RaspberryPi/Ondevice_AI/models/model_manifest.json)입니다.

---

## 검증

```bash
cd RaspberryPi/Runtime
python -m unittest discover -s tests -p "test_*.py" -v   # 151개 테스트
python deployment/verify_bundle.py                        # 필수 파일 + 모델 SHA-256
python -m hil.preflight                                   # Pi 환경 사전 점검
```

`tests/test_end_to_end.py`는 실제 TCP loopback으로 게이트웨이→AI→Risk→SQLite→API view 전체를 통과시킵니다. 이는 **소프트웨어 E2E**이며, 실제 센서 하드웨어 검증이 아닙니다. 하드웨어 검증 절차는 [`RaspberryPi/Runtime/docs/HIL_ACCEPTANCE.md`](RaspberryPi/Runtime/docs/HIL_ACCEPTANCE.md)에 있습니다.

---

## 주의사항

### LCD는 단일 명령에 포함되지 않습니다

`RaspberryPi/LCD/server.py`는 **자체 TCP `:9000` 수신기와 자체 `state.json`을 가진 독립 구현**입니다. canonical 게이트웨이와 포트가 충돌하고 상태 소스가 이중화되므로 `run_safenest.sh`가 실행하지 않습니다. Pi의 물리 LCD는 브라우저로 `http://localhost:8000/dashboard`를 띄우는 방식을 권장합니다.

같은 이유로 `research/co2_validation/pi/safenest_pi_service.py`(CO₂ 전용 `:9000` 수신기)도 런타임과 동시에 실행하면 안 됩니다.

### archive는 런타임이 참조하지 않습니다

`archive/`는 과거 구현·측정 증거 보존 전용입니다. 활성 런타임은 archive를 import하지도, 설정·모델을 읽지도 않습니다.

---

## 상류 저장소 동기화

| 컴포넌트 | 상류 | 통합 commit |
| --- | --- | --- |
| On-device AI | `sheepmeat/test` | `4129753e64e0f18a3491e5b6cc0454b0d36f1610` |
| 런타임·게이트웨이·backend·DB·Web | `yuname121/integration` | `9e4ddfe770d505266f33b39dfe9ba8ec86099f82` |
| Thermal 연구 | `yuname121/safenest-thermal-ai` | `db51112bfd02cdda2d41e99cf11acde75f771ecf` |
| CO₂ 측정·검증 | `yuseungha/Sandi-2026_summer` | `145deac4cbec12ce6459cf5a6858cb0d0b1d06da` |
| 기존 메인 저장소 | `jinsu1011/safenest-embedded-competition` | `6fc04d6e9e09aa0baac96592eb374f6d3de6af07` |

상류 갱신을 반영할 때:

1. 상류 저장소를 clone하고 새 HEAD SHA를 확인합니다.
2. **런타임 임계 경로**(`inference/`, `config/`, `adapters/`, `models/model_manifest.json`)의 diff를 먼저 봅니다.
3. 모델 매니페스트의 `deployment_allowed`와 `validation_status`가 바뀌었는지 확인합니다. 최신이라는 이유만으로 승격하지 않습니다.
4. 파일을 반영하고 `COMPONENT_SOURCES.json`의 SHA를 갱신합니다.
5. `python -m unittest discover -s tests`와 `verify_bundle.py`를 돌려 모델 SHA-256이 매니페스트와 일치하는지 확인합니다.

---

## 문제 해결

| 증상 | 확인할 것 |
| --- | --- |
| 대시보드가 "WebSocket 오프라인" | 백엔드가 살아있는지 `curl localhost:8000/health` |
| 모든 센서가 `DISCONNECTED` | ESP32의 `secrets.h` 속 Pi IP, 같은 2.4 GHz 네트워크인지, `:9000` 방화벽 |
| Thermal만 안 들어옴 | Thermal은 UDP `:5005`. TCP와 별도 포트입니다 |
| `virtual environment not found` | `./run_safenest.sh --install` 먼저 실행 |
| `port_9000_available: false` | LCD나 CO₂ 전용 서비스가 이미 `:9000`을 점유 중 |
| mmWave AI가 `INPUT_UNAVAILABLE` | 정상입니다. B-model은 300-sample 호흡 phase window를 요구하며 현재 펌웨어는 vendor scalar만 보냅니다 (`PENDING_MMWAVE_DEVICE_CONTRACT_VALIDATION`) |

---

## 기여

브랜치 규칙과 리뷰 절차는 [`CONTRIBUTING.md`](CONTRIBUTING.md)를 따릅니다. 단계별 통합 근거는 [`RaspberryPi/Runtime/docs/`](RaspberryPi/Runtime/docs/)에 PHASE 1~10으로 정리되어 있습니다.
