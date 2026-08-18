# MR60 SENSOR-OWNER ACQUISITION ROADMAP (MR60-CAP)

작성일: 2026-08-18 (CAP-2/CAP-3 실측 반영)
상태: CAP-0/1/2/3 완료 · CAP-5 부분 · CAP-6 차단
범위: 센서 담당자(물리 데이터 획득) 트랙 전용.
이 문서는 canonical 모델 로드맵이 아니다. Phase A/B/M-C/M-D/M-N ID 를 재사용하지 않는다.

---

## 0. 이 로드맵이 종속되는 상위 계약

모델 트랙은 이미 입력 계약을 **동결**했다.

- `RaspberryPi/Ondevice_AI/config/mmwave/m_n4_canonical_input_dataset_contract.json`
- `contract_id: MMWAVE_MR60_COMPAT_INPUT_DATASET_V1`, `status: FROZEN_FOR_M_N5`
- 실행 구현: `RaspberryPi/Ondevice_AI/scripts/mmwave_m_n4_canonical.py`

센서 트랙에 직접 걸리는 조항:

| 항목 | M-N4 계약 값 | 센서 트랙 의미 |
|---|---|---|
| `source_mr60.required_live_fields` | `breath_phase`, `ts_monotonic_ms`, `phase_age_ms` | 이 3개만 있으면 캡처는 계약 충족 |
| `timing.phase_update_estimate_ms` | `ts_monotonic_ms - phase_age_ms` | 파생 provenance 를 계약이 **공식 채택**함 |
| `timing.update_advancement_tolerance_ms` | 8.0 (마지막 **채택** 이벤트 기준) | 8 ms 이내 재게시는 폐기 |
| `gap` | 채택 간격이 `max(0.40 s, 4 × median)` 초과 시 창 전체 폐기 | 캡처 중 0.4 s 이상 끊김 금지 |
| `resampling` | 30 s 창, 8 Hz, 240 샘플, `[1,240,1]` | 세션 길이는 30 s 배수로 계획 |
| `team_mr60.supervised_training` | `DISALLOWED` (`physical_subjects: 1`) | 지금 우리 데이터는 학습 금지 상태 |
| `target.independent_reference_source` | `MOVESENSE_CHEST_ACC` | 프로젝트의 독립 reference 표준이 이미 정해져 있음 |

즉 **§37 Case B 의 `phase_update_seq` 부재는 모델 계약상 결함이 아니다.** 계약이 파생식을
정식 경로로 지정했다. 세션 분류는 `TEMPORAL_PROVENANCE_LIMITED` 대신
`TEMPORAL_PROVENANCE_DERIVED_CONTRACT_CONFORMING` 으로 둔다.

---

## 1. CAP-0 결과 — 캡처 스택 실측 (센서 없이 완료)

기존 PR18 파일럿 raw JSONL 2건을 **동결된 M-N4 로직에 그대로 통과**시켜 측정했다.
도구: `tools/cap0_m_n4_feasibility.py` (신규, read-only).

```bash
python3 tools/cap0_m_n4_feasibility.py pilot/M-C0-PILOT-STATIONARY-001.raw.jsonl
```

### 1.1 Capture readiness matrix

| 필드 | 상태 | 근거 |
|---|---|---|
| `breath_phase` | AVAILABLE (1799/1799, 전부 유한) | 파일럿 실측 |
| `ts_monotonic_ms` | AVAILABLE, 비감소 | 실측 |
| `seq` | AVAILABLE, 엄격 증가, gap 0 | 실측 |
| `phase_age_ms` | AVAILABLE (median 12 ms, p95 15 ms) | 실측 |
| `phase_update_ms` | **DERIVABLE**, M-N4 가 정식 채택 | 계약 |
| `phase_update_seq` | NOT_AVAILABLE | 계약상 불필요 (아래 1.3) |
| `presence` / `distance_cm_raw` | AVAILABLE | 실측 |
| `breath_rate_raw` | AVAILABLE (진단 전용, `breath_rate_raw_trusted: false`) | 실측 |
| `sensor_state` / `error_code` | AVAILABLE | 실측 |
| `firmware_version` / `config_hash` | AVAILABLE, 세션 내 단일값 | 실측 |

`firmware_version = safenest-mr60-esp/1.2.0`,
`config_hash = b817e8bf…c987834` — 사전 검증값과 일치.
원복 바이너리 `firmware_mr60_v1.2.0.bin` SHA-256 `3a80040e…7707cb` 도 실물 대조 일치.

### 1.2 M-N4 창 수율 — 실측

| 세션 | 길이 | 채택 이벤트 | 8 ms 규칙 폐기 | 0.4 s 초과 간격 | 30 s 창 채택 | 창 폐기 |
|---|---:|---:|---:|---:|---:|---:|
| STATIONARY-001 | 179.9 s | 1799 (9.999 Hz) | 0 | 0 | **5 / 5** | 0 |
| DESKWORK-001 | 179.9 s | 1798 (9.994 Hz) | 1 | 0 | **5 / 5** | 0 |

→ **3 분 세션 = 정확히 M-N4 창 5개.** 캡처 계획의 환산식:
`필요 창 수 N → 세션 길이 ≥ 60 s(warmup) + N × 30 s`.

### 1.3 phase_update_seq 부재의 실제 비용 ≈ 0

`rows_per_distinct_update_estimate = 1.000 / 1.001`.
파생 `phase_update_ms` 가 텔레메트리 행과 거의 1:1 이고, 8 ms 규칙이 폐기한 행은
3598 행 중 **1 행**뿐이다. `phase_age_ms` max 는 정지 세션에서 17 ms 로,
`kPhaseMaxAgeMs = 500` 에 한 번도 근접하지 않았다.
따라서 provenance 전용 펌웨어 패치의 실익은 현재 측정 근거상 미미하다 → **제안 보류**
(§11 절차는 유지하되, 실측이 필요성을 지지하지 않으므로 지금 올리지 않는다).

### 1.4 발견된 실제 문제 2건

**(a) LOW_AMPLITUDE 가 M-N4 를 그냥 통과한다 — 최우선 이슈**

| 세션 | `sensor_state != VALID` | error_code |
|---|---:|---|
| STATIONARY-001 | 87 % (1568/1799) | `BREATH_PHASE_LOW_AMPLITUDE` |
| DESKWORK-001 | 53 % (961/1799) | `BREATH_PHASE_LOW_AMPLITUDE` |

원인: `ESP32/reference/mmwave_platformio/include/mmwave_config.h`
`kBreathMinPhaseStd = 0.2F`, 30 s 창 표준편차가 그 아래면 DEGRADED
(`src/main.cpp:290`). 파일럿의 `breath_phase_std` 중앙값은 0.15–0.19 로 임계 바로 아래에서
계속 진동했다.

그런데 **M-N4 계약에는 진폭 게이트가 없다.** freshness/gap/MAD-epsilon 만 본다.
실제로 위 10개 창은 producer 가 DEGRADED 로 표시한 비율이 84–100 % 인데도 **전부 채택**됐고
MAD collapse 도 0건이었다. 즉 지금 방식대로 더 찍으면, 저진폭 데이터가 아무 표시 없이
학습 데이터에 들어간다.

→ 대응: (1) 창 단위 `producer_non_valid_fraction` 을 핸드오프에 **필수 동봉**한다
(도구가 이미 산출), (2) CAP-3 에서 진폭이 회복되는 거리/자세를 찾는다.
파일럿 거리는 45.9 cm 로 펌웨어 유효범위 `kDistanceMinCm = 40` 의 하단이었다.

**(b) USB serial 바이트 유실로 손상된 레코드 1건**

`pilot/M-C0-PILOT-STATIONARY-001.raw.jsonl:1030` 에서 인접 키가 융합된
`"breath_filtered_v_std"` 가 관측됨 (`breath_filtered_valid` + `breath_phase_std` 가
바이트 유실로 붙음). JSON 은 정상 파싱되므로 파싱 기반 QA 로는 잡히지 않는다.
빈도 1/3598. → QA 에 **미지 키 검출** 한 줄만 추가하면 충분하다.

### 1.5 §33 로컬 전용 미커밋 데이터

사전 조사 완료: **미반영 측정 데이터 0건.** 보고할 것 없음.

---

## 2. CAP-1 — 캡처 계약 (센서 없이 완료)

기존 스키마를 그대로 재사용한다. 새 디렉터리·새 매니페스트 스키마·새 검증기를 만들지 않는다
(§13, §29).

- `schemas/session_manifest.schema.json`, `schemas/raw_record.schema.json`
- `protocols/mc0_measurement_contract.json`
- `templates/session_manifest.planned.json`, `templates/environment_metadata.template.json`
- `tools/live_mr60_monitor.py` (raw JSONL 캡처), `tools/physical_capture_qa.py`
- `validators/validate_contract.py`

CAP-1 에서 추가한 것은 두 가지뿐이다.

1. `tools/cap0_m_n4_feasibility.py` — 세션이 M-N4 창을 몇 개 산출하는지 확인 (재사용)
2. `templates/capture_checklist.md` 의 **CAP-2/3 실행 조건** 절 (warmup·거리·길이·진폭)

subject ID 는 기존 규약 `SUBJ-PSEUDONYM-NNN` 를 유지한다. 사람과 세션은 별개이며,
한 사람의 인접 녹화가 서로 다른 ID 로 TRAIN/TEST 에 갈라지지 않게 한다.

---

## 3. CAP-2 / CAP-3 실측 결과 (2026-08-18 완료)

센서 연결 후 4개 세션을 기록했다. 전부 `validate_contract.py --check-files --strict-warnings` PASS.

### 3.1 세션 인벤토리 (§34)

| Session | Subject | Condition | Duration | Core phase | Freshness | Reference | Main limitation | Recommended use |
|---|---|---|---:|---|---|---|---|---|
| M-C0-20260818-CAP2-S001-01 | SUBJ-001 | 자연호흡·정지·앉음 52cm | 239.9 s | OK | DERIVED | none | 저진폭 43% | DEVICE_DOMAIN_REFERENCE |
| M-C0-20260818-CAP2-S001-02 | SUBJ-001 | 동일조건 반복 57cm | 239.9 s | OK | DERIVED | none | 저진폭 29% | DEVICE_DOMAIN_REFERENCE |
| M-C0-20260818-CAP3-S001-REBOOT-01 | SUBJ-001 | ESP 재부팅 후 52cm | 239.9 s | OK | DERIVED | none | 피험자 1명 | DEVICE_DOMAIN_REFERENCE |
| M-C0-20260818-CAP3-EMPTY-01 | SUBJ-NONE | 빈 방 | 240.0 s | 전부 0.0 | DERIVED | n/a | 호흡신호 없음(의도적) | FAILURE_QA_EVIDENCE |

총 canonical window 29개, 폐기 0. raw JSONL 은 기존 `raw/` ignore 정책에 따라 로컬 보관.

### 3.2 M-N4 수율

| 세션 | 창 | 폐기 | republication | phase_age max | 저진폭 |
|---|---:|---:|---:|---:|---:|
| CAP2-01 | 7 | 0 | 0 | 18 ms | 43 % |
| CAP2-02 | 7 | 0 | 0 | 18 ms | 29 % |
| REBOOT | 7 | 0 | 0 | 18 ms | 1 % |
| EMPTY | 8 | 0 | 0 | — | n/a |

네 세션 모두 10 Hz, 0.5 s 초과 끊김 0, uart/checksum 오류 0, seq 누락 0.

### 3.3 답이 나온 질문

**재부팅은 phase 스케일을 바꾸지 않는다.**

| 세션 | breath_phase 범위 | pstdev |
|---|---|---|
| CAP2-01 | −0.65 … +0.72 | 0.204 |
| CAP2-02 | −0.82 … +0.66 | 0.230 |
| REBOOT | −0.82 … +0.85 | 0.295 |

재부팅 후 값이 세션 간 자연 변동 범위 안에 있다. M-N4 의 `boot.window_may_cross_boot_or_restart: false` 는
타이밍(`ts_monotonic_ms` 리셋) 때문이지 스케일 변화 때문이 아니다. n=3 관찰이며 통계적 주장이 아니다.

**저진폭은 거리 문제가 아니다.** CAP-0 에서 세운 "파일럿 저진폭은 46 cm 때문"이라는 가설은 기각됐다.
파일럿과 같은 45.9/51.7 cm 에서 저진폭이 1 %까지 내려간 세션이 나왔고, CAP2-01 은 거리가 51.7 cm 로
고정된 상태에서 90–180 s 구간만 진폭이 내려갔다 회복했다. 호흡 깊이를 반영하는 신호로 본다.
→ 거리 특성화(CAP-3 잔여)의 우선순위를 낮춘다.

### 3.4 빈 방 세션 — presence gate 근거

모델 트랙 M-N7 의 `NO_PERSON_INFERENCE_GATING_HAZARD` 를 장치 쪽에서 재현했다.

```text
breath_phase      2400행 전부 정확히 0.0 (고유값 1종)
distance_cm_raw   2400행 전부 null
presence          2400행 전부 false
sensor_state      2400행 전부 UNKNOWN / PRESENCE_NOT_DETECTED

M-N4 창 8개 → 전부 채택, MAD=0, mad_collapsed=true (zero tensor)
```

**M-N4 는 빈 방을 거르지 않는다.** 계약의 `near_zero_behavior: ZERO_TENSOR` 대로 zero tensor 를 내보내고,
모델은 그것을 APNEA 로 읽는다. 이를 막을 수 있는 것은 presence gate 뿐이다.

다만 gate 가 쓸 producer 신호는 예외 0건으로 깨끗하다. Pi 런타임 담당자에게 그대로 넘길 수 있다.

---

## 4. CAP-5 핸드오프

모델 트랙이 소비할 것:

- raw: `raw/M-C0-20260818-*.jsonl` (로컬, SHA-256 은 각 manifest 의 `files.raw_jsonl`)
- manifest: `manifests/M-C0-20260818-*.session_manifest.json`
- QA: `qa/M-C0-20260818-*.qa.json`
- 창 수율/품질 재현: `python3 tools/cap0_m_n4_feasibility.py <raw.jsonl>`

세션당 반드시 함께 읽어야 하는 값은 `producer_non_valid_fraction` 이다.
M-N4 에 진폭 게이트가 없으므로, 저진폭 창을 구분하려면 이 값을 봐야 한다.

주의 두 가지가 각 manifest 노트에 기록돼 있다.

1. `distance_cm` 은 **장치 파생값**(`distance_cm_raw` 중앙값)이다. 줄자 실측이 아니므로
   운영자가 실측을 적은 `M-C0-PILOT-*` 의 값과 같은 성격으로 비교하면 안 된다.
2. `sensor_angle_deg = 100` 은 이번 세션들의 **운영자 기준**(책상면 기준, 90 = 책상에 수직)이다.
   `M-C0-PILOT-*` 의 `0`(가슴과 수평 정렬)과 다른 관례이므로 숫자를 직접 비교하면 안 된다.

---

## 5. CAP-6 — 차단됨

모델 트랙 M-N10 이 구체적 결손을 지목해 CAP-6 가 열렸다(§45). 근거는 담당자 메모의 다음 한 문장뿐이다.

> 현장에서 MR60+독립 호흡센서로 새 사람 최소 6명을 측정한 뒤 같은 PR에 두 번째 evidence commit

차단 요인 3가지:

| # | 차단 | 현황 | 해소 조건 |
|---|---|---|---|
| 1 | M-N10 측정 프로토콜 문서 | 이 저장소에 없음(main·PR 전수 확인) | 모델 담당자에게 요청 → `reports/MR60_CAP6_PROTOCOL_REQUEST.md` |
| 2 | 독립 호흡 레퍼런스 | 없음. `INDEPENDENT_REFERENCE = NOT_AVAILABLE` | 프로젝트 리드 결정(§24). M-N4 는 `MOVESENSE_CHEST_ACC` 계열을 전제 |
| 3 | 새 피험자 6명 | 1명(SUBJ-001) | 1·2 해소 후 모집 |

### 5.1 승인이 별도로 필요한 지점

M-N4 의 클래스 정의는 `APNEA = voluntary breath-hold overlap >= 6 s`, 즉 **자발적 숨 참기**를 전제한다.
센서 트랙 지시 §26 은 숨 참기·무호흡 시뮬레이션의 자율 수행을 금지한다.

따라서 CAP-6 프로토콜에 숨 참기가 포함될 경우, 장비·인원과 별개로 **참가자 안전 규칙을 포함한 별도 승인**이
필요하다. M-N10 문서에서 "MR60 측정으로 APNEA 를 얻을 계획인지"를 먼저 확인해야 한다.

---

## 6. 경계 (유지됨)

| 항목 | 상태 |
|---|---|
| 대규모 라벨 데이터셋 | NO |
| NORMAL/RAPID/APNEA 매핑 | NO |
| 숨 참기/무호흡 실험 | NO |
| 학습 / TFLite 추론 | NO |
| 구 B 모델 수정 | NO |
| 펌웨어 수정 | NO |
| raw 전처리 적용 | NO |

## 7. 현재 결손

1. 독립 respiration reference 없음 → supervised 주장 불가 (§37 Case C).
2. 피험자 1명 → `SUBJECT_DIVERSITY_LIMITED`. 처음 보는 사람에 대한 일반화 검증 불가.
3. M-N10 측정 규격 미확보 → CAP-6 착수 불가.
4. `distance_cm` 줄자 실측 미수행. 다음 세션에서 1회 재두면 해소된다.
5. 거리 특성화(80–110 cm) 미수행. 우선순위는 낮으나 미측정 상태.
