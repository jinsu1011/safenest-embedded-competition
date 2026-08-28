# 2026-08-28 Pi / ESP32 필드 작업 인수인계

- **작성일:** 2026-08-28 (KST)
- **대상 레포:** `jinsu1011/safenest-embedded-competition`
- **기준 커밋 (작업 시작 시 `main`):** `1df0c178b02d700f4893728b0a9b5836941b6adc` (`Merge pull request #49`)
- **본 PR 코드:** `RaspberryPi/Runtime/gateway/receiver.py` TCP 재접속 preempt
- **범위:** Raspberry Pi 런타임 통신·LCD 기동, ESP32 터미널 툴체인·플래시·시리얼 관측
- **범위 밖:** mmWave **모델/학습/추론** 문서. UART에서 값이 안 나온다는 **관측만** 적는다. 모델 담당 에이전트가 별도 작성한다.

이 문서는 채팅을 읽지 않은 팀원이 같은 장비에서 이어서 작업할 수 있게 쓴다.  
Wi-Fi 비밀번호, Pi SSH 비밀번호, `secrets.h` 원문은 **넣지 않는다.**

---

## 1. 한 줄 요약

Mac에서 Arduino IDE 없이 TEAM ESP32 스케치를 빌드·업로드할 수 있게 됐고, 필드 Pi(`192.168.137.189`)에 런타임을 붙여 관측했다.  
**TCP는 시작 직후 잠깐 붙었다가 페이로드 중간에 죽는다.** Pi 수신기가 끊긴 소켓을 붙잡고 재접속을 막던 문제는 이 PR로 고쳤다.  
그 핫패치는 재접속을 빨라지게만 하고, **Wi-Fi/TCP가 중간에 stall 하는 근본 원인은 남아 있다.**  
mmWave는 TCP가 살아 있던 구간에서도 Pi에 phase/presence/rate가 전부 `null`이었다. 모델 문제가 아니라 **센서→ESP UART 입력** 쪽이다.

---

## 2. 오늘 한 일과 하지 않은 일

### 한 일

| 항목 | 내용 |
|---|---|
| Mac 클론 | 이 Cursor 워크스페이스에 팀 Git을 Pi와 같은 SHA로 맞춤 |
| ESP 툴체인 | Homebrew `arduino-cli` 1.5.1 + `esp32:esp32` 3.3.11, FQBN `esp32:esp32:esp32` |
| `secrets.h` | 로컬만 생성. gitignore. `RPI_HOST=192.168.137.189`, SSID `ddd`, TCP `9000` |
| 라이브러리 | Sensirion SCD4x는 Library Manager. Seeed mmWave는 Library Manager에 없음 → 공식 GitHub 1.0.0 |
| 플래시 | 921600 실패 → **115200** 성공. 보드 `/dev/cu.usbserial-110` |
| 시리얼 | `dtr=off,rts=off` 필수. 기본 DTR/RTS는 ESP를 리셋함 |
| Pi 런타임 | `./run_safenest.sh` 기동 확인. `:8000` `:9000` `:5005` listen |
| LCD | 스크립트는 Chromium을 안 띄움. `/display` 200 확인 후 키오스크 수동 기동 |
| TCP 수신기 | `accept()`가 `process()` 안에 막혀 재접속이 5초 deadline에 막히던 구조 수정 |
| 필드 핫패치 | 같은 `receiver.py`를 라이브 Pi에 복사하고 런타임 재기동. **GitHub `main`에는 아직 없음** |

### 하지 않은 일 (의도)

- ESP 스케치 센서/리스크 로직 변경 없음 (`secrets.h`만 로컬)
- mmWave 모델, B23, M-N9, 학습 데이터 문서화 없음
- `nan`/`0`을 숫자로 보이게 하는 펌웨어/런타임 우회 없음
- 이 PR을 `main`에 merge하지는 않음 (리뷰 후)

---

## 3. 네트워크 / 호스트 (2026-08-28 필드)

Windows/Mac ICS 계열 핫스팟 `192.168.137.0/24`. AP 게이트웨이는 보통 `192.168.137.1`.

| 역할 | 주소 | 비고 |
|---|---|---|
| 핫스팟 AP | `192.168.137.1` | ESP TCP stall이 여기서 심해짐 (UDP 열화상 부하와 겹침) |
| Mac | `192.168.137.25` (`Mac.mshome.net`) | 개발·시리얼·필드 모니터 |
| Raspberry Pi | **`192.168.137.189`** | `sandi@…`, 경로 `/home/sandi/safenest-team-main` |
| ESP32 (DHCP) | **`192.168.137.238`** | MAC `cc:7b:5c:f2:1f:ec`, ESP32-D0WD-V3 |
| 예전 필드 IP | `192.168.0.3` | `PI_RUNBOOK.md`에 남아 있던 **폐기 주소**. 시리얼에 뜨면 **옛 플래시** |

Wi-Fi SSID는 **`ddd`** (2.4 GHz, WPA2/WPA3). 비밀번호는 `secrets.h`에만.

**IP 규칙 (오늘 가장 많이 헷갈린 것):**

- `secrets.h`의 `RPI_HOST`는 **Pi 목적지**다. ESP 자기 IP가 아니다.
- ESP는 DHCP로 `.238` 같은 주소를 받는다. `.189`가 시리얼에 보이면 “연결 대상”이지 ESP 주소가 아니다.
- 시리얼에 `connecting to 192.168.0.3`이 나오면 칩에 옛 펌웨어가 남은 것이다. 오늘 재플래시 후 목표는 `.189:9000`.

---

## 4. ESP32 로컬 툴체인 (Mac, Arduino IDE 없음)

워크스페이스:

```text
/Users/junwoo/Library/Mobile Documents/com~apple~CloudDocs/대학/2026/safenest-team-main
```

스케치: `ESP32/Arduino/esp32_sensor_node/esp32_sensor_node.ino`  
시크릿 템플릿: **`ESP32/secret.h.example`** (스케치 폴더의 `secrets.h.example`이 아님)

```bash
cp ESP32/secret.h.example ESP32/Arduino/esp32_sensor_node/secrets.h
# WIFI_SSID / WIFI_PASSWORD / RPI_HOST 만 로컬에서 수정
# git check-ignore 로 untracked 확인. 커밋 금지
```

### 검증된 버전 (이 Mac, 2026-08-28)

| 구성 요소 | 버전 | 설치 경로 |
|---|---|---|
| `arduino-cli` | 1.5.1 (Homebrew) | `brew install arduino-cli` |
| ESP32 core | `esp32:esp32` **3.3.11** | Boards Manager URL: Espressif `package_esp32_index.json` |
| 보드 | ESP32 Dev Module | FQBN `esp32:esp32:esp32` |
| Sensirion I2C SCD4x | 1.1.0 | Library Manager |
| Sensirion Core | 0.7.3 | SCD4x 의존성 |
| Seeed Arduino mmWave | 1.0.0 | **Library Manager에 없음.** GitHub `Seeed-Projects/Seeed-mmWave-library` |
| Adafruit NeoPixel | 1.15.5 | Seeed 전이 의존성 |
| hp_BH1750 | 1.0.2 | Seeed 전이 의존성 |

Seeed 필수 API (설치본에서 확인함): `SEEED_MR60BHA2`, `getHeartBreathPhases`, `handleType`, `ReportHumanDetection`.

**설치하면 안 되는 것:** Library Manager의 24 GHz radar / mmWaveKit 유사 패키지. 헤더/클래스 이름이 다르다.

Seeed CLI 설치 예:

```bash
arduino-cli lib install --git-url https://github.com/Seeed-Projects/Seeed-mmWave-library.git
# 또는 ZIP → Arduino libraries/Seeed_Arduino_mmWave
arduino-cli lib install "Adafruit NeoPixel"
arduino-cli lib install "hp_BH1750"
```

### 컴파일 / 업로드 / 모니터

USB 포트는 이 세션에서 **`/dev/cu.usbserial-110`**. 꽂을 때마다 `arduino-cli board list`로 확인.

```bash
cd "/Users/junwoo/Library/Mobile Documents/com~apple~CloudDocs/대학/2026/safenest-team-main"

arduino-cli compile --fqbn esp32:esp32:esp32 ESP32/Arduino/esp32_sensor_node

# 기본 921600 업로드는 이 보드에서 실패했음
arduino-cli upload --fqbn esp32:esp32:esp32:UploadSpeed=115200 \
  --port /dev/cu.usbserial-110 ESP32/Arduino/esp32_sensor_node

# DTR/RTS 켜면 ESP가 리셋되고 Wi-Fi/TCP가 불안정해짐
arduino-cli monitor --port /dev/cu.usbserial-110 \
  --config baudrate=115200,dtr=off,rts=off
```

시리얼 정상 흐름:

```text
[health] wifi=up ...
[network] connecting to 192.168.137.189:9000
[network] Raspberry Pi connected
```

`Raspberry Pi connected`가 **유지**돼야 Pi 필드 모니터가 LIVE다.  
`connecting`만 반복되면 ESP `client.connect(..., 1500)` 실패 루프다 (타임아웃 1.5초, 스케치 `telemetryTcpTask`).

펌웨어 계약 (변경 없음):

| 방향 | 프로토콜 | 포트 |
|---|---|---|
| ESP → Pi 스칼라 (mmWave/CO₂/PIR JSON) | TCP client | `RPI_PORT` = 9000 |
| ESP → Pi 열화상 청크 | UDP | `.ino` 상수 `THERMAL_UDP_PORT` = 5005 |

---

## 5. Raspberry Pi 운영 (오늘 확인한 것)

경로: `/home/sandi/safenest-team-main`  
사용자: `sandi`  
실행 커밋: 작업 시작 시 Mac과 동일 `1df0c17`. 그 위 `receiver.py`만 핫패치.

### 기동

`./run_safenest.sh`는 백엔드·TCP 9000·UDP 5005·TTS까지다. **Chromium LCD는 안 켠다.**

```bash
cd /home/sandi/safenest-team-main
ss -ltnp | grep -E ":8000|:9000" || true
ss -lunp | grep 5005 || true

# 이미 떠 있으면 중복 기동하지 말 것
bash ./run_safenest.sh
# 또는 백그라운드: setsid -f bash -c 'cd /home/sandi/safenest-team-main && exec bash ./run_safenest.sh >> logs/runtime.log 2>&1'
```

기대 포트:

| 포트 | 역할 |
|---|---|
| TCP `:8000` | FastAPI / LCD `/display` / `/health` / `/api/status` |
| TCP `:9000` | ESP 텔레메트리 |
| UDP `:5005` | 열화상 |

오늘 `/display`는 **`main`의 `backend/app.py`에 이미 있음** (200). 런북에 적힌 “로컬 패치가 아니면 404”는 **구버전 설명**이다.

### LCD 키오스크 (오늘 수동으로 올림)

Pi 그래픽 세션 (`DISPLAY=:0`, wayland `labwc` seat0):

```bash
export DISPLAY=:0
export WAYLAND_DISPLAY=wayland-0
export XDG_RUNTIME_DIR=/run/user/1000
pkill -f "chromium.*8000/display" 2>/dev/null || true
nohup chromium --kiosk --ozone-platform=x11 \
  --user-data-dir=/tmp/safenest-chromium-display \
  http://127.0.0.1:8000/display \
  >/tmp/chromium-display.log 2>&1 &
```

TTS가 들리면 런타임은 떠 있는 것이다. 화면이 없으면 Chromium만 없는 경우가 많다.

재기동 주의: SSH에서 `pkill` 후 포그라운드 `run_safenest.sh`를 켜면 SSH 세션이 죽으면서 런타임도 죽는다. **`setsid`로 분리**해서 켰다. `:8000`이 남아 있으면 먼저 프로세스를 정리한다.

### 필드 모니터

모니터가 깨진 게 아니다. TCP가 안 들어오면 `Δ=0` / `DISCONNECTED` / LCD `offline`·통신오류가 **정상 표시**다.

Mac:

```bash
cd ".../safenest-team-main/RaspberryPi/Runtime"
python3 hil/pi_field_monitor.py --base http://192.168.137.189:8000
python3 hil/pi_field_monitor.py --once --base http://192.168.137.189:8000
```

Pi:

```bash
cd /home/sandi/safenest-team-main/RaspberryPi/Runtime
python3 hil/pi_field_monitor.py
```

볼 칸: `TCP telem flowing`의 **Δ**, `UDP thermal flowing`의 **Δ**, 센서 `status`/`age`.  
`Δ=0`이면 그 간격에 새 패킷이 없다.

---

## 6. 이 PR의 코드 변경 (Pi TCP 수신기)

파일:

- `RaspberryPi/Runtime/gateway/receiver.py`
- `RaspberryPi/Runtime/tests/test_gateway_protocol.py` (`test_new_connection_preempts_stalled_client`)

### 이전 동작 (버그)

`SafeNestTCPServer.serve_forever()`가 `accept()` 후 **같은 스레드에서** `processor.process()`를 호출했다.

- `listen(2)` — ESP 재접속 폭주 시 backlog가 바로 참
- `process()`는 패킷 deadline **5초** 동안 소켓을 붙잡음
- ESP `connect()` 타임아웃은 **1.5초** → connecting 폭풍
- 반쯤 죽은 TCP(헤더 일부만 온 상태)가 다음 `accept`를 막음

관측된 Pi 에러:

```text
receive deadline exceeded: got 0 of 16 bytes     # 헤더조차 안 옴
receive deadline exceeded: got 0 of 938~950 bytes  # JSON 페이로드 도중 stall
```

소켓 예: `FIN-WAIT-1` (옛 연결 종료 중) + `SYN-RECV` (새 핸드셰이크 정체).

### 이후 동작 (이 PR)

- listen backlog **16**
- 새 inbound 연결이 오면 **즉시** 기존 소켓을 shutdown/close 하고 워커 스레드를 교체
- `accept` 루프는 `process()`에 막히지 않음
- 한 번에 ESP 스트림 **하나**만 처리하는 계약은 유지 (새 연결이 옛 연결을 대체)

루프백 테스트 `TCPServerLoopbackTests` + `test_new_connection_preempts_stalled_client` 통과 (Mac·핫패치 Pi).

### 핫패치 상태 (중요)

라이브 Pi 워킹 트리의 `receiver.py`는 **GitHub `main`보다 앞선 로컬 복사**다. 백업:

```text
/tmp/receiver.py.bak
/tmp/test_gateway_protocol.py.bak
```

이 PR이 merge된 뒤 Pi에서는 핫패치를 버리고 pull 한다.

```bash
cd /home/sandi/safenest-team-main
git fetch origin
git checkout main
git pull --ff-only origin main
# 런타임 재기동 후:
ss -ltn | grep 9000
# Recv-Q/Send-Q 옆 backlog 가 16 근처면 새 코드
```

핫패치가 남아 있는 채로 `git pull`하면 충돌날 수 있다. 그때는 이 PR 버전을 쓰고 `/tmp/*.bak`는 `main` 원본이다.

### 이 패치가 고치지 않는 것

preempt는 **재접속이 5초씩 막히던 것**만 푼다.  
관측상 TCP는 첫 버스트(텔레메트리 수십~수백, 열화상 수십 프레임) 후 또 `got 0 of ~940 bytes`로 죽는다.  
원인은 ESP 쪽 전송/핫스팟 ICS/UDP+TCP 혼잡 쪽으로 남아 있다. 펌웨어 `telemetryTcpTask` 송신 실패 시 `client.stop()` 후 1.5초 reconnect.

---

## 7. 오늘 관측된 두 개의 독립 장애

서로 다른 층이다. 하나를 고쳐도 다른 하나는 그대로다.

### A) TCP: 시작만 붙고 곧 끊김

증상:

- 시리얼 `[health] wifi=up` 유지되는 경우가 많음
- `[network] connecting to 192.168.137.189:9000` 반복, 가끔 짧은 `Raspberry Pi connected`
- Pi: 위 deadline 에러 후 패킷 카운트 정지
- 필드 모니터 Δ=0, 센서 `DISCONNECTED`/`STALE`, LCD `offline` / 통신오류
- `ss`에 `:9000` ESTAB 없음

오해하지 말 것:

| 보이는 것 | 실제 의미 |
|---|---|
| 시리얼 CO₂ ppm | ESP **로컬 I²C**. Pi 수신 증거가 아님 |
| 시리얼 `thermal_frames` 증가 | ESP **로컬 캡처**. UDP가 Pi에 도착했는지는 별개 |
| TTS / LCD emergency | 런타임 프로세스 생존. 라이브 ESP 세션이 아님 |
| 필드 모니터 Δ=0 | 모니터 버그 아님. TCP 유입 없음 |

열화상 UDP는 TCP와 별도다. TCP가 죽어도 UDP 프레임이 잠깐 들어올 수 있다. 반대로 열화상이 살아나 UDP datagram이 많아지면 (예: 1500+) ICS 핫스팟에서 TCP가 **더 잘** 죽는 패턴이 있었다.

오늘 숫자의 예 (세션마다 누적이 달랐음):

- 한 구간: telemetry ~318 후 `got 0 of 950 bytes`
- 다른 구간: telemetry 768, boot 2, 이후 `got 0 of 16 bytes`
- 재기동 후: telemetry 149 + thermal 83 후 `got 0 of 941 bytes`
- 열화상 정상 구간: completed frames ~159, datagrams ~1525

### B) mmWave: UART에 측정이 없음 (모델 문서 아님)

모델/B23/학습은 **담당 에이전트 문서**. 여기는 ESP·Pi가 본 페이로드만.

- 시리얼 `[health] resp=nan heart=nan` → ESP가 rate를 못 읽음
- 나중에 시리얼 `0` → 보드 안 float가 0.0. **Pi JSON으로 갔다는 뜻이 아님**
- TCP가 붙어 있던 동안 Pi mmWave jsonl: `breath_phase` / `human_detected_raw` / breath·heart rate **전부 null**
- Pi `MMWAVE_VALUES_INVALID`는 그 입력에 대한 **올바른** fail-close
- 에러를 숨기려고 0을 LIVE로 바꾸지 말 것

배선 (스케치 고정, 오늘 펌웨어 변경 없음):

| 신호 | ESP32 |
|---|---|
| MR60 TX → ESP RX | GPIO **16** |
| MR60 RX ← ESP TX | GPIO **17** |
| UART | 115200 |

CO₂·열화상은 I²C/SPI라 UART와 무관하다. 그래서 열화상/CO₂가 살아 있는데 mmWave만 `nan`이면 통신 스택이 아니라 **레이더 모듈·TX/RX 교차·전원**을 본다.

Seeed `begin()`은 `setRxBufferSize(32*1024)` 후 `begin(baud)`다. ESP32 Dev Module `pins_arduino.h`에 RX2/TX2가 없어도, 스케치가 `setPins(16,17)`을 begin 전에 호출하면 핀은 저장된다. `update(0)`는 루프마다 available 바이트를 비운다. 오늘 관측은 “파서가 값을 버린다”기보다 **0x0A13 / rate / presence 프레임이 안 들어온다**.

이 항목의 다음 문서는 mmWave 담당이 쓴다.

---

## 8. 시리얼 `0` vs Pi `DISCONNECTED`

같은 순간에 둘 다 보일 수 있다.

1. 시리얼 health는 ESP 로컬 float를 `%.1f`로 찍는다. `nan`이면 UART 샘플 없음, `0.0`이면 보드가 0을 읽음.
2. Pi LIVE는 **유지되는 TCP 세션**으로 JSON이 들어와야 한다.
3. TCP가 죽으면 Pi 센서 age가 수십~백 초로 늘고 `DISCONNECTED`가 된다. 디스크의 마지막 mmWave 레코드는 예전의 `null`로 남을 수 있다.
4. 필드 모니터 `0`은 종종 **Δ=0** (증가량)이다. 호흡수 0과 글자만 같다.

---

## 9. 다음에 할 일 (권장 순서)

1. **이 PR 리뷰·merge** → Pi `git pull --ff-only origin main` → 핫패치 제거 → 런타임 재기동. listen backlog 16 확인.
2. **TCP stall 근본 원인** (preempt 다음). 후보:
   - ICS 핫스팟(`192.168.137.1`) 대신 일반 2.4 GHz AP
   - 열화상 UDP 부하와 TCP 동시 전송
   - ESP `sendTelemetry` 실패/`client.stop()` / 1.5s connect
   - Pi `recv_exact` 5s deadline vs 반쯤 열린 소켓  
   센서 JSON 의미를 바꿔서 고치지 말 것.
3. **mmWave UART 하드웨어**는 모델 담당 + 배선. GPIO16/17 TX/RX 교차, 모듈 5V/GND, BHA2 vs FDA2.
4. ESP 펌웨어 로직 PR은 이 문서 범위가 아님. 툴체인은 이미 터미널만으로 가능.

금지:

- Pi `main`을 SSH로 또 고치고 Git에 안 남기기 (오늘은 긴급 핫패치였고 이 PR이 그 부채를 갚는다)
- `secrets.h` 커밋
- mmWave null을 0/LIVE로 위장

---

## 10. 관련 파일

| 항목 | 위치 |
|---|---|
| TCP 수신기 | `RaspberryPi/Runtime/gateway/receiver.py` |
| 프로토콜 | `RaspberryPi/Runtime/gateway/protocol.py` |
| 테스트 | `RaspberryPi/Runtime/tests/test_gateway_protocol.py` |
| 통신 계약 문서 | `RaspberryPi/Runtime/docs/PHASE3_COMMUNICATION.md` |
| 필드 모니터 | `RaspberryPi/Runtime/hil/pi_field_monitor.py` |
| Pi 런북 | `PI_RUNBOOK.md` |
| ESP 스케치 | `ESP32/Arduino/esp32_sensor_node/esp32_sensor_node.ino` |
| 시크릿 템플릿 | `ESP32/secret.h.example` |
| Arduino 환경 | `ESP32/docs/ARDUINO_ENVIRONMENT_SETUP_KO.md` |
| LCD `/display` | `RaspberryPi/Runtime/backend/app.py` |
| 기동 스크립트 | 저장소 루트 `run_safenest.sh` |

---

## 11. 재현 / 점검 명령

```bash
# Mac: 컴파일
arduino-cli compile --fqbn esp32:esp32:esp32 ESP32/Arduino/esp32_sensor_node

# Mac: Pi 포트
nc -z -G 2 192.168.137.189 9000 && echo 9000_OPEN
curl -fsS --max-time 5 http://192.168.137.189:8000/health

# Mac: 필드 모니터 1회
python3 RaspberryPi/Runtime/hil/pi_field_monitor.py --once --base http://192.168.137.189:8000

# Pi: 수신기 테스트 (Runtime venv)
cd /home/sandi/safenest-team-main/RaspberryPi/Runtime
python3 -m unittest tests.test_gateway_protocol.TCPServerLoopbackTests -v

# Pi: 현재 TCP 세션
ss -tnp | grep 9000 || true
```

---

## 12. 인수 체크리스트

- [ ] `RPI_HOST=192.168.137.189` (Pi) vs ESP DHCP `192.168.137.238` 구분
- [ ] 시리얼 `192.168.0.3` = 옛 플래시
- [ ] 업로드 115200, 모니터 `dtr=off,rts=off`
- [ ] Seeed는 Library Manager가 아니라 공식 GitHub 1.0.0
- [ ] `run_safenest.sh` ≠ LCD Chromium
- [ ] 필드 모니터 Δ=0 은 TCP 없음 (모니터 고장 아님)
- [ ] 시리얼 CO₂/thermal_frames ≠ Pi LIVE
- [ ] TCP preempt는 재접속 블로킹만 완화. mid-payload stall은 남음
- [ ] mmWave null/nan은 UART 입력. 모델 문서는 담당 에이전트
- [ ] Pi 핫패치를 이 PR merge 후 `git pull`로 교체
- [ ] `secrets.h` / 비밀번호는 Git에 없음
