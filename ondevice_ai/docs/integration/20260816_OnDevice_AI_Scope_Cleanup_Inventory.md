# SafeNest ondevice_ai 범위 정리 및 legacy 판정 인벤토리

**기준 저장소:** `jinsu1011/safenest-embedded-competition`
**기준 커밋:** `0fc2fd5be40f3a5714e738258183676f4adb1109`
**판정일:** 2026-08-16

## 실제 Pi 실행 경로 확인

현재 Raspberry Pi의 설치·기동 경로는 `integration/install_raspberry_pi.sh`와
`integration/start_all.sh`다. 이 경로는 `integration/pi_lcd/`와
`integration/web/`을 실행하며, `integration/README.md`는 현재 판정이
`web/server.js`의 규칙 기반 `evaluate()`/`riskScore()`이고 `ondevice_ai/`의
V4 위험도 엔진과 아직 연결되지 않았다고 명시한다.

따라서 현재 Pi runtime은 `ondevice_ai/risk/`나
`ondevice_ai/integrated_node/safenest_risk_engine.py`를 import하지 않는다.
이는 해당 AI 경로가 불필요하다는 뜻이 아니라, AI provider 통합은 아직 후속
작업이라는 뜻이다.

## 사전 이동 인벤토리

| 경로 | 현재 목적 | 실행·테스트 의존성 | 현재 Pi runtime | AI 소유 | 결정 |
|---|---|---|---:|---:|---|
| `models/`, `datasets/`, `scripts/` | 모델·계보·validator·재현 증거 | phase validator와 AI 테스트 | 아니오 | 예 | `KEEP_ACTIVE_AI` |
| `inference/`, `preprocessing/`, `sensors/` | 입력 계약·TFLite 추론·provider 어댑터 | `run_node.py`, 테스트 | 향후 AI 통합 대상 | 예 | `KEEP_ACTIVE_AI` |
| `risk/risk_engine.py`, `risk/fallback.py`, `risk/risk_rules.py` | AI provider 결과의 fail-closed·mock·B9 평가 경로 | `run_node.py`, B9 scripts, active tests | 아니오 | 예 | `KEEP_ACTIVE_DEPENDENCY` |
| `integrated_node/run_node.py`, `runtime_config.py` | provider 주입·mock/real fail-closed AI 통합 계약 | active tests와 팀 인수인계 | 향후 AI 통합 대상 | 예 | `KEEP_ACTIVE_AI` |
| `integrated_node/safenest_risk_engine.py` | 이전 simulator compatibility | legacy integration tests·학습 안내 문서 | 아니오 | 부분적 | `DEFER_OWNER_DECISION` |
| `integrated_node/safenest_integrated_plotter.py`, `virtual_sensor_streamer.py` | 이전 GUI/가상센서 simulator | 역사 도구·학습 안내 | 아니오 | 부분적 | `DEFER_OWNER_DECISION` |
| `integrated_node/competition_runtime/` | Pi LCD·웹 runtime의 중복 사본 | 코드 import 없음; 과거 문서 링크만 존재 | 아니오 | 아니오 | `ARCHIVE_HISTORICAL_REFERENCE` |

## 이번 archive 이동

`integrated_node/competition_runtime/` 전체를
`archive/legacy_prototypes/ondevice_ai_competition_runtime_20260816/`로 `git mv`했다.
이 그룹은 현재 `integration/`에 있는 Pi LCD receiver·웹 dashboard·설치 스크립트의
이전 중복 사본이다. archive README에는 원래 경로, 기준 커밋, 이동 사유와 현재
권위 경로를 기록했다.

이동 대상은 `HISTORICAL_REFERENCE`이며 `NOT_CURRENT_PI_RUNTIME`이다. 이는 새
production risk engine을 도입하거나 기존 위험도 수식·threshold·AI 모델을 바꾼
작업이 아니다.

## 남은 ownership 판단

`safenest_risk_engine.py`와 GUI simulator 묶음은 current Pi runtime은 아니지만,
active test와 학습 안내 문서가 직접 참조한다. 이 파일들을 archive하려면 역사
테스트와 교육용 참조를 함께 분리하고, active test suite의 책임 범위를 다시
승인해야 한다. 따라서 이번 PR에서는 삭제·이동하지 않고 legacy 상태만 명시한다.

## 정리 후 active ondevice_ai 책임

- **models:** runtime 기본 모델과 offline B 후보의 계보·무결성 정보
- **inference:** TFLite 입력·출력 계약 검증과 추론 adapter
- **preprocessing:** AI 입력 변환 계약
- **scripts/validators:** A/B 단계 재현·검증·제한 기록
- **tests:** active provider/fail-closed/model 계약 테스트
- **sensor AI adapters:** team device provider와 AI의 경계
- **integration contracts:** `run_node.py` provider injection과 실측 C 단계 인수인계

현재 Pi 수신·표시·웹 실행 코드는 `integration/`이 소유한다. 미래 production risk
engine의 설계·가중치·경보 정책은 이 archive 정리의 범위 밖이다.
