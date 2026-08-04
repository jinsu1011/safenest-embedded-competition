# `ondevice_ai/`

SafeNest V4 온디바이스 AI 구현 전체를 하나의 응집된 패키지로 보존하는 영역이다. 모델, 데이터셋, 설정, 추론, 위험도 엔진, 통합 노드, 테스트를 한자리에서 파악할 수 있다.

팀원별 파트 적용 안내는 👉 **[통합 팀원 인수인계 가이드 (`docs/TEAM_HANDOFF_GUIDE.md`)](docs/TEAM_HANDOFF_GUIDE.md)** 를 참고한다.

## 1. 디렉터리 목적
Raspberry Pi 5에서 동작하는 SafeNest V4 온디바이스 AI 파이프라인 전체 — 학습 산출물부터 실행 노드까지 — 를 한 패키지로 관리한다.

## 2. 시스템에서 담당하는 기능
`devices/`가 제공한 센서 판독값을 INT8 TFLite 모델로 추론하고, 가중치 융합 위험도 엔진으로 정상·주의·위험을 판정하며, 보수적 fallback과 통합 실행 노드를 제공한다.

## 3. 포함해야 하는 파일 유형
추론·위험도·통합 노드·학습·도구 Python 코드, TFLite 모델과 메타데이터, 전처리 NPZ와 매니페스트, YAML/JSON 설정, 벤치마크 결과, V4 테스트와 V4 문서를 포함한다.

## 4. 포함하면 안 되는 파일 유형
기기별 드라이버·펌웨어(`devices/`), 공용 센서 계약(`shared/contracts/`), 3D CAD(`hardware/`), 가상환경·캐시·생성 아카이브는 포함하지 않는다.

## 5. 주요 하위 구성
| 경로 | 역할 |
|---|---|
| `config/` | `models.yaml`, `sensors.yaml`, `risk_rules.yaml`, `risk_engine.json` |
| `datasets/` | 전처리 NPZ와 수집 매니페스트, `build_processed_npz.py` |
| `models/` | CO2·mmWave·Thermal INT8 TFLite 3종과 `model_manifest.json` |
| `src/sensors/` | V4 관점의 센서 registry·orchestration (기기 드라이버 사본은 두지 않는다) |
| `src/inference/` | TFLite interpreter 3종, `model_registry.py`, `inference_result.py` |
| `src/risk/` | `risk_engine.py`, `risk_rules.py`, `fallback.py` |
| `src/integrated_node/` | `run_node.py`(운영), `run_demo.py`, `run_mr60_usb_node.py`, 플로터·스트리머 |
| `src/training/` | `thermal_prep.py`, `thermal_train.py` |
| `src/tools/` | 아카이브 빌더, 학습 가이드 생성기, GUI 플로터, 검증 도구 |
| `benchmarks/` | Thermal 추론 지연 측정 스크립트와 결과 JSON |
| `tests/` | V4 단위·통합 테스트 9개 파일 |
| `docs/` | MR60 연동, 인수인계 가이드, walkthrough |

## 6. 입력과 출력 인터페이스
입력은 `devices/<device>/src/`의 어댑터 판독값, `models/`의 TFLite 산출물, `config/`의 임계값·가중치다. 출력은 `InferenceResult`, 위험도 평가 객체, 통합 노드의 JSON Lines 텔레메트리 스트림(stdout)이다.

## 7. 다른 기능 영역과의 관계
- `shared/contracts/base_sensor.py`의 계약에 기대어 동작한다.
- 기기 실구현이 필요하면 `devices.<device>.src...`를 명시적으로 import한다.
- `devices/mmwave/firmware/`가 내보낸 JSONL 텔레메트리를 리플레이 입력으로 사용할 수 있다.
- 반대로 `devices/`가 `ondevice_ai/`를 import하지 않는 것이 원칙이다.

## 8. 실행·학습·추론 또는 활용 방법
모든 명령은 **저장소 루트**에서 실행한다.

```bash
# 환경 (macOS 기준, Pi에서는 requirements-pi.txt)
python3 -m venv .venv
.venv/bin/python -m pip install -r ondevice_ai/requirements-mac.txt

# mock 센서 데모
.venv/bin/python -m ondevice_ai.src.integrated_node.run_demo

# 운영 통합 노드
.venv/bin/python -m ondevice_ai.src.integrated_node.run_node --mode mock

# MR60 USB 실기기 노드
.venv/bin/python -m ondevice_ai.src.integrated_node.run_mr60_usb_node --port /dev/ttyUSB0

# 학습·전처리
.venv/bin/python -m ondevice_ai.src.training.thermal_prep
.venv/bin/python -m ondevice_ai.src.training.thermal_train

# 테스트와 벤치마크
.venv/bin/python -m unittest discover -s ondevice_ai/tests -p 'test_*.py'
.venv/bin/python ondevice_ai/benchmarks/benchmark_thermal.py
```

모델·데이터셋·설정 경로는 항상 이 패키지 기준(`ondevice_ai/models/`, `ondevice_ai/datasets/`, `ondevice_ai/config/`)으로 해석한다.

## 9. 현재 개발 상태 및 버전
SafeNest V4 구조에 MR60 ESP 어댑터 보강분(`b0d3c95`)을 통합한 상태다. TFLite 3종은 모두 `v0.1.0`이며, `ondevice_ai/tests` 65개 테스트가 통과한다(skip 2).

**알려진 미해결:** `ondevice_ai/src/tools/verify_safenest_learning_examples.py`가 `non-numeric RPM unexpectedly produced a structured result` AssertionError로 실패한다. 재편 이전 커밋 `2509525`에서도 동일하게 실패하므로 구조 이동과 무관한 기존 결함이다.

## 10. 향후 파일 추가 및 관리 규칙
절대경로를 코드에 넣지 말고 `Path(__file__).resolve()` 기준으로 계산한다. 새 모듈에는 대응 테스트를 추가한다. 기기 드라이버를 `src/sensors/`로 복사하지 말고 `devices/`에서 import한다. 모델 교체 시 `models/model_manifest.json`, `config/models.yaml`, 관련 테스트를 같은 PR에서 갱신하고 SHA-256을 기록한다. 사용자명 디렉터리는 만들지 않는다.

## 11. 주요 기여자와 원본 브랜치·커밋 추적 정보
담당: Junwoo Han (`@sheepmeat`) — 온디바이스 AI 및 융합 / Jinsu Kim (`@jinsu1011`) — MR60 연동 및 통합.

| 구성 | 원본 ref | 원본 커밋 | 원본 경로 |
|---|---|---|---|
| V4 추론·위험도·통합·테스트 | `origin/Ondevice_AI` | `d97df3e` | `src/`, `models/`, `datasets/`, `config/`, `tests/` |
| MR60 AI 연동 보강 | `codex/mmwave-phase-integration` | `b0d3c95` | `SafeNest_V4_OnDevice_AI/` (원본 경로) |

이동 커밋 `38274c0`, 경로 수정 커밋 `3313f4b`·`32cdd1d`. 상세 근거는 [`docs/architecture/BRANCH_PROVENANCE.md`](../docs/architecture/BRANCH_PROVENANCE.md)에 있다.
