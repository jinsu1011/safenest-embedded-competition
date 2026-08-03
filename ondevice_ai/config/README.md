# `config/`

## 1. 디렉터리 목적
코드와 artifact에서 분리된 SafeNest 런타임 설정 계약을 관리한다.

## 2. 시스템에서 담당하는 기능
센서 버스, 모델 선택, MR60 전처리, 위험도 규칙과 임계값을 제공한다.

## 3. 포함해야 하는 파일 유형
검토 가능한 YAML/JSON 설정, 스키마 설명과 비밀값 없는 예시를 포함한다.

## 4. 포함하면 안 되는 파일 유형
API 키, 장치 인증서, 모델 바이너리, 데이터셋과 사용자별 절대경로는 포함하지 않는다.

## 5. 주요 하위 구성
`models.yaml`, `sensors.yaml`, `risk_rules.yaml`, `risk_engine.json`이 있다. `mmwave_processing.json`은 기기 담당 경계에 맞춰 `devices/mmwave/config/`로 옮겼다.

## 6. 입력과 출력 인터페이스
입력은 운영자가 검토한 설정 값이며 출력은 `ondevice_ai/src/`가 읽는 모델·센서·위험도 파라미터다.

## 7. 다른 기능 영역과의 관계
`ondevice_ai/models/`, `ondevice_ai/src/inference/`, `ondevice_ai/src/risk/`와 `devices/<device>/` 펌웨어 사이의 경로와 값 계약을 연결한다. mmWave 기기 전용 전처리 설정은 `devices/mmwave/config/mmwave_processing.json`으로 분리했다.

## 8. 실행·학습·추론 또는 활용 방법
저장소 루트를 현재 디렉터리로 두고 실행하면 기본 상대경로로 로드된다.

## 9. 현재 개발 상태 및 버전
V4 YAML 위험 규칙을 공식 설정으로 채택했으며 legacy JSON은 `archive/`에만 보존한다.

## 10. 향후 파일 추가 및 관리 규칙
설정 변경은 스키마·기본값·호환성 테스트와 함께 제출하고 JSON/YAML 이중 원본을 만들지 않는다.

## 11. 주요 기여자와 원본 브랜치·커밋 추적 정보
담당: Junwoo Han (`@sheepmeat`), Jinsu Kim (`@jinsu1011`).
V4 설정은 `origin/Ondevice_AI` (`d97df3e`)의 `config/`, MR60 처리 설정은 `codex/mmwave-phase-integration` (`b0d3c95`)에서 이관했다. 이동 커밋 `38274c0`.
