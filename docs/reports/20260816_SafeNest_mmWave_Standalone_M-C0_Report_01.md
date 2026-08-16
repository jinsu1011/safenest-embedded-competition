# SafeNest mmWave standalone M-C0 correspondence audit

- Repository: `jinsu1011/safenest-embedded-competition`
- Branch: `codex/mmwave-m-c0-correspondence`
- Head at audit: `b88d1a597839b7bb803dc2590e0de55e187c959e`
- Evidence-root used: `devices/mmwave/firmware`
- Decision: **`BLOCKED_PENDING_SIGNAL_CORRESPONDENCE`**
- Blocking reason: **`SIGNAL_CORRESPONDENCE_NOT_ESTABLISHED`**
- Correspondence evaluated: `true`
- Correspondence disproven: `false`
- Model scoring/inference: **not executed**
- Raw modification/copy: **none**

## Method and write boundary

The script opened `2528` regular files below the evidence-root in `rb` read-only mode and separately SHA-256 hashed every present file in the enumerated expected input set. All output paths were asserted to be outside the evidence-root. Raw MR60 JSONL/CSV remained in place and was not copied into the repository.

Numeric conventions:
- telemetry row cadence = `(timestamp_count - 1) / (last_timestamp - first_timestamp)`
- fresh 0x0A13 cadence = count of `phase_age_ms` decreases divided by timestamp span; this is an inferred reset proxy, not a direct packet counter
- phase-age p95 uses linear percentile interpolation; `>30,000 ms` is a reporting partition, not an official failure threshold
- 30-second fresh-window count uses fixed non-overlapping 30-second bins and counts bins with at least 300 reset-proxy events
- phase rpm = 60 divided by the median interval between positive crossings of the session-mean-centered phase; it is a signal diagnostic, not a paced-cue-to-label mapping
- interpolation and INT8 calculations are diagnostics only; the frozen BPF/resampling contract was not silently applied

## Expected evidence and SHA-256

| Expected item | Status | Evidence path (repo-relative, personal path component redacted) | Records | SHA-256 |
|---|---|---|---:|---|
| `S001_NORMAL_D06` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-25_occupied_d06_v1_360s__S001_NORMAL_D06.csv` | 2998 | `8a2b8cb8aa017110672fd3045f0d2b0228dfc7da6e40f6ce30e03dbca9cfee98` |
| `S001_NORMAL_D09` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-25_occupied_d09_v1_360s__S001_NORMAL_D09.csv` | 2998 | `23c7eb303f679cd6134c84db8d735c756f70c39a21de8e41bca77b7e4889505b` |
| `S001_NORMAL_D12` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-25_occupied_d12_v1_360s__S001_NORMAL_D12.csv` | 2998 | `4b52b83367f67e6f317bb3178c641372eb9f5f81c4b9535dba3008c5aef04617` |
| `S001_NORMAL_D15` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-25_occupied_d15_v1_360s__S001_NORMAL_D15.csv` | 2999 | `cf98144314ba2e339a7dd660f2ce5e1296dc7d83bf81b994ba3e77d06245c60e` |
| `S001_BREATH_PACED_12_01` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-25_breath_paced_12rpm__S001_BREATH_PACED_12_01.csv` | 2087 | `2502ff4d4f66613c062231ec3a3a2de8d3a045fdb1efe52731c87cff364478fb` |
| `S001_BREATH_PACED_12_02` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-28_breath_paced_12rpm_explicit_v2_attempt03__S001_BREATH_PACED_12_02.csv` | 1774 | `6ea49a108e89c7b1627cb3f04009ea1ae0a05d13b82c54a92de5d3b72a799de1` |
| `S001_BREATH_PACED_15_03` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-26_breath_paced_15rpm__S001_BREATH_PACED_15_03.csv` | 1779 | `5d630fd40a59a2b484581584ac311f85c507503bb5856eea6b84327b75b3c645` |
| `S001_BREATH_PACED_20_04` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-26_breath_paced_20rpm__S001_BREATH_PACED_20_04.csv` | 1784 | `87e9292254cef55696f25d1550b295612f7f2721bb79dd61306e4c02650b88dd` |
| `S001_BREATH_PACED_20_05` | `PRESENT` | `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-26_breath_paced_20rpm_deep__S001_BREATH_PACED_20_05.csv` | 1784 | `6bd13bd5de4242fc3147746031b236516947dfebb85923ef1421f88413444a06` |
| `2026-08-01_occupied_d09_v120_31min_attempt02` | `PRESENT` | `devices/mmwave/firmware/logs/final/2026-08-01_occupied_d09_v120_31min_attempt02.jsonl` | 18574 | `7f9e9ac65377c6dc217af92f9dee2401b6162540e2245fce97acf2ed49368a34` |
| `M-C0-PILOT-DESKWORK-001` | `KNOWN_BUT_NOT_PROVIDED` | `['devices/mmwave/firmware/device_measurements/M-C0-PILOT-DESKWORK-001.jsonl', 'devices/mmwave/firmware/device_measurements/M-C0-PILOT-DESKWORK-001/records.jsonl']` | 1799 | `—` |
| `M-C0-PILOT-STATIONARY-001` | `KNOWN_BUT_NOT_PROVIDED` | `['devices/mmwave/firmware/device_measurements/M-C0-PILOT-STATIONARY-001.jsonl', 'devices/mmwave/firmware/device_measurements/M-C0-PILOT-STATIONARY-001/records.jsonl']` | 1799 | `—` |

Present expected files: `10` / `12`. Missing items were recorded as `KNOWN_BUT_NOT_PROVIDED`; they were not silently skipped.

## Per-session measured findings

| Session | Records | Row Hz | Fresh 0x0A13 Hz | Phase rpm | Phase age min / median / p95 / max ms | >30 s | 300-fresh windows | Interp RMSE |
|---|---:|---:|---:|---:|---|---:|---:|---:|
| `S001_NORMAL_D06` | 2998 | 9.994964166 | N/A | 20.04468266 | None / None / None / None | None | 0 | N/A |
| `S001_NORMAL_D09` | 2998 | 9.99613096 | N/A | 19.699214478 | None / None / None / None | None | 0 | N/A |
| `S001_NORMAL_D12` | 2998 | 9.995797563 | N/A | 20.266696872 | None / None / None / None | None | 0 | N/A |
| `S001_NORMAL_D15` | 2999 | 9.998365844 | N/A | None | None / None / None / None | None | 0 | N/A |
| `S001_BREATH_PACED_12_01` | 2087 | 9.995304219 | N/A | 10.598330195 | None / None / None / None | None | 0 | N/A |
| `S001_BREATH_PACED_12_02` | 1774 | 9.995433558 | N/A | 12.18605948 | None / None / None / None | None | 0 | N/A |
| `S001_BREATH_PACED_15_03` | 1779 | 9.994097974 | N/A | 14.928893032 | None / None / None / None | None | 0 | N/A |
| `S001_BREATH_PACED_20_04` | 1784 | 9.994226554 | N/A | 20.170279064 | None / None / None / None | None | 0 | N/A |
| `S001_BREATH_PACED_20_05` | 1784 | 9.992994255 | N/A | 20.030636268 | None / None / None / None | None | 0 | N/A |
| `2026-08-01_occupied_d09_v120_31min_attempt02` | 18574 | 9.986342911 | 4.30467137 | 19.264097775 | 0.0 / 12.0 / 195627.0 / 288530.0 | 0.139173038 | 0 | 0.008928878 |

## Preserved measurement corrections

- `S001_NORMAL_D15`: the finite `range_m` sample standard deviation is `2.93759692` cm, computed from `2639` rows in `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/2026-07-25_occupied_d15_v1_360s__S001_NORMAL_D15.csv`. The same file's `resp_phase` population std is `0.0`; the frozen value is the phase/vitals signal, not distance.
- `S001_BREATH_PACED_12_01` is not treated as a 12-rpm ground truth: `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/DELIVERY_NOTES.md` records an actual trial of approximately `6.06` rpm. The cue remains metadata only.
- Existing project records retain the corrected phase periods `12.34` / `15.00–15.01` / `20.00` rpm versus vendor medians `14.0` / `19.0` / `23.0` (`docs/operations/PROJECT_PROGRESS.md` and the delivery notes). These are measurement notes and do not create a paced-rpm-to-class mapping.
- The phase-rpm values in the table are independently recomputed from each listed evidence file using the positive-crossing formula above; they are not substituted with paced cues or vendor medians.

### Question 1 — signal-semantic correspondence

`breath_phase`/`resp_phase` was present and periodic components were measurable in the supplied legacy captures. That establishes a phase-like telemetry signal, not equivalence to the frozen Phase-B `resp_phase_model_ready_bpf_zscore` semantic. No independent canonical reference waveform is present, so the measured assessment is `PHASE_LIKE_SIGNAL_OBSERVED_BUT_PHASE_B_EQUIVALENCE_NOT_ESTABLISHED`; `correspondence_disproven=false`.

### Question 2 — `breath_rate_raw` as waveform input

The measured answer is **no**. The static pipeline scan found waveform input paths `["devices/mmwave/firmware/export_mmwave_csv.py", "devices/mmwave/firmware/src/main.cpp", "devices/mmwave/src/mr60_esp_adapter.py", "ondevice_ai/adapters/mmwave_csv_adapter.py", "ondevice_ai/inference/mmwave_interpreter.py"]` and recorded `breath_rate_raw` only in telemetry/export/diagnostic matches. Per-session parsing also used `{"legacy_csv": "resp_phase", "long_jsonl": "breath_phase"}` as the waveform field.

### Question 3 — row cadence vs fresh cadence

The table reports the two cadences separately. Legacy CSV has no `phase_age_ms`/0x0A13 freshness field, so its fresh cadence is `N/A`, not assumed to be the row cadence. The long log reports an inferred cadence from phase-age resets and labels it as a proxy.

### Question 4 — timestamp integrity

Per-session gaps, duplicates, non-monotonic timestamps, timestamp freezes, sequence loss, and freeze flags are in `offline_contract_correspondence.json` under `per_session[].timestamp_integrity`. Gap counts use the diagnostic threshold stated above; no official phase-age failure threshold was invented.

### Question 5 — `phase_age_ms` distribution

The long JSONL's min/median/p95/max and fraction over 30 seconds are measured in the table and JSON. Legacy CSV sessions report `FIELD_NOT_PRESENT`, so no phase-age statistic is fabricated.

### Question 6 — 300 genuinely fresh samples

The measured count is shown per session. A value of `0` means no fixed 30-second bin contained 300 phase-age reset-proxy events. CSV sessions are additionally marked not provable because freshness metadata is absent.

### Question 7 — interpolation

Interpolation was **not applied** to any audit input. Where phase-age reset proxies existed, linear interpolation was simulated only to quantify distortion; its RMSE/MAE/max-absolute error are reported per session. The method remains unresolved.

### Question 8 — BPF + z-score identity

The answer is **not established as identical**. The frozen contract is `M-B10B_SELECTED_REAL_CANDIDATE_BPF_ZSCORE_V1` with 0.1–0.5 Hz, order 4, zero-phase filtfilt, mean `0.0031162832173884064`, and std `2.955399434649939`. Raw phase statistics and a clearly labeled affine-only proxy are in each session result; no BPF was silently substituted.

### Question 9 — pre/post INT8 distribution

The JSON contains diagnostic before-INT8, after-INT8-dequantized, quantized integer, saturation, and quantization-error distributions using scale `0.041720833629369736` and zero-point `-3`. Because BPF was not reconstructed, these are explicitly non-contract-equivalent diagnostics. The auxiliary frozen training reference, when available, is hashed and cited in the JSON.

### Question 10 — 620/620 all-APNEA collapse stage

No stage is assigned. This run did not replay inference, and the expected evidence set contains no stage-labeled 620/620 replay artifact. Inference remains prohibited until the correspondence gate authorizes it; the collapse stage therefore remains unresolved rather than guessed.

## Decision

**`BLOCKED_PENDING_SIGNAL_CORRESPONDENCE`** with `correspondence_evaluated=true` and `correspondence_disproven=false`. The result is measured and successful as a block: phase-like telemetry is present, but the frozen Phase-B semantic, fresh 300-sample window, and exact preprocessing/INT8 distribution correspondence are not established. Exploratory inference is not authorized.

## What remains unknown

- Exact physical/numeric semantic mapping from MR60 `breath_phase` to the frozen Phase-B input.
- Official phase-age failure threshold; 30 seconds is only a reporting partition here.
- Direct 0x0A13 packet identity/update cadence versus phase-age reset proxy.
- Approved interpolation/resampling method and its acceptable distortion.
- Formal pre-BPF/post-BPF training-distribution comparison for MR60.
- Stage responsible for the historical all-APNEA collapse.
- Independent M-C1 reference hardware, sample size, and paced-rpm-to-label mapping.
- Official measurement distances; practical starting points and freeze observations remain evidence, not a frozen protocol.

## Boundaries preserved

No retraining, preprocessing change, INT8 recalibration, LOCKED_TEST reopening, M-C1 capture, clinical apnea claim, paced-cue class mapping, or raw-file modification was performed.
