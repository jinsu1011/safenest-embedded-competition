# MR60 SENSOR-OWNER ACQUISITION ROADMAP (MR60-CAP)

작성일: 2026-08-18
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

## 3. 남은 단계 (센서 필요)

### CAP-2 — 소규모 중립 다피험자 파일럿
자연호흡, 정지, 자세 명시, 피험자당 **4 분**(60 s warmup + 6 창).
가능하면 3명 이상. 1–2명이면 `SUBJECT_DIVERSITY_LIMITED` 로 신고하고 진행.
게이트: `cap0_m_n4_feasibility.py` 로 창 채택률과 `producer_non_valid_fraction` 확인.

### CAP-3 — 반복성 + 최소 기하 변형
동일 피험자 2회차 1건, ESP 재부팅 후 1건.
기하 변형은 **거리 1건만** — 파일럿 45.9 cm 대비 **80–100 cm** 를 권장한다
(진폭 회복 여부 확인이 목적이며, 매트릭스를 만들지 않는다).

### CAP-4 — paced 특성화 (선택)
저부담일 때만. `intended_paced_rate` / 독립 reference / `breath_rate_raw` 를 각각 분리 기록.
cue 를 ground truth 로 쓰지 않는다. 클래스 매핑 금지.

### CAP-5 — 핸드오프
세션별 raw 경로 + manifest + QA + `cap0_m_n4_feasibility.py` 출력 + 한계.

### CAP-6 — 표적 캡처
자동 실행하지 않는다. 모델 트랙이 구체적 결손을 지목한 뒤에만 연다.

---

## 4. 경계 (유지됨)

| 항목 | 상태 |
|---|---|
| 대규모 라벨 데이터셋 | NO |
| NORMAL/RAPID/APNEA 매핑 | NO |
| 숨 참기/무호흡 실험 | NO |
| 학습 / TFLite 추론 | NO |
| 구 B 모델 수정 | NO |
| 펌웨어 수정 | NO (제안조차 현재 근거상 보류) |
| raw 전처리 적용 | NO |

## 5. 현재 결손

1. 독립 respiration reference 없음. 계약이 지목한 표준은 `MOVESENSE_CHEST_ACC` 이며,
   확보 여부는 프로젝트 리드 결정 사항이다. 없으면 supervised 주장 불가 (§37 Case C).
2. 물리 피험자 1명 (`m_n4_canonical_input_dataset_contract.json` 기준). CAP-2 의 존재 이유.
3. 파일럿 전 구간이 producer 기준 저진폭. 거리/자세 재현 조건이 미확정.
4. 재부팅 간 phase 스케일 안정성 미측정 (CAP-3).
