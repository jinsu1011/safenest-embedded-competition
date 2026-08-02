# `src/`

## 1. 디렉터리 목적
라즈베리 파이에서 실행되는 센서 수집, 추론, 위험도 융합 및 통합 노드 코드를 기능별 Python 패키지로 제공한다.

## 2. 시스템에서 담당하는 기능
센서 데이터를 표준화하고 TFLite 추론 결과를 V4 위험도 엔진에 전달해 최종 상태를 생성한다.

## 3. 포함해야 하는 파일 유형
검토 가능한 `.py`, 소스에 필요한 작은 정적 규칙, 패키지 `__init__.py`만 포함한다.

## 4. 포함하면 안 되는 파일 유형
모델 바이너리, 원본 측정 로그, 비밀값, 가상환경, 캐시와 생성 결과는 포함하지 않는다.

## 5. 주요 하위 구성
`sensors/`, `inference/`, `risk/`, `integrated_node/`, `training/`, `tools/`로 구성한다.

## 6. 입력과 출력 인터페이스
입력은 센서 프레임·JSON 패킷·모델 매니페스트이며, 출력은 `InferenceResult`와 위험도 평가 객체 또는 JSON 텔레메트리다.

## 7. 다른 기능 영역과의 관계
`config/`, `models/`, `datasets/`를 읽고 `firmware/`의 직렬 텔레메트리를 수신하며 `tests/`에서 검증된다.

## 8. 실행·학습·추론 또는 활용 방법
저장소 루트에서 `python3 -m src.integrated_node.run_demo`를 실행하고, 학습 유틸리티는 `python3 -m src.training.<module>`로 호출한다.

## 9. 현재 개발 상태 및 버전
SafeNest V4 통합 구조이며 MR60 ESP 어댑터 보강분(`b0d3c95`)을 포함한다.

## 10. 향후 파일 추가 및 관리 규칙
절대경로를 코드에 넣지 말고 저장소 루트 기준 경로를 사용하며 새 모듈에는 대응 테스트를 추가한다.

## 11. 주요 기여자와 원본 브랜치 추적 정보
Junwoo Han(`sheepmeat`, `origin/Ondevice_AI`, `d97df3e`)의 V4 구현과 Jinsu Kim(`jinsu1011`, `codex/mmwave-phase-integration`, `b0d3c95`)의 MR60 통합을 계승한다.
