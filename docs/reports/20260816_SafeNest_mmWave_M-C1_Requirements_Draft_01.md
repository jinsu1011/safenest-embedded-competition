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

## PR18 pilot consequence for capture tooling

The two PR18 pilot captures resolve the M-C0 alternatives in favour of (a):
the measured limitation is supported as structural to the audited MR60/ESP
telemetry path, rather than specific to the 2026-07-26 legacy CSV capture
method. `M-C0-PILOT-DESKWORK-001` measured `3.679658492 Hz` and
`M-C0-PILOT-STATIONARY-001` measured `3.518230325 Hz`, while their telemetry
row cadences were `9.993996932 Hz` and `9.993330369 Hz`, respectively. These
values are recorded separately under `PR18_PILOT_CAPTURE` in
`datasets/mmwave/manifests/M-C0_correspondence_audit/m_c0_summary.json`; each
fresh-cadence proxy is computed as the count of `phase_age_ms` decreases divided
by that pilot's timestamp span. The comparison classifies (a) because both
pilot values are closer to the independently measured legacy fresh-cadence
proxy of `4.30467137 Hz` than to nominal 10 Hz telemetry rows.

Consequently, M-C1 capture tooling must change the acquisition boundary used
for eligibility. It must:

- record each source 0x0A13/phase update when received, with an update identity,
  source timestamp, sequence, and freshness provenance, rather than treating a
  periodic re-emission of the last stored phase as a new sample;
- count genuinely fresh source updates, not emitted telemetry rows, and fail
  closed unless a candidate window contains 300 independently identifiable
  fresh updates;
- prevent stale repeats, interpolation, or synthesis from increasing the fresh
  sample count; and
- instrument the upstream MR60-to-ESP receive path so the project can determine
  whether that boundary can supply a contract-eligible window. If it cannot,
  the current capture path remains ineligible and a different acquisition
  capability must be selected through a separately approved protocol.

This consequence does not choose a numeric `phase_age_ms` threshold, a
resampling method, an official distance, reference hardware, or sample size.
Those remain **UNDEFINED**, and this finding does not authorize capture.

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
