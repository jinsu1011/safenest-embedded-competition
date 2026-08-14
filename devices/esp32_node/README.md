# `devices/esp32_node/`

## 1. 디렉터리 목적
네 개 센서를 한 보드에서 수집해 Raspberry Pi로 전송하는 ESP32 수집 노드의 펌웨어와 보드 설정을 한곳에서 관리한다.

## 2. 시스템에서 담당하는 기능
MR60BHA2(UART), SCD4x(I2C), PIR(디지털 입력), MI48 계열 열화상(I2C 제어 + SPI 데이터)을 스케줄에 따라 읽고, 1초 주기 `safenest.telemetry.v1` JSON 패킷으로 Wi-Fi TCP 9000에 전송한다. 위험도 판정은 하지 않는다.

## 3. 포함해야 하는 파일 유형
ESP32 스케치와 헤더, 보드 핀·주기·전송 설정, 자격증명 예제(`secrets.example.h`), 보드 단독으로 확인 가능한 절차를 포함한다.

## 4. 포함하면 안 되는 파일 유형
실제 Wi-Fi 자격증명(`secrets.h`), Pi 쪽 수신·표시·웹 코드(`integration/`), 위험도 융합과 추론(`ondevice_ai/`), 개별 센서의 Python 어댑터(`devices/<sensor>/src/`)는 포함하지 않는다.

## 5. 주요 하위 구성
`firmware/esp32_sensor_node.ino`(수집·패킷화 전체)와 `firmware/secrets.example.h`(Wi-Fi SSID·비밀번호·`RPI_HOST` 템플릿)로 구성된다.

## 6. 입력과 출력 인터페이스
입력은 UART/I2C/SPI/GPIO 원신호다. 출력은 `schema`, `device_id`, `uptime_ms`와 센서별 값·유효성 플래그를 담은 JSON 텔레메트리이며, 값을 읽지 못하면 0으로 바꾸지 않고 유효성 플래그를 내린다. 열화상은 프레임 대신 `thermal_max_c` 스칼라만 실어 보낸다.

## 7. 다른 기능 영역과의 관계
이 노드의 텔레메트리를 `integration/pi_lcd/server.py`가 받아 저장하고, `integration/web/server.js`가 상태를 판정한다. 이 디렉터리는 Pi 쪽 코드를 import하지 않는다. `devices/mmwave/firmware/`는 MR60 단독 계측·검증용 PlatformIO 프로젝트로 목적이 다르며, 이 스케치는 4센서 통합 수집용이다.

## 8. 실행·학습·추론 또는 활용 방법
Arduino IDE에서 `firmware/esp32_sensor_node.ino`를 열고, `firmware/secrets.example.h`를 같은 폴더의 `secrets.h`로 복사해 Wi-Fi와 `RPI_HOST`를 채운 뒤 ESP32 Dev Module로 업로드한다. 보드·라이브러리 설치 절차는 [`docs/esp32_node/ESP32_ARDUINO_SETUP.md`](../../docs/esp32_node/ESP32_ARDUINO_SETUP.md)에 있다.

## 9. 현재 개발 상태 및 버전
실제 하드웨어(ESP32 + Raspberry Pi 5 + LCD)에서 4센서 수집과 LCD 자동 전환까지 검증했다. 열화상 배열은 픽셀 약 30%만 살아 있어 최고 온도만 사용하며, 프레임 스트리밍은 `THERMAL_STREAM_FRAMES = false`로 꺼져 있다. 한계는 [`docs/esp32_node/ESP32_LCD_INTEGRATION_NOTES.md`](../../docs/esp32_node/ESP32_LCD_INTEGRATION_NOTES.md) 5절에 기록했다.

## 10. 향후 파일 추가 및 관리 규칙
핀 배치나 전송 주기를 바꾸면 [`docs/esp32_node/COMMUNICATION_PROTOCOL.md`](../../docs/esp32_node/COMMUNICATION_PROTOCOL.md)와 Pi 쪽 파서를 같은 PR에서 함께 고친다. 한 번에 필터 또는 임계값 하나만 바꾸고 변경 전후를 같은 조건에서 비교한다. `secrets.h`는 절대 커밋하지 않는다.

## 11. 주요 기여자와 원본 브랜치·커밋 추적 정보
담당: Seungha (`@yuseungha`) — ESP32 수집 노드 펌웨어, 센서 배선, 텔레메트리.
원본 ref `yuseungha/safenest-embedded-competition@0992a6d`(`main`에 PR #1로 병합), 원본 경로 `yuseungha/esp32_sensor_node/`.
