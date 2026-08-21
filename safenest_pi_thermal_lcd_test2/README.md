# SafeNest ESP32 + Raspberry Pi 열화상 LCD 테스트 묶음 2

이 폴더를 Raspberry Pi의 `~/safenest_pi_thermal_lcd_test2`로 통째로 복사해 사용합니다. GitHub 원격 `main`의 최신 RaspberryPi 코드에 OpenCV 열화상과 온디바이스 AI LCD 화면을 결합한 복사본입니다. `/admin`, `/guest/dashboard/A01`, `/dashboard`, `/display`는 모두 같은 FastAPI 서버(HTTP 8000)를 사용합니다.

## RaspberryPi 코드 기준

- 저장소: `https://github.com/jinsu1011/safenest-embedded-competition.git`
- 동기화 시 원격 `main`: `c3765ef14157991e1678e247d586d53e0aa57bcb`
- 반영된 원격 기능: `/admin`, `/guest/dashboard/A01`, `/api/thermal/A01`, UDP 5005 preflight, CO₂ C-B6·mmWave M-N9 canonical runtime, mmWave spectral 처리, Risk Formula V1
- 추가 유지 기능: `/display`, `/api/lcd/thermal`, `/api/lcd/thermal/image.jpg`, OpenCV `INFERNO` JPEG, Thermal AI 판정 패널
- 상세 동기화 내역: `SOURCE_SYNC.json`

## ESP32 코드 기준

ESP32 통합 코드는 `https://github.com/jinsu1011/safenest-embedded-competition.git`의 원격 `main`을 기준으로 동기화했습니다.

- ESP32 스케치가 마지막으로 변경된 기준 커밋: `41c3b15893590a1244d2bc827dee7835c9e26acf` (현재 `main`에도 동일 blob 유지)
- 스케치: `ESP32/Arduino/esp32_sensor_node/esp32_sensor_node.ino`
- Git blob SHA: `6773751eeae4cbea1012420542c8716f567b704f`
- 펌웨어/스키마: `1.3.0` / `1.3`
- `mmwave.human_detected_raw`를 `true`/`false`/`null` 3상태로 전송합니다.

상세 동기화 출처는 `SOURCE_SYNC.json`, 변경 내용은 스케치 폴더의 `ESP32_UPDATE_CHANGELOG_KO.md`를 확인하십시오.

## 통신 포트

| 데이터 | 프로토콜 | Pi 포트 |
|---|---|---|
| mmWave, CO2, PIR | TCP | `9000` |
| 80×62 열화상 프레임 | UDP | `5005` |
| LCD와 Dashboard | HTTP | `8000` |

ESP32와 Pi는 같은 LAN에 있어야 하며, Pi IP는 `hostname -I`로 확인합니다.

## 1. Raspberry Pi에서 Git clone

VS Code Remote SSH로 Raspberry Pi에 접속한 뒤 팀 저장소의 기능 브랜치를 clone하고 이 폴더로 이동합니다.

```bash
git clone --branch feature/thermal-lcd-ai-view \
  https://github.com/jinsu1011/safenest-embedded-competition.git
cd safenest-embedded-competition/safenest_pi_thermal_lcd_test2
```

## 2. Pi 환경 점검 및 설치

Raspberry Pi OS 64-bit, Python 3.10 이상을 권장합니다. 첫 설치에는 인터넷과 `sudo` 권한이 필요합니다.

```bash
bash scripts/00_check_pi.sh
bash scripts/01_install.sh
bash scripts/00_check_pi.sh --after-install
```

설치 스크립트는 `python3-venv`, `curl`, `iproute2`, Chromium과 폴더 내부 `.venv`의 FastAPI, Uvicorn, NumPy, OpenCV Headless, LiteRT 등을 설치합니다.

선택 설정은 다음과 같이 준비합니다.

```bash
cp .env.example .env
```

UFW를 켠 경우에만 포트를 허용합니다.

```bash
sudo ufw allow 8000/tcp
sudo ufw allow 9000/tcp
sudo ufw allow 5005/udp
```

## 3. ESP32 준비 및 업로드

필요한 Arduino 구성:

- Espressif `esp32` 보드 패키지
- Sensirion `Sensirion I2C SCD4x`
- Seeed Studio `Seeed Arduino mmWave`
- 내장 `WiFi`, `WiFiUDP`, `Wire`, `SPI`

`ESP32/Arduino/esp32_sensor_node/secrets.h.example`을 같은 폴더의 `secrets.h`로 복사해 Wi-Fi와 Pi IP를 입력합니다.

```cpp
constexpr char WIFI_SSID[] = "2.4GHz_WIFI_NAME";
constexpr char WIFI_PASSWORD[] = "WIFI_PASSWORD";
constexpr char RPI_HOST[] = "192.168.0.44";
constexpr uint16_t RPI_PORT = 9000;
```

Arduino IDE에서 `ESP32 Dev Module`을 선택해 업로드하고 Serial Monitor는 `115200 baud`로 엽니다. 열화상 UDP 목적지 포트는 스케치의 `5005`입니다. 실제 `secrets.h`는 Git에 커밋하지 마십시오.

## 4. 최종 실행

Pi Desktop이 LCD에 로그인된 상태에서 실행합니다.

```bash
bash run_safenest.sh
```

이 명령은 TCP/UDP 수신기, OpenCV 변환, LiteRT AI 추론, FastAPI 서버와 Chromium `/display` 키오스크를 함께 시작합니다. Desktop 세션이 없으면 다음처럼 서버만 시작합니다.

```bash
bash run_safenest.sh --no-kiosk
```

- LCD: `http://<PI_IP>:8000/display`
- 기존 Dashboard: `http://<PI_IP>:8000/dashboard`
- 관리자 웹: `http://<PI_IP>:8000/admin`
- A01 방문자 열화상: `http://<PI_IP>:8000/guest/dashboard/A01`
- 종료: 실행 터미널에서 `Ctrl+C`

## 5. 상태 확인

두 번째 SSH 터미널에서 실행합니다.

```bash
bash scripts/04_status.sh
bash scripts/05_smoke_test.sh
```

첫 완성 열화상 프레임을 받기 전 JPEG API `503`과 AI `INPUT_UNAVAILABLE`은 정상입니다. 왼쪽에는 OpenCV `INFERNO` 열화상, 오른쪽에는 `NOT_HUMAN`, `HUMAN_NORMAL`, `HUMAN_FALL`과 confidence가 표시됩니다.

현재 모델과 펌웨어는 실기 검증 전 후보/통합 시험용입니다. 의료 진단 또는 안전 인증 판단에 사용하면 안 됩니다.
