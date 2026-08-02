# `firmware/`

## 1. 디렉터리 목적
SafeNest MCU 센서 노드의 빌드 가능한 펌웨어 프로젝트를 보관한다.

## 2. 시스템에서 담당하는 기능
ESP32-C6와 MR60 mmWave 센서의 수집, 필터링, 상태 판정 및 직렬 텔레메트리 송신을 담당한다.

## 3. 포함해야 하는 파일 유형
PlatformIO 설정, C/C++ 소스·헤더, 센서 설정, 재현 가능한 캡처·분석 도구와 검증 로그를 포함한다.

## 4. 포함하면 안 되는 파일 유형
`.pio/`, 장치별 비밀값, 임시 빌드 산출물과 출처가 불명확한 바이너리는 포함하지 않는다.

## 5. 주요 하위 구성
`esp_wroom32_mr60_monitor/` 아래 `src/`, `include/`, `config/`, `analysis/`, `analysis_tools/`, `logs/`, `csv/`가 있다.

## 6. 입력과 출력 인터페이스
입력은 MR60 UART 프레임이며 출력은 USB/UART JSONL 텔레메트리와 재현 가능한 분석 요약이다.

## 7. 다른 기능 영역과의 관계
`src/sensors/mmwave/`가 텔레메트리를 소비하고 `docs/operations/`가 설치·운용 절차를 설명한다.

## 8. 실행·학습·추론 또는 활용 방법
`cd firmware/esp_wroom32_mr60_monitor && pio run`으로 빌드하며 장치 업로드 전 해당 런북을 확인한다.

## 9. 현재 개발 상태 및 버전
MR60 schema 1.2와 최종 v1.2.0 측정·검증 작업(`b0d3c95`)을 포함한다.

## 10. 향후 파일 추가 및 관리 규칙
장치 설정 변경은 헤더·JSON·문서·검증 로그를 함께 갱신하고 원본 JSONL은 절대 덮어쓰지 않는다.

## 11. 주요 기여자와 원본 브랜치 추적 정보
Jinsu Kim(`jinsu1011`)의 `origin/main` 계보와 `codex/mmwave-phase-integration`(`b0d3c95`) 작업을 통합했다.
