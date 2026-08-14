#!/usr/bin/env python3
"""Compute machine-readable QA for one immutable MR60 physical JSONL capture."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter
from pathlib import Path


NUMERIC_FIELDS = (
    "distance_cm_raw",
    "breath_rate_raw",
    "breath_rate_filtered",
    "breath_phase_std",
    "heart_rate_raw",
    "total_phase",
    "breath_phase",
    "heart_phase",
    "distance_std_cm",
)

COVERAGE_FIELDS = (
    "human_detected_raw",
    "human_detected_stable",
    *NUMERIC_FIELDS,
    "sensor_firmware_version",
)


def finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(fraction * len(ordered)) - 1)
    return ordered[index]


def rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 6)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-jsonl", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    records: list[dict] = []
    malformed_lines: list[int] = []
    with args.raw_jsonl.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                malformed_lines.append(line_number)
                continue
            if not isinstance(record, dict):
                malformed_lines.append(line_number)
                continue
            records.append(record)

    intervals_ms: list[float] = []
    sequence_gap_events = 0
    missing_sequences = 0
    sequence_duplicates = 0
    sequence_backwards = 0
    timestamp_duplicates = 0
    timestamp_backwards = 0
    previous_seq = None
    previous_ts = None
    for record in records:
        seq = record.get("seq")
        ts = record.get("ts_monotonic_ms")
        if isinstance(seq, int) and not isinstance(seq, bool) and previous_seq is not None:
            delta = seq - previous_seq
            if delta > 1:
                sequence_gap_events += 1
                missing_sequences += delta - 1
            elif delta == 0:
                sequence_duplicates += 1
            elif delta < 0:
                sequence_backwards += 1
        if isinstance(ts, int) and not isinstance(ts, bool) and previous_ts is not None:
            delta_ms = float(ts - previous_ts)
            if delta_ms > 0:
                intervals_ms.append(delta_ms)
            elif delta_ms == 0:
                timestamp_duplicates += 1
            else:
                timestamp_backwards += 1
        if isinstance(seq, int) and not isinstance(seq, bool):
            previous_seq = seq
        if isinstance(ts, int) and not isinstance(ts, bool):
            previous_ts = ts

    mean_interval = statistics.fmean(intervals_ms) if intervals_ms else None
    duration_ms = (
        records[-1].get("ts_monotonic_ms") - records[0].get("ts_monotonic_ms")
        if len(records) >= 2
        and isinstance(records[0].get("ts_monotonic_ms"), int)
        and isinstance(records[-1].get("ts_monotonic_ms"), int)
        else None
    )

    coverage = {}
    for field in COVERAGE_FIELDS:
        populated = sum(record.get(field) is not None for record in records)
        coverage[field] = {
            "populated": populated,
            "ratio": rounded(populated / len(records)) if records else None,
        }

    numeric_ranges = {}
    for field in NUMERIC_FIELDS:
        values = [float(record[field]) for record in records if finite(record.get(field))]
        numeric_ranges[field] = {
            "count": len(values),
            "min": rounded(min(values)) if values else None,
            "max": rounded(max(values)) if values else None,
            "mean": rounded(statistics.fmean(values)) if values else None,
            "median": rounded(statistics.median(values)) if values else None,
        }

    state_counts = Counter(str(record.get("sensor_state")) for record in records)
    error_counts = Counter(str(record.get("error_code")) for record in records)
    uart_bad = sum(record.get("uart_frame_ok") is not True for record in records)
    checksum_bad = sum(record.get("checksum_ok") is not True for record in records)
    heart_verified_true = sum(record.get("heart_verified") is True for record in records)

    stream_integrity_pass = not any((
        malformed_lines,
        sequence_gap_events,
        sequence_duplicates,
        sequence_backwards,
        timestamp_duplicates,
        timestamp_backwards,
        uart_bad,
        checksum_bad,
    ))

    result = {
        "qa_schema_version": "m-c0-physical-qa-1.0",
        "raw": {
            "path": args.raw_jsonl.as_posix(),
            "sha256": hashlib.sha256(args.raw_jsonl.read_bytes()).hexdigest(),
            "byte_count": args.raw_jsonl.stat().st_size,
            "physical_lines": len(records) + len(malformed_lines),
            "valid_json_records": len(records),
            "malformed_line_count": len(malformed_lines),
            "malformed_lines": malformed_lines,
        },
        "identity": {
            "device_ids": sorted({str(record.get("device_id")) for record in records}),
            "firmware_versions": sorted({str(record.get("firmware_version")) for record in records}),
            "sensor_firmware_versions": sorted({str(record.get("sensor_firmware_version")) for record in records}),
            "config_hashes": sorted({str(record.get("config_hash")) for record in records}),
        },
        "sequence": {
            "first": records[0].get("seq") if records else None,
            "last": records[-1].get("seq") if records else None,
            "gap_events": sequence_gap_events,
            "missing_sequences": missing_sequences,
            "duplicates": sequence_duplicates,
            "backwards": sequence_backwards,
        },
        "timing": {
            "first_ts_monotonic_ms": records[0].get("ts_monotonic_ms") if records else None,
            "last_ts_monotonic_ms": records[-1].get("ts_monotonic_ms") if records else None,
            "duration_ms": duration_ms,
            "effective_cadence_hz": rounded(1000.0 / mean_interval) if mean_interval else None,
            "mean_interval_ms": rounded(mean_interval),
            "median_interval_ms": rounded(statistics.median(intervals_ms)) if intervals_ms else None,
            "p95_interval_ms": rounded(percentile(intervals_ms, 0.95)),
            "jitter_pstdev_ms": rounded(statistics.pstdev(intervals_ms)) if intervals_ms else None,
            "maximum_gap_ms": rounded(max(intervals_ms)) if intervals_ms else None,
            "gap_over_500ms": sum(value > 500.0 for value in intervals_ms),
            "duplicate_timestamps": timestamp_duplicates,
            "backward_timestamps": timestamp_backwards,
            "nominal_30s_windows": math.floor(duration_ms / 30000) if duration_ms is not None else 0,
        },
        "communication": {
            "uart_bad": uart_bad,
            "checksum_bad": checksum_bad,
        },
        "coverage": coverage,
        "numeric_ranges": numeric_ranges,
        "sensor_state_counts": dict(sorted(state_counts.items())),
        "error_code_counts": dict(sorted(error_counts.items())),
        "heart_verified_true": heart_verified_true,
        "stream_integrity_pass": stream_integrity_pass,
        "claim_boundaries": {
            "physical_signal_captured": bool(records),
            "respiration_accuracy_verified": False,
            "heart_accuracy_verified": False,
            "clinical_apnea_validated": False,
            "deployment_ready": False,
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if stream_integrity_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
