# SafeNest mmWave M-C1 Requirements Draft

Status: **documentation only — M-C1 remains `BLOCKED_HARDWARE`**

This draft records capture requirements derived from the measured M-C0
correspondence audit. It does not authorize M-C1 capture, inference, model
scoring, retraining, preprocessing changes, or LOCKED_TEST access.

## Why these requirements exist

The M-C0 audit of the long MR60 log
`devices/mmwave/firmware/logs/final/2026-08-01_occupied_d09_v120_31min_attempt02.jsonl`
measured telemetry row cadence separately from the phase-age reset proxy:
`9.986342911 Hz` versus `4.30467137 Hz`. The computation is recorded in the
M-C0 JSON artifacts as `(timestamp_count - 1) / timestamp_span` for row cadence
and `phase_age_ms` decrease count divided by timestamp span for the freshness
proxy. No session produced a valid 300-genuinely-fresh-sample window.

The nine legacy CSVs used by the historical window path do not contain
`phase_age_ms` or a 0x0A13 freshness identity. Reconstructing
`ondevice_ai/adapters/mmwave_csv_adapter.py` produced 620 historical input
windows, but freshness for every one of those windows is unobservable from the
CSV evidence. A nominal telemetry cadence therefore cannot be treated as a
proven fresh-phase cadence.

## M-C1 capture must guarantee

### 1. Fresh-phase update rate is measured per session

Every session must retain the raw freshness evidence needed to identify a
genuinely fresh phase update. The session report must include:

- telemetry row cadence;
- fresh-phase/0x0A13 update cadence measured independently;
- the exact fields and computation used to identify a fresh update; and
- an explicit status if the fresh cadence cannot be measured.

The row cadence must never be used as a substitute for fresh-phase cadence.
No assumed 10 Hz fresh-phase rate is acceptable.

### 2. `phase_age_ms` is logged and reported per session

Each session must preserve `phase_age_ms` (or an explicitly identified direct
freshness field) with timestamps and sequence information sufficient to audit
it. The session report must include the phase-age distribution:

- minimum;
- median;
- p95;
- maximum; and
- fraction over the selected reporting partition.

The M-C0 value of 30 seconds is only a reporting partition. A formal
`phase_age_ms` failure threshold remains **UNDEFINED** and is not set by this
draft.

### 3. Formal-evaluation eligibility requires one genuine window

A session is eligible for formal M-C1 evaluation only when it yields at least
one window containing `300` genuinely fresh samples. The freshness evidence
must support that claim; a row count, timestamp cadence, reset proxy, repeated
value, or interpolated sample does not by itself qualify.

The exact window overlap policy and any resampling policy remain unresolved and
must be decided and recorded before an approved M-C1 protocol is issued.

## Required per-session audit record

The capture record should preserve, at minimum, raw timestamp, sequence, phase,
phase-age/freshness field, distance/vitals fields, firmware/model identity,
session metadata, and file SHA-256. The derived report must cite the source
file and computation for every numeric claim. Missing freshness fields must be
reported as missing, not reconstructed silently from row cadence.

The following findings remain constraints for interpretation:

- the M-C0 decision is `BLOCKED_PENDING_SIGNAL_CORRESPONDENCE`;
- semantic correspondence is `UNDETERMINED`;
- temporal correspondence is `MEASURED_INSUFFICIENT`;
- `valid_300_fresh_windows` is `0` in the measured evidence;
- the 620-window legacy path diverges at freshness provenance before
  `BPF_ZSCORE`; and
- the all-APNEA historical collapse is not assigned to BPF, z-score, INT8, or
  the model by this document.

## Still undefined and not authorized here

This draft intentionally does not define or authorize:

- a numeric `phase_age_ms` failure threshold;
- a resampling or interpolation method;
- official measurement distances;
- independent M-C1 reference hardware;
- M-C1 sample size; or
- any paced-rpm-to-label mapping.

M-C1 remains `BLOCKED_HARDWARE` until the required independent hardware and an
approved capture protocol exist. No new capture was performed for this draft.
