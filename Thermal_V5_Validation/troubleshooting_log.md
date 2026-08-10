# 트러블슈팅 기록 (Troubleshooting Log)

본 문서는 Thermal-44 V5 Real Validation 검증 과정에서 발생한 각종 에러 사항과 원인, 해결 방법을 기록합니다.

## 1. 아두이노 IDE 업로드 시 외부 라이브러리 누락 에러
- **증상:** `Seeed_Arduino_mmWave.h: No such file or directory` 등 컴파일 에러 발생
- **원인:** 통합 센서 노드 펌웨어(`esp32_sensor_node.ino`)를 최초 빌드할 때, PC 환경에 mmWave 및 SCD4x 관련 외부 라이브러리가 미설치되어 있었음.
- **해결:** 
  1. Arduino IDE 라이브러리 매니저를 통해 설치를 안내했으나 검색/설치 과정에서 문제 발생.
  2. GitHub 공식 저장소(`Love4yzp/Seeed-mmWave-library`)에서 `git clone` 명령어를 사용하여 Windows 로컬 `Arduino/libraries` 폴더에 강제로 수동 설치하여 해결 완료.

## 2. ESP32 포트 인식 불가 현상
- **증상:** 아두이노 IDE에서 `Failed uploading: no upload port provided` 발생 및 포트 탭 비활성화.
- **원인:** Type-C 단자를 가진 저가형 ESP32 호환 보드의 회로 설계 특성상, C to C 케이블을 사용하면 PC에서 장치 자체를 전력/데이터 통신 기기로 인식하지 못함.
- **해결:** 데이터 통신이 지원되는 'USB-A to USB-C' 케이블(또는 허브 경유)로 교체하여 물리적인 하드웨어 인식 문제 해결.

## 3. 라즈베리파이 TFLite 패키지 설치 에러
- **증상:** `pip install tflite-runtime` 실행 시 `No matching distribution found` 에러 발생.
- **원인:** 라즈베리파이 5의 최신 OS(Bookworm, Python 3.11 이상) aarch64 환경에서는 구형 `tflite-runtime` wheel 파일이 더 이상 pip 저장소에서 공식 제공되지 않음.
- **해결:** TFLite의 최신 공식 후속 라이브러리 패키지인 `ai-edge-litert`로 대체하여 성공적으로 설치 완료(`pip install ai-edge-litert`). 설치 후 모듈 임포트가 정상적으로 작동함을 테스트함.
