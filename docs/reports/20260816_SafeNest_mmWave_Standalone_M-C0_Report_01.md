# SafeNest mmWave standalone M-C0 — before evidence access

- Phase: `M-C0`
- Branch: `codex/mmwave-m-c0-correspondence`
- Base commit: `0e8538c75354691fccf5f223029b0e633c1260af`
- Decision: **`BLOCKED_PENDING_SIGNAL_CORRESPONDENCE`**
- Blocking reason: **`EVIDENCE_NOT_ACCESSIBLE_IN_STANDALONE`**
- Correspondence evaluated: `false`
- Correspondence disproven: `false`
- Evidence-root supplied: `false`
- Model scoring/inference: **not executed**
- Raw modification: **none**

## Before-state statement

This commit records the required state before any evidence-root is supplied.
Correspondence failure was **NOT observed**; the audit could not run because raw
telemetry was absent from the standalone working tree. This is an access block,
not a measured correspondence failure.

The next step is to add read-only `--evidence-root` access, enumerate every
expected evidence item, hash the inputs, and rerun the audit without copying
raw MR60 JSONL/CSV into this repository.

## Preserved boundaries

- No inference, Accuracy/F1/confusion matrix, or model scoring.
- No retraining, preprocessing change, or INT8 recalibration.
- No LOCKED_TEST reopening or tuning.
- No new M-C1 capture.
- No raw JSONL/CSV modification or commit.
- No paced-rpm-to-class mapping and no clinical apnea claim.

## What remains unknown

- `breath_phase` semantic and numeric correspondence to the frozen Phase-B input.
- Fresh `0x0A13` cadence separately from telemetry row cadence.
- Per-session timestamp integrity and `phase_age_ms` distributions.
- Whether any session provides 300 genuinely fresh samples over approximately 30 seconds.
- Interpolation/resampling method and measured distortion.
- MR60 pre-INT8 and post-INT8 distributions against the frozen training distribution.
- The transform stage responsible for the historical 620/620 APNEA exploratory collapse.
- Independent reference hardware, formal M-C1 sample size, and paced-rpm label mapping.
