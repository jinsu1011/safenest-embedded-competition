# `ondevice_ai/tests/`

## 1. 디렉터리 목적
SafeNest Python 모듈과 모델·설정·센서 계약의 회귀 검증을 한곳에서 수행한다.

## 2. 시스템에서 담당하는 기능
정상·오류·fallback·fault injection·3모델 통합·MR60 provenance 동작을 검증한다.

## 3. 포함해야 하는 파일 유형
`test_*.py`, 작은 fixture, benchmark 스크립트와 기준 결과를 포함한다.

## 4. 포함하면 안 되는 파일 유형
제품 코드의 유일한 구현, 거대 원본 데이터, 캐시와 실제 비밀값은 포함하지 않는다.

## 5. 주요 하위 구성
V4 unittest 모듈 9개로 구성한다. 성능 기준 자료는 `ondevice_ai/benchmarks/`로, mmWave 기기 단독 테스트는 `devices/mmwave/tests/`로 분리했다.

## 6. 입력과 출력 인터페이스
입력은 `ondevice_ai/src|models|config|datasets/`와 `devices/<device>/src/`, `shared/contracts/`이며 출력은 unittest 성공·실패와 명시적 오류 메시지다.

## 7. 다른 기능 영역과의 관계
구조나 경로를 바꾸는 모든 기능 변경은 이 디렉터리의 회귀 테스트로 검증한다.

## 8. 실행·학습·추론 또는 활용 방법
저장소 루트에서 `python3 -m unittest discover -s ondevice_ai/tests -p "test_*.py"`를 실행한다. 기기 단독 테스트는 `-s devices/mmwave/tests`로 별도 실행한다.

## 9. 현재 개발 상태 및 버전
현재 이 수트는 65개 테스트(skip 2)가 통과하고, `devices/mmwave/tests` 19개를 합쳐 총 84개다.

## 10. 향후 파일 추가 및 관리 규칙
외부 하드웨어 없이 결정적으로 실행되게 작성하고 실행하지 않은 테스트를 성공으로 기록하지 않는다.

## 11. 주요 기여자와 원본 브랜치·커밋 추적 정보
담당: Junwoo Han (`@sheepmeat`), Jinsu Kim (`@jinsu1011`).
기본 수트는 `origin/Ondevice_AI` (`d97df3e`)의 원본 경로 `tests/`, MR60 관련 수트는 `codex/mmwave-phase-integration` (`b0d3c95`)에서 이관했다. 이동 커밋 `38274c0`.
