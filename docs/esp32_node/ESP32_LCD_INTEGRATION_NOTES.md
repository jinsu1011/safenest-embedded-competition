# ESP32 → Raspberry Pi → 상태 판정 → LCD 통합 작업 노트

ESP32 실측 센서값이 라즈베리파이의 기존 판정 로직을 거쳐 LCD 화면을 자동으로
바꾸도록 연결한 작업입니다. 기존 파일 구조와 아키텍처는 유지했고, 끊겨 있던
연결점만 최소 수정했습니다.

실제 하드웨어(ESP32 + Raspberry Pi 5 + LCD)에서 검증했습니다.

## 1. 최종 데이터 흐름

```
ESP32 (esp32_sensor_node.ino)
  → TCP :9000, safenest.telemetry.v1 JSON (1초 주기)
  → SensorReceiver._handle_connection() → SensorStore.record_telemetry()   [server.py]
  → GET /api/state (HTTP :8080)
  → pollRaspberryPi() 1초 폴링                                             [SafeNest_Web/server.js]
  → normalizeReading() → evaluate() / riskScore()   (기존 판정 로직, 미변경)
  → 상태 변경 감지 (previousStatus !== item.status)
  → pushBridgeState()  ← 이번에 추가한 연결부
  → POST /api/state
  → apply_state_change() → state.json 저장 + 부저 동기화                   [server.py]
  → display.html 이 /api/state 를 폴링해 렌더링
```

## 2. 핵심 문제와 해결

### 2-1. 판정 결과가 LCD로 가지 않았음 (본 작업의 핵심)

`integration/web/server.js` 가 ESP32 실측값으로 `evaluate()` 를 매초 실행해
상태를 정확히 계산하고 있었지만, 그 결과를 어디에도 전달하지 않았습니다.
LCD가 읽는 `APP_STATE` 는 `/control` 화면의 수동 POST로만 바뀌는 별개 상태였습니다.

→ `pushBridgeState()` 를 추가해, 이미 존재하던 `POST /api/state` 엔드포인트로
계산된 상태를 전달합니다. 상태가 **바뀔 때만** 호출하므로 LCD 불필요 갱신이 없습니다.

### 2-2. ESP32 재부팅 시 센서 수신이 영구 정지

`_handle_connection()` 이 `socket.timeout` 에서 `continue` 만 반복해, 재부팅으로
생긴 half-open 소켓을 영원히 붙들고 새 연결을 accept하지 않았습니다.
실제로 재현되어 서버 재시작 전까지 복구 불가였습니다.

→ 유휴 타임아웃과 패킷 중간 끊김 감지를 추가했습니다. 회귀 테스트 2건 포함.

### 2-3. 열화상 카메라가 인식되지 않음 (실은 배선 정상)

`initializeThermalCamera()` 가 **리셋 펄스를 주기 전에** I²C 주소를 조회하고
있었습니다. 카메라는 리셋 후에만 응답하므로 항상 not found 였습니다.

→ 리셋을 프로브보다 먼저 수행. `[thermal] ready: addr=0x40 fw=3.2.13` 확인.

### 2-4. CO₂ 센서가 0을 반환

I²C 400 kHz가 브레드보드 배선에서 전송을 깨뜨리고 있었습니다.
(SPI를 1 MHz로 낮춘 기존 주석과 같은 이유)

→ 100 kHz로 낮추자 CO₂가 정상 동작(700~900 ppm)했습니다.

### 2-5. 열화상 프레임이 링크를 마비시킴

9.9 KB 프레임을 ESP32가 3초 안에 전송하지 못하고 중간에 끊어, 텔레메트리까지
45초당 6회 끊겼습니다. 게다가 배열의 약 70%가 죽은 값(−65 ℃)이라
영상 자체가 사용 불가였습니다.

→ 프레임 스트리밍을 끄고(`THERMAL_STREAM_FRAMES = false`), **최고 온도만**
기존 1초 텔레메트리 JSON에 `thermal_max_c` 필드로 실어 보냅니다.
연결 끊김이 0회가 되었습니다.

노이즈 픽셀 하나가 "고열"로 오판되는 것을 막기 위해, 단일 최댓값이 아니라
**살아있는 픽셀 중 상위 16개의 최저값**을 보고합니다.

## 3. 변경한 파일

| 파일 | 변경 내용 |
| --- | --- |
| `integration/web/server.js` | `pushBridgeState()` 추가, 상태 변경 시에만 LCD 갱신 |
| `integration/pi_lcd/server.py` | 유휴/중간끊김 감지, 소켓 타임아웃 정합, `thermal_max_c` 수신, 죽은 픽셀 제외 |
| `integration/pi_lcd/static/display.html` | `최고 온도` 타일 추가 |
| `integration/pi_lcd/static/common.css` | 타일 개수에 맞춰 한 줄 배치 |
| `integration/pi_lcd/start_lcd.sh` | 키오스크 화면을 가리던 번역 팝업 차단 |
| `integration/pi_lcd/tests/test_sensor_receiver.py` | 회귀 테스트 3건 추가 (총 13건) |
| `devices/esp32_node/firmware/esp32_sensor_node.ino` | 열화상 리셋 순서, I²C 100 kHz, 최고 온도 전송 |

경로는 이 저장소 기준입니다. 원본 작업은 `yuseungha/safenest-embedded-competition@0992a6d`에서
`yuseungha/` 아래 평면 구조로 이루어졌고, 이 저장소로 옮기면서 `CONTRIBUTING.md`의 배치 표에 맞게
기기 영역과 통합 영역으로 나누었습니다.

기존 AI/판정 로직(`evaluate()`, `riskScore()`)과 상태 구조
(`normal-empty` / `normal-occupied` / `warning` / `danger` / `emergency` / `offline`)는
변경하지 않고 그대로 재사용했습니다.

## 4. 검증 결과

| 항목 | 결과 |
| --- | --- |
| ESP32 수신 | PASS (실제 하드웨어) |
| parsing / preprocessing | PASS |
| 상태 판정 | PASS |
| LCD 자동 전환 | PASS — `normal-occupied` / `danger` / `warning` / `offline` 실제 화면 확인 |
| 상태 동일 시 미갱신 | PASS — 25회 폴링 중 센서값이 계속 변해도 LCD 쓰기 0회 |
| malformed input | PASS (4종 모두 400, 서버 생존) |
| ESP32 재부팅 복구 | PASS |
| 자동 테스트 | 13건 전부 통과 (PC·라즈베리파이 양쪽) |

## 5. 알려진 한계

- **열화상 배열이 부분적으로만 동작합니다.** 픽셀의 약 70%가 −65 ℃ 고정값이고,
  살아있는 30%로 최고 온도를 산출합니다. 값이 16~35 ℃ 사이에서 흔들리며
  가끔 튀면 `warning` 으로 잠깐 넘어갑니다. 워치독을 끄고 4분 관찰 시
  살아있는 픽셀이 0% → 29%까지만 회복되었습니다(정상은 95% 이상).
  배선이 정상이라면 센서 전원 용량을 점검할 필요가 있습니다.
- **호흡수에 노이즈가 있습니다** (1~29 rpm 진동). `resp < 10` 이 `danger` 조건이라
  상태가 자주 바뀝니다. 이동평균 등 평활화는 판정 민감도를 바꾸므로 적용하지 않았습니다.
- 열화상 프레임 스트리밍은 `THERMAL_STREAM_FRAMES = true` 한 줄로 되돌릴 수 있습니다.

## 6. 실행 방법

```bash
bash integration/install_raspberry_pi.sh
```

```bash
bash integration/start_all.sh
```

`devices/esp32_node/firmware/secrets.example.h` 를 같은 폴더의 `secrets.h` 로 복사한 뒤 Wi-Fi SSID·비밀번호와
`RPI_HOST`(라즈베리파이 IP)를 채워야 합니다. `secrets.h` 는 `.gitignore` 로 제외되어
저장소에 올라가지 않습니다.
