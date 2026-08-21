# SafeNest Thermal T-B5 Raspberry Pi 운영 기본 모델 준비성 검증

검증일: 2026-08-21 (Asia/Seoul)

대상 브랜치: `feature/thermal-b5-readiness`

기준 커밋: `8a8fcfbfa36087fa17b1fa06205f3a9c526a1539`

최종 분류: **BLOCKED**

## 1. 결론

`SMALL_CNN_BASELINE_V1_P1_full_int8.tflite`는 파일 신원, INT8 텐서 계약, 후보 전처리 경로, fail-closed 입력 검증, 출력 메타데이터, 위험 엔진의 Thermal 단독 DANGER 방지까지 로컬에서 확인했다. 그러나 운영 기본 모델 승격은 차단한다.

필수 게이트 중 독립 라벨 고정 테스트 정확도, 실제 Raspberry Pi 추론/지연/자원, 실센서 단위·방향 계약, 30분 soak, 8개 HIL 시나리오와 이미지, 운영 rollback 실증, 전체 저장소 회귀가 완료되지 않았다. 기존 O2.6 실측 프레임의 FLOAT↔INT8 top-1 일치율도 90.26%이고 low-side 포화가 커서 `INT8_QUANTIZATION_REVIEW_REQUIRED` 상태다.

로컬 통합 준비 코드만 평가하면 `PASS_WITH_LIMITATIONS`지만, 질문인 “Raspberry Pi 운영 기본 모델로 적용 가능한가”에 대한 답은 `BLOCKED`다. 운영 선택기와 현재 모델 manifest는 변경하지 않았다.

## 2. 실제 수행 작업

- `origin/main`을 `git pull --ff-only`로 확인했고 기준 커밋이 최신임을 확인한 뒤 기능 브랜치를 만들었다.
- 후보 TFLite의 SHA-256, 크기와 FlatBuffer 입력/출력 계약을 독립 파싱했다.
- Raw V1의 **정확히 10,080바이트인 완성 프레임만** SNTU v1로 변환하는 비운영 어댑터를 추가했다. 단위와 방향 근거가 없거나 stale/future/partial/sentinel 입력이면 거부한다.
- SNTU 디코더가 `0xFFFF` 픽셀 sentinel을 상태나 AI로 전달하지 않도록 했다.
- 후보 전용 P1 Celsius→global z-score→INT8 경로와 모델/전처리/단위/방향/포화 메타데이터를 추가했다. 운영 `LazyModel`이나 manifest에는 연결하지 않았다.
- Thermal AI 결과에 source timestamp, freshness, validity, sensor status, frame sequence, model/preprocessing identity를 노출했다.
- `HUMAN_FALL`을 LYING 파생 자세 proxy로 취급했다. Thermal 단독은 emergency override를 만들지 않으며, DANGER에는 비-Thermal 신호 보강이 필요하다. 검증된 mmWave apnea override는 유지했다.
- 저장된 Pi 프레임 NPZ를 실제 Pi에서 재생해 JSON/CSV 지연·포화·자원 결과를 남기는 후보 전용 도구를 추가했다.
- 같은 저장 프레임에서 OpenCV 열화상 PNG, 터미널 판정 PNG, raw NPZ, 증거 JSON을 동기 생성하는 8개 시나리오 캡처 도구를 추가했다. 실센서 증거 자체는 아직 없다.
- 모델 선택기 변경, Pi 접근, 패키지 설치, 서비스 재시작, 커밋, push는 수행하지 않았다.

## 3. 측정 및 검증 결과

| 항목 | 결과 | 판정 |
|---|---:|---|
| INT8 파일 크기 | 318,280 bytes | PASS |
| INT8 SHA-256 | `fa9730c29535477a3994c11e664474a0ca0116afaaa172889f47446ab2ac46be` | PASS |
| 입력 | `[1,62,80,1]`, INT8, scale `0.31791284680366516`, zero-point `-125` | PASS |
| 출력 | `[1,3]`, INT8, scale `0.00390625`, zero-point `-128` | PASS |
| 후보 집중 회귀 | 49 tests, 49 PASS | PASS |
| Python compileall | `ai gateway risk tests hil` | PASS |
| 운영 selector diff | empty | PASS — 의도적으로 미변경 |
| 기존 O2.6 실제 프레임 FLOAT↔INT8 | 139/154, 90.26%, mismatch 15 | BLOCKED |
| O2.6 low saturation | median 43.4%, p95 83.1% | BLOCKED |
| 독립 라벨 고정 테스트 정확도/F1/혼동행렬 | 미측정 | BLOCKED |
| 실제 Pi p50/p95/p99/FPS/RSS/온도 | 미측정 | BLOCKED |
| 실센서 30분 soak/8 시나리오 | 미실행 | BLOCKED |
| 전체 Runtime 회귀 | 258 중 23 failures, 17 errors, 1 skipped | BLOCKED |

O2.6의 154개 프레임은 정확도 데이터가 아니다. 라벨이 없으므로 top-1 동등성만 말할 수 있다. FLOAT 파일과 원본 캡처가 현재 워크스페이스에 없어 이번 세션에서 독립 재실행하지 않았다.

로컬 위험 정책 샘플:

| 입력 | 점수 | 레벨 | emergency |
|---|---:|---|---|
| Thermal `HUMAN_FALL` + 정상/낮은 비-Thermal 신호 | 20.25 | NORMAL | false |
| Thermal `HUMAN_FALL` + mmWave 0.75 + CO2 1500 ppm + no-motion | 66.25 | DANGER | false |

두 번째 결과는 가중 위험 DANGER이며 emergency override가 아니다.

현재 상태와 목표 상태의 차이:

| 계약 | 현재 | 운영 목표 | 차이 |
|---|---|---|---|
| 모델 선택 | legacy `thermal_fall_int8_v0.1.0` | B5 FULL_INT8 + P1 | selector 미승인/미변경 |
| 전처리 | legacy per-frame min/max | Celsius + P1 global z-score + locked INT8 | 후보 경로만 구현 |
| 전송 | SNTU v1 운영, Raw V1 별도 | 검증 단위/방향 + CRC/sequence 기반 단일 계약 | Raw V1 blind chunk는 통합 불가 |
| 정확도 | 독립 locked label 없음 | 책임자가 승인한 locked overall/클래스별 기준 | 기준 승인·측정 불가 |
| 양자화 | 90.26% 동등성, saturation review | 승인된 동등성/포화 기준 통과 | 차단 |
| Pi 성능 | 미측정 | p50/p95/p99/FPS/drop/CPU/RAM/temp 예산 통과 | 장비 필요 |
| 위험 정책 | 로컬 정합 | 실센서 정상/경고/위험/stale/invalid HIL | HIL 필요 |
| 복구 | 문서만 작성 | 재시작/rollback drill PASS | 운영 승인 필요 |

## 4. 남은 위험과 차단 게이트

1. 독립 피험자/환경의 pristine locked test가 없다. 정확도 90% 이상, 클래스별 recall/F1, 혼동행렬, 조건별 반복 측정을 판정할 수 없다.
2. 기존 현장 154프레임에서 INT8 저측 포화가 크고 FLOAT↔INT8 일치율이 90.26%다. 대표 데이터 재양자화 또는 INT8 배포 보류 검토가 필요하다.
3. Raw V1의 물리 단위와 `62×80` 방향이 학습 canonical 방향과 같다는 센서/펌웨어 근거가 없다. 기존 1,320/1,460바이트 blind chunk에는 frame id/index/offset/CRC가 없어 손실·중복·재정렬 무결성을 증명할 수 없다.
4. 이 PC에는 `ai_edge_litert`, `tflite_runtime`, `tensorflow`가 없어 실제 interpreter invoke를 수행하지 않았다. 패키지는 설치하지 않았다.
5. Raspberry Pi와 실센서에 접근하지 않아 지연, FPS, RSS, CPU/SoC 온도, 장기 안정성, 재부팅/재연결을 확인하지 않았다.
6. 전체 Runtime 회귀는 이번 변경 범위 밖의 UI/Backend/Stage 7·9 계약 실패와 로컬 추론 런타임 부재 등을 포함해 green이 아니다. 이번 변경 직접 범위 49개는 green이다.
7. 현재 `.docx` 통합 보고서는 운영 승격 단계가 아니므로 수정하지 않았다. LibreOffice도 없어 최신 문서의 시각 렌더 검증을 수행할 수 없었다.

## 5. 변경 파일

핵심 구현:

- `RaspberryPi/Runtime/gateway/thermal_raw_v1_adapter.py`
- `RaspberryPi/Runtime/gateway/protocol.py`
- `RaspberryPi/Runtime/ai/thermal_b5_candidate.py`
- `RaspberryPi/Runtime/ai/pipeline.py`
- `RaspberryPi/Runtime/risk/engine.py`
- `RaspberryPi/Ondevice_AI/risk/risk_config.json`
- `RaspberryPi/Runtime/hil/thermal_b5_pi_benchmark.py`
- `RaspberryPi/Runtime/hil/thermal_b5_scenario_capture.py`

테스트:

- `RaspberryPi/Runtime/tests/test_thermal_b5_readiness.py`
- `RaspberryPi/Runtime/tests/test_thermal_udp.py`
- `RaspberryPi/Runtime/tests/test_ai_pipeline.py`
- `RaspberryPi/Runtime/tests/test_risk_engine.py`
- `RaspberryPi/Runtime/tests/test_gateway_risk_pipeline.py`

증거/운영 산출물은 이 디렉터리에 있다. 원본 모델 바이너리, `models.yaml`, `model_manifest.json`은 변경하지 않았다.
각 자료 저장소의 branch/HEAD/dirty 기준선은 `workspace_baseline.json`에 보존했다.

## 6. 재현 명령

저장소 루트에서:

```bash
cd RaspberryPi/Runtime
python3 -m unittest tests.test_thermal_b5_readiness tests.test_thermal_udp tests.test_ai_pipeline tests.test_risk_engine tests.test_gateway_risk_pipeline -q
python3 -m compileall -q ai gateway risk tests hil
python3 hil/thermal_b5_pi_benchmark.py --help
cd ../..
git diff --check
git diff -- RaspberryPi/Ondevice_AI/config/models.yaml RaspberryPi/Ondevice_AI/models/model_manifest.json
```

승인된 Pi와 승인된 저장 프레임이 준비된 뒤:

```bash
cd /home/pi/safenest/team-safenest-embedded/RaspberryPi/Runtime
../../.venv/bin/python hil/thermal_b5_pi_benchmark.py \
  --input-npz /var/lib/safenest/validation/thermal_b5/saved_runtime_frames.npz \
  --output-json /var/lib/safenest/validation/thermal_b5/results/pi_benchmark.json \
  --output-csv /var/lib/safenest/validation/thermal_b5/results/pi_benchmark.csv \
  --warmup 20 --repeat 10 \
  --orientation-contract NATIVE_ROWS_62_COLS_80_MATCHES_TRAINING_CANONICAL \
  --physical-unit-contract MI48_UINT16_0P1_KELVIN
```

FLOAT 원본과 실제 snapshot을 승인된 위치에 놓은 뒤 동등성 재검증:

```bash
cd /home/pi/safenest/team-safenest-embedded/RaspberryPi/Runtime
../../.venv/bin/python -m hil.thermal_o2_6_field_equivalence \
  --snapshot /var/lib/safenest/validation/thermal_b5/mi48_real_snapshot \
  --float-artifact /var/lib/safenest/artifacts/thermal/SMALL_CNN_BASELINE_V1_P1_float32.tflite \
  --output /var/lib/safenest/validation/thermal_b5/results/float_int8_equivalence.json
```

## 7. 운영 판단

현재 판단은 **BLOCKED — 운영 기본 모델 전환 금지**다. 기존 `thermal_fall_int8_v0.1.0` 선택을 유지한다. 후보 코드는 진단/HIL 경로에만 있으며 production selected 값은 false다.

승격을 재검토하려면 `readiness_checklist.json`의 모든 필수 게이트가 PASS여야 한다. 정확도/성능의 정식 프로젝트 기준은 아직 없으므로 `proposed_acceptance_criteria.json`에 보수적 임시안을 제시했으며 책임자 승인이 필요하다. 독립 라벨 평가, 실제 Pi 지연/자원 예산, 30분 soak, 8 시나리오, rollback 실증, 전체 필수 회귀 green이 필요하다.

## 8. 필요한 승인

- Raspberry Pi와 실센서에 대한 **읽기 중심 조사/HIL 실행 승인** 및 접속 정보
- 승인된 FLOAT reference와 라벨 고정 테스트/실제 캡처의 제공 위치 및 사용 승인
- 필요한 경우 Pi의 기존 venv에서만 의존성을 설치할 승인; 이번 세션에서는 설치하지 않음
- 8개 시나리오 수행·이미지 저장 승인 및 안전 담당자의 판정 기준 확인
- `proposed_acceptance_criteria.json`의 정확도·양자화·Pi 성능 임시 기준을 채택하거나 수정할 책임자 승인
- 모든 게이트 통과 후 별도 production selector 변경/서비스 재시작/rollback drill 승인
- 리뷰 후 기능 브랜치 commit/push/PR 승인
