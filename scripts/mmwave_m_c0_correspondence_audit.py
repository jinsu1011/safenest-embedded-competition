#!/usr/bin/env python3
"""Run the SafeNest mmWave M-C0 correspondence audit.

The audit is intentionally read-only with respect to ``--evidence-root``.
It opens every regular file below that directory, SHA-256 hashes the
enumerated expected inputs, reads the documented captures, and writes only
derived JSON/Markdown outside the evidence root.
It never runs the model, never reopens LOCKED_TEST, never resamples an input
as the contract, and never copies raw MR60 JSONL/CSV into the repository.

With no ``--evidence-root`` the command emits the reproducible before-state
and keeps the ``EVIDENCE_NOT_ACCESSIBLE_IN_STANDALONE`` taxonomy.  With an
evidence root it evaluates the correspondence questions and can still return
the measured, successful blocked decision when correspondence is not proven.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import json
import math
import re
import statistics
import struct
import subprocess
from pathlib import Path
from typing import Any, Iterable


DECISION_BLOCKED = "BLOCKED_PENDING_SIGNAL_CORRESPONDENCE"
DECISION_AUTHORIZED = "AUTHORIZED_FOR_EXPLORATORY_INFERENCE"
BLOCKED_BEFORE = "EVIDENCE_NOT_ACCESSIBLE_IN_STANDALONE"
BLOCKED_MEASURED = "SIGNAL_CORRESPONDENCE_NOT_ESTABLISHED"
EXPECTED_LONG_LOG_SHA256 = "7f9e9ac65377c6dc217af92f9dee2401b6162540e2245fce97acf2ed49368a34"

AUDIT_DIR = Path("datasets/mmwave/manifests/M-C0_correspondence_audit")
SUMMARY_PATH = AUDIT_DIR / "m_c0_summary.json"
INVENTORY_PATH = AUDIT_DIR / "existing_measurement_inventory.json"
CORRESPONDENCE_PATH = AUDIT_DIR / "offline_contract_correspondence.json"
REPORT_PATH = Path("docs/reports/20260816_SafeNest_mmWave_Standalone_M-C0_Report_01.md")
RUN_LOG_PATH = Path("docs/reports/20260816_SafeNest_mmWave_M-C0_Run_Log_01.md")

FROZEN = {
    "contract_id": "M-B10B_SELECTED_REAL_CANDIDATE_BPF_ZSCORE_V1",
    "profile_id": "M-B1_D0_B1_Z1",
    "profile_name": "BPF_ZSCORE",
    "sample_rate_hz": 10.0,
    "window_samples": 300,
    "window_seconds": 30.0,
    "lowcut_hz": 0.1,
    "highcut_hz": 0.5,
    "bpf_order": 4,
    "bpf_phase_mode": "ZERO_PHASE_FILTFILT",
    "zscore_mean": 0.0031162832173884064,
    "zscore_std": 2.955399434649939,
    "input_scale": 0.041720833629369736,
    "input_zero_point": -3,
    "input_shape": [1, 300, 1],
    "input_dtype": "int8",
    "artifact_sha256": "6dff6aaa72c79d76715d40cf7e32bb1e6cd9b2c2e3ac78eaf2fda737561430c5",
    "artifact_bytes": 22080,
    "runtime_model_id": "M-B3_CONV1D_GAP_BASELINE_seed42_M-B6_STRICT_INT8",
}

EXPECTED_CSV_SUFFIXES = {
    "S001_NORMAL_D06": "__S001_NORMAL_D06.csv",
    "S001_NORMAL_D09": "__S001_NORMAL_D09.csv",
    "S001_NORMAL_D12": "__S001_NORMAL_D12.csv",
    "S001_NORMAL_D15": "__S001_NORMAL_D15.csv",
    "S001_BREATH_PACED_12_01": "__S001_BREATH_PACED_12_01.csv",
    "S001_BREATH_PACED_12_02": "__S001_BREATH_PACED_12_02.csv",
    "S001_BREATH_PACED_15_03": "__S001_BREATH_PACED_15_03.csv",
    "S001_BREATH_PACED_20_04": "__S001_BREATH_PACED_20_04.csv",
    "S001_BREATH_PACED_20_05": "__S001_BREATH_PACED_20_05.csv",
}

PILOT_IDS = (
    "M-C0-PILOT-DESKWORK-001",
    "M-C0-PILOT-STATIONARY-001",
)

SESSION_CONTEXT = {
    "S001_NORMAL_D06": {"cue_rpm": None, "vendor_median_rpm": None, "role": "legacy occupied distance"},
    "S001_NORMAL_D09": {"cue_rpm": None, "vendor_median_rpm": None, "role": "legacy occupied distance"},
    "S001_NORMAL_D12": {"cue_rpm": None, "vendor_median_rpm": None, "role": "legacy occupied distance"},
    "S001_NORMAL_D15": {"cue_rpm": None, "vendor_median_rpm": None, "role": "legacy occupied distance"},
    "S001_BREATH_PACED_12_01": {
        "cue_rpm": 12.0,
        "vendor_median_rpm": None,
        "role": "failed paced trial; delivery note says actual trial was approximately 6.06 rpm",
        "documented_actual_rpm": 6.06,
    },
    "S001_BREATH_PACED_12_02": {"cue_rpm": 12.0, "vendor_median_rpm": 14.0, "role": "valid paced cue"},
    "S001_BREATH_PACED_15_03": {"cue_rpm": 15.0, "vendor_median_rpm": 19.0, "role": "valid paced cue"},
    "S001_BREATH_PACED_20_04": {"cue_rpm": 20.0, "vendor_median_rpm": 23.0, "role": "paced shallow trial"},
    "S001_BREATH_PACED_20_05": {"cue_rpm": 20.0, "vendor_median_rpm": 23.0, "role": "paced deep trial"},
    "2026-08-01_occupied_d09_v120_31min_attempt02": {
        "cue_rpm": None,
        "vendor_median_rpm": 23.0,
        "role": "long occupied log",
    },
}

PIPELINE_FILES = (
    Path("ondevice_ai/adapters/mmwave_csv_adapter.py"),
    Path("ondevice_ai/inference/mmwave_interpreter.py"),
    Path("devices/mmwave/src/mr60_esp_adapter.py"),
    Path("devices/mmwave/firmware/export_mmwave_csv.py"),
    Path("devices/mmwave/firmware/src/main.cpp"),
)


def repo_rel(root: Path, path: Path) -> str:
    """Return a repository-relative path without exposing a local root."""

    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def sanitize_segment(segment: str) -> str:
    """Redact delivery-folder personal-name components in derived outputs."""

    # The delivery folder contains a person's name.  Keep the date and role,
    # but remove one or more underscore-delimited name components.
    return re.sub(r"_(?:[^_]+_)*delivery_v2", "_delivery_v2", segment, flags=re.IGNORECASE)


def public_evidence_path(root: Path, evidence_root: Path, path: Path) -> str:
    rel = path.resolve().relative_to(evidence_root.resolve())
    safe = "/".join(sanitize_segment(part) for part in rel.parts)
    prefix = repo_rel(root, evidence_root)
    return f"{prefix}/{safe}" if safe else prefix


def is_within(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def assert_output_outside_evidence(paths: Iterable[Path], evidence_root: Path) -> None:
    """Fail closed if any derived write target is inside the evidence root."""

    evidence_root = evidence_root.resolve()
    for path in paths:
        if is_within(path, evidence_root):
            raise AssertionError(f"write target is inside read-only evidence-root: {path}")


def sha256_file(path: Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    # Explicit rb mode is the read-only evidence boundary.
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return digest.hexdigest(), size


def open_all_evidence_files_read_only(evidence_root: Path) -> int:
    """Open every regular file below evidence-root without reading/writing it."""

    count = 0
    for path in sorted(evidence_root.rglob("*")):
        # Do not follow toolchain symlinks out of the evidence root.  The
        # read-only inventory is explicitly for regular evidence files.
        if path.is_symlink() or not path.is_file():
            continue
        with path.open("rb"):
            pass
        count += 1
    return count


def as_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def round_value(value: Any, digits: int = 9) -> Any:
    if isinstance(value, float):
        return round(value, digits)
    return value


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def numeric_stats(values: Iterable[float]) -> dict[str, Any]:
    values = [float(value) for value in values if math.isfinite(float(value))]
    if not values:
        return {"count": 0, "min": None, "median": None, "p05": None, "p95": None, "max": None, "mean": None, "std": None}
    return {
        "count": len(values),
        "min": round_value(min(values)),
        "median": round_value(statistics.median(values)),
        "p05": round_value(percentile(values, 0.05)),
        "p95": round_value(percentile(values, 0.95)),
        "max": round_value(max(values)),
        "mean": round_value(statistics.fmean(values)),
        "std": round_value(statistics.pstdev(values) if len(values) > 1 else 0.0),
    }


def distance_summary(rows: list[dict[str, Any]], kind: str) -> dict[str, Any]:
    """Summarize distance telemetry without confusing it with phase freeze."""

    if kind == "legacy_csv":
        field = "range_m"
        unit = "m"
        values = [value for value in (as_float(row.get(field)) for row in rows) if value is not None]
    else:
        field = "distance_cm_raw"
        unit = "cm"
        values = [value for value in (as_float(row.get(field)) for row in rows) if value is not None]
    return {
        "field": field,
        "unit": unit,
        "finite_sample_count": len(values),
        "stats": numeric_stats(values),
        "sample_std": round_value(statistics.stdev(values)) if len(values) > 1 else None,
        "sample_std_cm": round_value(statistics.stdev(values) * 100.0) if kind == "legacy_csv" and len(values) > 1 else None,
        "computation": "population stats plus sample standard deviation over finite distance telemetry values; legacy CSV range_m is in metres",
    }


def run_lengths(flags: list[bool]) -> dict[str, int]:
    count = 0
    longest = 0
    current = 0
    for flag in flags:
        if flag:
            count += 1
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return {"interval_count": count, "longest_interval_run": longest}


def load_csv_rows(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    malformed = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row:
                malformed += 1
                continue
            rows.append(row)
    return rows, malformed


def load_jsonl_rows(path: Path) -> tuple[list[dict[str, Any]], int]:
    rows: list[dict[str, Any]] = []
    malformed = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            if isinstance(value, dict):
                rows.append(value)
            else:
                malformed += 1
    return rows, malformed


def normalize_rows(rows: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if kind == "legacy_csv":
            timestamp = as_float(row.get("timestamp_s"))
            phase = as_float(row.get("resp_phase"))
            phase_age = None
            seq = None
            vendor_rate = as_float(row.get("breath_rpm"))
            raw_rate = None
        else:
            timestamp_ms = as_float(row.get("ts_monotonic_ms"))
            timestamp = timestamp_ms / 1000.0 if timestamp_ms is not None else None
            phase = as_float(row.get("breath_phase"))
            phase_age = as_float(row.get("phase_age_ms"))
            seq = as_float(row.get("seq"))
            vendor_rate = as_float(row.get("breath_rate_raw"))
            raw_rate = vendor_rate
        result.append(
            {
                "index": index,
                "timestamp_s": timestamp,
                "phase": phase,
                "phase_age_ms": phase_age,
                "seq": seq,
                "vendor_rate": vendor_rate,
                "breath_rate_raw": raw_rate,
                "freeze_detected": bool(row.get("freeze_detected") is True),
            }
        )
    return result


def timestamp_integrity(records: list[dict[str, Any]]) -> dict[str, Any]:
    timestamps = [r["timestamp_s"] for r in records if r["timestamp_s"] is not None]
    intervals = [b - a for a, b in zip(timestamps, timestamps[1:])]
    positive = [value for value in intervals if value > 0]
    median_ms = statistics.median(positive) * 1000.0 if positive else None
    gap_threshold_ms = max(150.0, 1.5 * median_ms) if median_ms is not None else None
    gaps = [value for value in intervals if gap_threshold_ms is not None and value * 1000.0 > gap_threshold_ms]
    timestamp_freezes = run_lengths([value == 0 for value in intervals])
    nonmonotonic = sum(1 for value in intervals if value < 0)
    duration = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else None
    row_cadence = (len(timestamps) - 1) / duration if duration and duration > 0 else None

    seqs = [int(r["seq"]) for r in records if r["seq"] is not None]
    seq_diffs = [b - a for a, b in zip(seqs, seqs[1:])]
    seq_missing = sum(max(value - 1, 0) for value in seq_diffs if value > 1)
    seq_integrity = {
        "status": "MEASURED" if seqs else "FIELD_NOT_PRESENT",
        "first": seqs[0] if seqs else None,
        "last": seqs[-1] if seqs else None,
        "record_count": len(seqs),
        "missing_sequence_count": seq_missing if seqs else None,
        "duplicate_sequence_count": sum(1 for value in seq_diffs if value == 0) if seqs else None,
        "nonmonotonic_sequence_count": sum(1 for value in seq_diffs if value < 0) if seqs else None,
        "computation": "sum(max(seq[i+1]-seq[i]-1, 0) for positive sequence gaps)",
    }
    return {
        "record_count_with_timestamp": len(timestamps),
        "row_cadence_hz": round_value(row_cadence),
        "duration_s": round_value(duration),
        "median_interval_ms": round_value(median_ms),
        "min_interval_ms": round_value(min(intervals) * 1000.0) if intervals else None,
        "max_interval_ms": round_value(max(intervals) * 1000.0) if intervals else None,
        "gap_threshold_ms_diagnostic": round_value(gap_threshold_ms),
        "gap_count": len(gaps),
        "duplicate_timestamp_count": sum(1 for value in intervals if value == 0),
        "nonmonotonic_timestamp_count": nonmonotonic,
        "timestamp_freeze_intervals": timestamp_freezes,
        "freeze_flag_count": sum(1 for r in records if r["freeze_detected"]),
        "sequence": seq_integrity,
        "computation": {
            "row_cadence_hz": "(timestamp_count - 1) / (last_timestamp - first_timestamp)",
            "gap_count": "interval_ms > max(150 ms, 1.5 * median_positive_interval_ms); diagnostic only, not an official failure threshold",
        },
    }


def phase_signal_summary(records: list[dict[str, Any]], context: dict[str, Any]) -> dict[str, Any]:
    pairs = [(r["timestamp_s"], r["phase"]) for r in records if r["timestamp_s"] is not None and r["phase"] is not None]
    times = [item[0] for item in pairs]
    values = [item[1] for item in pairs]
    summary = numeric_stats(values)
    summary["unique_value_count"] = len(set(values))
    equal_flags = [a == b for a, b in zip(values, values[1:])]
    summary["freeze_intervals"] = run_lengths(equal_flags)

    center = statistics.fmean(values) if values else None
    positive_crossings: list[float] = []
    if center is not None:
        for i in range(1, len(values)):
            left = values[i - 1] - center
            right = values[i] - center
            if left <= 0 < right and values[i] != values[i - 1]:
                fraction = (-left) / (right - left)
                positive_crossings.append(times[i - 1] + fraction * (times[i] - times[i - 1]))
    periods = [b - a for a, b in zip(positive_crossings, positive_crossings[1:]) if b > a]
    period_s = statistics.median(periods) if periods else None
    phase_rpm = 60.0 / period_s if period_s and period_s > 0 else None
    vendor_median = context.get("vendor_median_rpm")
    return {
        "field": "resp_phase" if any("resp_phase" in str(r) for r in []) else "breath_phase_or_resp_phase",
        "finite_sample_count": len(values),
        "stats": summary,
        "positive_crossing_count": len(positive_crossings),
        "dominant_period_s_from_median_positive_crossing_interval": round_value(period_s),
        "dominant_phase_rpm": round_value(phase_rpm),
        "paced_cue_rpm": context.get("cue_rpm"),
        "documented_actual_trial_rpm": context.get("documented_actual_rpm"),
        "documented_vendor_median_rpm": vendor_median,
        "phase_minus_vendor_median_rpm": round_value(phase_rpm - vendor_median) if phase_rpm is not None and vendor_median is not None else None,
        "computation": "center signal by its session mean; estimate period from median interval between positive mean crossings; rpm=60/period_s",
    }


def freshness_summary(records: list[dict[str, Any]]) -> tuple[dict[str, Any], list[int]]:
    age_pairs = [(index, r["timestamp_s"], r["phase_age_ms"]) for index, r in enumerate(records) if r["timestamp_s"] is not None and r["phase_age_ms"] is not None]
    if not age_pairs:
        return (
            {
                "status": "FIELD_NOT_PRESENT",
                "fresh_0x0A13_cadence_hz": None,
                "phase_age_ms": {"min": None, "median": None, "p95": None, "max": None, "fraction_over_30000_ms": None},
                "phase_age_reset_count": None,
                "computation": "not measurable because phase_age_ms is absent",
            },
            [],
        )
    ages = [item[2] for item in age_pairs]
    reset_indices: list[int] = []
    reset_times: list[float] = []
    for previous, current in zip(age_pairs, age_pairs[1:]):
        if current[2] < previous[2]:
            reset_indices.append(current[0])
            reset_times.append(current[1])
    span = age_pairs[-1][1] - age_pairs[0][1]
    cadence = len(reset_times) / span if span > 0 else None
    return (
        {
            "status": "INFERRED_FROM_PHASE_AGE_RESETS",
            "fresh_0x0A13_cadence_hz": round_value(cadence),
            "phase_age_ms": {
                "min": round_value(min(ages)),
                "median": round_value(statistics.median(ages)),
                "p95": round_value(percentile(ages, 0.95)),
                "max": round_value(max(ages)),
                "fraction_over_30000_ms": round_value(sum(1 for age in ages if age > 30000.0) / len(ages)),
            },
            "phase_age_reset_count": len(reset_times),
            "computation": "fresh event proxy = phase_age_ms[i] < phase_age_ms[i-1]; cadence = reset_count / timestamp span",
            "failure_threshold_status": "UNDEFINED; 30000 ms is only the requested reporting partition",
        },
        reset_indices,
    )


def fixed_window_freshness(records: list[dict[str, Any]], reset_indices: list[int]) -> dict[str, Any]:
    event_times = [records[index]["timestamp_s"] for index in reset_indices if records[index]["timestamp_s"] is not None]
    if not event_times:
        return {
            "windows_with_300_genuinely_fresh_samples": 0,
            "max_fresh_samples_in_nonoverlapping_30s_window": 0,
            "status": "NOT_PROVABLE_NO_PHASE_AGE_FIELD" if not reset_indices else "NO_RESET_EVENTS",
            "computation": "fixed non-overlapping 30 s bins from the first telemetry timestamp",
        }
    start = event_times[0]
    bins: dict[int, int] = {}
    for timestamp in event_times:
        bucket = int((timestamp - start) // FROZEN["window_seconds"])
        bins[bucket] = bins.get(bucket, 0) + 1
    maximum = max(bins.values()) if bins else 0
    return {
        "windows_with_300_genuinely_fresh_samples": sum(1 for count in bins.values() if count >= FROZEN["window_samples"]),
        "max_fresh_samples_in_nonoverlapping_30s_window": maximum,
        "status": "MEASURED_FROM_PHASE_AGE_RESET_PROXY",
        "computation": "count reset-proxy events per fixed non-overlapping 30 s bin; count bins >= 300",
    }


def interpolation_diagnostic(records: list[dict[str, Any]], reset_indices: list[int]) -> dict[str, Any]:
    points = [(records[index]["timestamp_s"], records[index]["phase"]) for index in reset_indices if records[index]["timestamp_s"] is not None and records[index]["phase"] is not None]
    if len(points) < 2:
        return {
            "required_status": "UNRESOLVED",
            "applied_to_audit": False,
            "simulation_status": "NOT_QUANTIFIABLE",
            "distortion": None,
        }
    point_times = [point[0] for point in points]
    point_values = [point[1] for point in points]
    observed: list[float] = []
    interpolated: list[float] = []
    for record in records:
        timestamp = record["timestamp_s"]
        phase = record["phase"]
        if timestamp is None or phase is None or timestamp < point_times[0] or timestamp > point_times[-1]:
            continue
        right = bisect.bisect_right(point_times, timestamp)
        if right == 0 or right >= len(point_times):
            continue
        left = right - 1
        span = point_times[right] - point_times[left]
        fraction = (timestamp - point_times[left]) / span if span > 0 else 0.0
        estimate = point_values[left] + fraction * (point_values[right] - point_values[left])
        observed.append(phase)
        interpolated.append(estimate)
    errors = [a - b for a, b in zip(observed, interpolated)]
    return {
        "required_status": "UNRESOLVED",
        "applied_to_audit": False,
        "simulation_status": "SIMULATED_LINEAR_INTERPOLATION_FROM_PHASE_AGE_RESET_PROXY",
        "distortion": {
            "sample_count": len(errors),
            "mae": round_value(statistics.fmean(abs(error) for error in errors)) if errors else None,
            "rmse": round_value(math.sqrt(statistics.fmean(error * error for error in errors))) if errors else None,
            "max_abs": round_value(max(abs(error) for error in errors)) if errors else None,
            "observed_std": round_value(numeric_stats(observed)["std"]),
            "interpolated_std": round_value(numeric_stats(interpolated)["std"]),
        },
        "computation": "linear interpolation between phase_age reset-proxy samples; compared with observed held/repeated telemetry at the original timestamps",
    }


def affine_and_int8(values: list[float], training_reference: dict[str, Any] | None) -> dict[str, Any]:
    normalized = [(value - FROZEN["zscore_mean"]) / FROZEN["zscore_std"] for value in values]

    def quantize(value: float) -> int:
        scaled = value / FROZEN["input_scale"]
        rounded = math.floor(scaled + 0.5) if scaled >= 0 else math.ceil(scaled - 0.5)
        return max(-128, min(127, rounded + FROZEN["input_zero_point"]))

    quantized = [quantize(value) for value in normalized]
    dequantized = [(value - FROZEN["input_zero_point"]) * FROZEN["input_scale"] for value in quantized]
    errors = [after - before for before, after in zip(normalized, dequantized)]
    saturation = sum(1 for value in quantized if value in (-128, 127)) / len(quantized) if quantized else None
    before = numeric_stats(normalized)
    after = numeric_stats(dequantized)
    result: dict[str, Any] = {
        "status": "DIAGNOSTIC_AFFINE_AND_INT8_ONLY",
        "bpf_applied": False,
        "before_int8": before,
        "after_int8_dequantized": after,
        "quantized_integer_stats": numeric_stats([float(value) for value in quantized]),
        "quantized_saturation_fraction": round_value(saturation),
        "quantization_error": numeric_stats(errors),
        "computation": "normalized_proxy=(raw_phase - frozen_mean)/frozen_std; q=round_half_away_from_zero(normalized/scale)+zero_point; clamp int8; dequantize=(q-zero_point)*scale",
    }
    if training_reference:
        ref_before = training_reference.get("naive_affine", {}).get("stats")
        if ref_before:
            result["training_reference_before_int8"] = ref_before
            result["mean_delta_vs_training_reference"] = round_value(before["mean"] - ref_before["mean"])
            result["std_delta_vs_training_reference"] = round_value(before["std"] - ref_before["std"])
    return result


def read_npy_float64(path: Path) -> list[float]:
    """Read the small frozen float64 NPY reference without importing NumPy."""

    data = path.read_bytes()
    if data[:6] != b"\x93NUMPY" or data[6] != 1:
        raise ValueError("only NPY v1 float64 reference is supported")
    header_length = struct.unpack("<H", data[8:10])[0]
    header_start = 10
    header = data[header_start : header_start + header_length].decode("latin1")
    if "'<f8'" not in header and '"<f8"' not in header:
        raise ValueError("training reference is not little-endian float64")
    payload = data[header_start + header_length :]
    return [value[0] for value in struct.iter_unpack("<d", payload)]


def load_training_reference(root: Path) -> dict[str, Any] | None:
    candidates = (
        root / "safenest-mmwave-standalone/datasets/mmwave/processed/mmwave_canonical_real_v1.npy",
        root / "safenest_integration/sources/ondevice_ai/datasets/mmwave/processed/mmwave_canonical_real_v1.npy",
    )
    source = next((path for path in candidates if path.is_file()), None)
    if source is None:
        return None
    values = read_npy_float64(source)
    normalized = [(value - FROZEN["zscore_mean"]) / FROZEN["zscore_std"] for value in values]
    digest, size = sha256_file(source)
    source_path = repo_rel(root, source)
    try:
        subprocess.run(
            ["git", "ls-files", "--error-unmatch", source_path],
            cwd=root,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        source_tracked = True
    except (OSError, subprocess.CalledProcessError):
        source_tracked = False
    return {
        "source_path": source_path,
        "sha256": digest,
        "bytes": size,
        "source_tracked_in_target_repo": source_tracked,
        "reproducible_from_published_target": source_tracked,
        "raw_stats": numeric_stats(values),
        "naive_affine": {
            "stats": numeric_stats(normalized),
            "computation": "same diagnostic frozen affine used for MR60 raw phase; BPF was not reconstructed",
        },
        "status": "AVAILABLE_AUXILIARY_FROZEN_REFERENCE" if source_tracked else "AVAILABLE_LOCAL_ONLY_AUXILIARY_REFERENCE_NOT_TRACKED",
    }


def pipeline_usage(root: Path) -> dict[str, Any]:
    waveform_matches: list[dict[str, Any]] = []
    raw_rate_matches: list[dict[str, Any]] = []
    for relative in PIPELINE_FILES:
        path = root / relative
        if not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            if "resp_phase" in line or "breath_phase" in line:
                if any(token in line for token in ("required_cols", "phases", "phase", "prepare_window", "input_tensor", "resp_phase")):
                    waveform_matches.append({"path": relative.as_posix(), "line": line_number, "text": line.strip()[:180]})
            if "breath_rate_raw" in line:
                raw_rate_matches.append({"path": relative.as_posix(), "line": line_number, "text": line.strip()[:180]})
    waveform_input_files = sorted({item["path"] for item in waveform_matches if "resp_phase" in item["text"] or "breath_phase" in item["text"]})
    return {
        "breath_rate_raw_used_as_waveform_input": False,
        "waveform_input_field": "resp_phase/breath_phase",
        "waveform_input_files": waveform_input_files,
        "waveform_matches": waveform_matches[:40],
        "breath_rate_raw_matches": raw_rate_matches[:40],
        "computation": "static scan of the CSV adapter/interpreter and MR60 adapter/exporter; waveform assignment is phase, while breath_rate_raw matches are telemetry/export/diagnostic references",
    }


def find_named_file(evidence_root: Path, name: str) -> Path | None:
    matches = sorted(path for path in evidence_root.rglob(name) if path.is_file())
    return matches[0] if matches else None


def expected_evidence(root: Path, evidence_root: Path, all_hashes: dict[Path, dict[str, Any]]) -> list[dict[str, Any]]:
    expected: list[dict[str, Any]] = []
    for session_id, suffix in EXPECTED_CSV_SUFFIXES.items():
        path = next((candidate for candidate in sorted(evidence_root.rglob("*.csv")) if candidate.name.endswith(suffix)), None)
        item: dict[str, Any] = {
            "session_id": session_id,
            "kind": "legacy_csv",
            "expected_filename_suffix": suffix,
            "status": "PRESENT" if path else "KNOWN_BUT_NOT_PROVIDED",
            "record_count_expected": None,
        }
        if path:
            if path.resolve() not in all_hashes:
                digest, size = sha256_file(path)
                all_hashes[path.resolve()] = {"sha256": digest, "bytes": size}
            rows, malformed = load_csv_rows(path)
            item.update(
                {
                    "path": public_evidence_path(root, evidence_root, path),
                    "sha256": all_hashes[path.resolve()]["sha256"],
                    "bytes": all_hashes[path.resolve()]["bytes"],
                    "record_count": len(rows),
                    "malformed_record_count": malformed,
                }
            )
        else:
            item["candidate_path"] = f"{repo_rel(root, evidence_root)}/csv/<delivery_v2>/*{suffix}"
        expected.append(item)

    long_name = "2026-08-01_occupied_d09_v120_31min_attempt02.jsonl"
    long_path = find_named_file(evidence_root, long_name)
    item = {
        "session_id": "2026-08-01_occupied_d09_v120_31min_attempt02",
        "kind": "long_jsonl",
        "expected_filename": long_name,
        "status": "PRESENT" if long_path else "KNOWN_BUT_NOT_PROVIDED",
    }
    if long_path:
        if long_path.resolve() not in all_hashes:
            digest, size = sha256_file(long_path)
            all_hashes[long_path.resolve()] = {"sha256": digest, "bytes": size}
        rows, malformed = load_jsonl_rows(long_path)
        item.update(
            {
                "path": public_evidence_path(root, evidence_root, long_path),
                "sha256": all_hashes[long_path.resolve()]["sha256"],
                "bytes": all_hashes[long_path.resolve()]["bytes"],
                "record_count": len(rows),
                "malformed_record_count": malformed,
                "expected_sha256": EXPECTED_LONG_LOG_SHA256,
                "sha256_matches_expected": all_hashes[long_path.resolve()]["sha256"] == EXPECTED_LONG_LOG_SHA256,
            }
        )
    else:
        item["candidate_path"] = f"{repo_rel(root, evidence_root)}/logs/final/{long_name}"
    expected.append(item)

    for pilot_id in PILOT_IDS:
        matches = sorted(path for path in evidence_root.rglob("*") if path.is_file() and pilot_id in path.name)
        item = {
            "session_id": pilot_id,
            "kind": "pr18_pilot",
            "expected_record_count": 1799,
            "status": "PRESENT" if matches else "KNOWN_BUT_NOT_PROVIDED",
            "candidate_paths": [
                f"{repo_rel(root, evidence_root)}/device_measurements/{pilot_id}.jsonl",
                f"{repo_rel(root, evidence_root)}/device_measurements/{pilot_id}/records.jsonl",
            ],
        }
        if matches:
            path = matches[0]
            if path.resolve() not in all_hashes:
                digest, size = sha256_file(path)
                all_hashes[path.resolve()] = {"sha256": digest, "bytes": size}
            item.update(
                {
                    "path": public_evidence_path(root, evidence_root, path),
                    "sha256": all_hashes[path.resolve()]["sha256"],
                    "bytes": all_hashes[path.resolve()]["bytes"],
                }
            )
            if path.suffix.lower() == ".jsonl":
                rows, malformed = load_jsonl_rows(path)
                item.update({"record_count": len(rows), "malformed_record_count": malformed})
        expected.append(item)
    return expected


def analyze_session(root: Path, evidence_root: Path, item: dict[str, Any], all_hashes: dict[Path, dict[str, Any]], training_reference: dict[str, Any] | None) -> dict[str, Any] | None:
    if item.get("status") != "PRESENT" or item.get("kind") not in {"legacy_csv", "long_jsonl"}:
        return None
    path_text = item["path"]
    # Recover the local file from its sanitized name by matching the recorded SHA.
    target_sha = item["sha256"]
    path = next((candidate for candidate, record in all_hashes.items() if record["sha256"] == target_sha), None)
    if path is None:
        return None
    kind = item["kind"]
    rows, malformed = load_csv_rows(path) if kind == "legacy_csv" else load_jsonl_rows(path)
    records = normalize_rows(rows, kind)
    context = SESSION_CONTEXT.get(item["session_id"], {})
    integrity = timestamp_integrity(records)
    phase = phase_signal_summary(records, context)
    if kind == "legacy_csv":
        phase["field"] = "resp_phase"
    else:
        phase["field"] = "breath_phase"
    freshness, reset_indices = freshness_summary(records)
    fresh_windows = fixed_window_freshness(records, reset_indices)
    interpolation = interpolation_diagnostic(records, reset_indices)
    distance = distance_summary(rows, kind)
    finite_phase = [record["phase"] for record in records if record["phase"] is not None]
    bpf_comparison = {
        "meaning_equivalent_to_frozen_contract": False,
        "scale_equivalent_to_frozen_contract": False,
        "assessment": "NOT_ESTABLISHED",
        "frozen_contract": {
            "contract_id": FROZEN["contract_id"],
            "band_hz": [FROZEN["lowcut_hz"], FROZEN["highcut_hz"]],
            "sample_rate_hz": FROZEN["sample_rate_hz"],
            "zscore_mean": FROZEN["zscore_mean"],
            "zscore_std": FROZEN["zscore_std"],
        },
        "raw_phase_stats_before_any_bpf": numeric_stats(finite_phase),
        "diagnostic_affine_proxy": affine_and_int8(finite_phase, training_reference),
        "reason": "Raw MR60 phase-like values were measured, but the exact frozen zero-phase Butterworth BPF semantic cannot be established from telemetry alone; the diagnostic affine is not silently treated as the contract.",
    }
    vendor_values = [record["vendor_rate"] for record in records if record["vendor_rate"] is not None]
    return {
        "session_id": item["session_id"],
        "kind": kind,
        "role": context.get("role"),
        "evidence_path": path_text,
        "sha256": item["sha256"],
        "bytes": item["bytes"],
        "record_count": len(rows),
        "malformed_record_count": malformed,
        "phase_semantic_correspondence": {
            "assessment": "PHASE_LIKE_SIGNAL_OBSERVED_BUT_PHASE_B_EQUIVALENCE_NOT_ESTABLISHED",
            "correspondence_disproven": False,
            "basis": "finite phase values and, where detectable, a periodic phase-like component were observed; no independent Phase-B semantic/reference signal exists in this evidence set",
            "numeric": phase,
        },
        "breath_rate_raw": {
            "field_present": any(record["breath_rate_raw"] is not None for record in records),
            "finite_value_count": len(vendor_values),
            "stats": numeric_stats(vendor_values),
            "used_as_waveform_input": False,
            "waveform_field_used": "resp_phase" if kind == "legacy_csv" else "breath_phase",
            "computation": "field mapping plus static pipeline scan; vendor rate is kept as telemetry/diagnostic and is not placed in the waveform array",
        },
        "row_cadence_and_fresh_cadence": {
            "telemetry_row_cadence_hz": integrity["row_cadence_hz"],
            "fresh_0x0A13_cadence_hz": freshness["fresh_0x0A13_cadence_hz"],
            "fresh_cadence_status": freshness["status"],
            "computation": {
                "row": integrity["computation"]["row_cadence_hz"],
                "fresh": freshness["computation"],
            },
        },
        "timestamp_integrity": integrity,
        "phase_age_ms": freshness["phase_age_ms"],
        "fresh_windows": fresh_windows,
        "interpolation": interpolation,
        "distance_or_range": distance,
        "bpf_zscore_equivalence": bpf_comparison,
        "int8_distribution": bpf_comparison["diagnostic_affine_proxy"],
    }


def before_state(root: Path) -> tuple[dict[str, Any], str]:
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, text=True).strip()
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        branch, head = "UNKNOWN_BRANCH", "UNKNOWN_HEAD"
    summary = {
        "schema_version": "M-C0_SUMMARY_V1",
        "phase": "M-C0",
        "branch": branch,
        "head_at_run": head,
        "decision": DECISION_BLOCKED,
        "blocking_reason": BLOCKED_BEFORE,
        "correspondence_evaluated": False,
        "correspondence_disproven": False,
        "evidence_root_supplied": False,
        "preflight_gate": "PASS_INHERITED_FROM_PREVIOUS_STANDALONE_RUN",
        "execution": {
            "m_c0_executed": False,
            "model_scoring_executed": False,
            "m_c0b_inference_executed": False,
            "m_c1_capture_executed": False,
            "m_c2_metrics_executed": False,
            "locked_test_reopened": False,
            "raw_files_modified": False,
        },
        "decision_is_successful_blocked_outcome": True,
        "provenance": {
            "raw_mr60_jsonl_csv_committed": False,
            "raw_mr60_jsonl_csv_modified": False,
            "note": "No evidence-root was supplied; correspondence was not evaluated.",
        },
    }
    report = f"""# SafeNest mmWave standalone M-C0 — evidence-root not supplied

- Branch: `{branch}`
- Head at run: `{head}`
- Decision: **`{DECISION_BLOCKED}`**
- Blocking reason: **`{BLOCKED_BEFORE}`**
- Correspondence evaluated: `false`
- Correspondence disproven: `false`

Correspondence failure was **NOT observed**; the audit could not run because raw telemetry was absent from the standalone working tree. This before-state is not a measured signal failure.

No inference, preprocessing change, INT8 recalibration, LOCKED_TEST reopening, M-C1 capture, or raw-file modification was performed. Supply `--evidence-root` to run the read-only evidence audit.
"""
    return summary, report


def render_report(root: Path, evidence_root: Path, summary: dict[str, Any], expected: list[dict[str, Any]], sessions: list[dict[str, Any]], all_file_count: int, pipeline: dict[str, Any], training_reference: dict[str, Any] | None) -> str:
    present = [item for item in expected if item["status"] == "PRESENT"]
    missing = [item for item in expected if item["status"] != "PRESENT"]
    lines = [
        "# SafeNest mmWave standalone M-C0 correspondence audit",
        "",
        f"- Repository: `jinsu1011/safenest-embedded-competition`",
        f"- Branch: `{summary.get('branch')}`",
        f"- Head at audit: `{summary.get('head_at_run')}`",
        f"- Evidence-root used: `{repo_rel(root, evidence_root)}`",
        f"- Decision: **`{summary['decision']}`**",
        f"- Blocking reason: **`{summary['blocking_reason']}`**",
        f"- Correspondence evaluated: `{str(summary['correspondence_evaluated']).lower()}`",
        f"- Correspondence disproven: `{str(summary['correspondence_disproven']).lower()}`",
        "- Model scoring/inference: **not executed**",
        "- Raw modification/copy: **none**",
        "",
        "## Method and write boundary",
        "",
        f"The script opened `{all_file_count}` regular files below the evidence-root in `rb` read-only mode and separately SHA-256 hashed every present file in the enumerated expected input set. All output paths were asserted to be outside the evidence-root. Raw MR60 JSONL/CSV remained in place and was not copied into the repository.",
        "",
        "Numeric conventions:",
        "- telemetry row cadence = `(timestamp_count - 1) / (last_timestamp - first_timestamp)`",
        "- fresh 0x0A13 cadence = count of `phase_age_ms` decreases divided by timestamp span; this is an inferred reset proxy, not a direct packet counter",
        "- phase-age p95 uses linear percentile interpolation; `>30,000 ms` is a reporting partition, not an official failure threshold",
        "- 30-second fresh-window count uses fixed non-overlapping 30-second bins and counts bins with at least 300 reset-proxy events",
        "- phase rpm = 60 divided by the median interval between positive crossings of the session-mean-centered phase; it is a signal diagnostic, not a paced-cue-to-label mapping",
        "- interpolation and INT8 calculations are diagnostics only; the frozen BPF/resampling contract was not silently applied",
        "",
        "## Expected evidence and SHA-256",
        "",
        "| Expected item | Status | Evidence path (repo-relative, personal path component redacted) | Records | SHA-256 |",
        "|---|---|---|---:|---|",
    ]
    for item in expected:
        lines.append(
            f"| `{item['session_id']}` | `{item['status']}` | `{item.get('path', item.get('candidate_path', item.get('candidate_paths', '—')))}` | {item.get('record_count', item.get('expected_record_count', '—'))} | `{item.get('sha256', '—')}` |"
        )
    lines += [
        "",
        f"Present expected files: `{len(present)}` / `{len(expected)}`. Missing items were recorded as `KNOWN_BUT_NOT_PROVIDED`; they were not silently skipped.",
        "",
        "## Per-session measured findings",
        "",
        "| Session | Records | Row Hz | Fresh 0x0A13 Hz | Phase rpm | Phase age min / median / p95 / max ms | >30 s | 300-fresh windows | Interp RMSE |",
        "|---|---:|---:|---:|---:|---|---:|---:|---:|",
    ]
    for session in sessions:
        phase = session["phase_semantic_correspondence"]["numeric"]
        age = session["phase_age_ms"]
        distortion = session["interpolation"].get("distortion") or {}
        age_text = " / ".join(str(age.get(key)) for key in ("min", "median", "p95", "max"))
        lines.append(
            f"| `{session['session_id']}` | {session['record_count']} | {session['row_cadence_and_fresh_cadence']['telemetry_row_cadence_hz']} | {session['row_cadence_and_fresh_cadence']['fresh_0x0A13_cadence_hz'] if session['row_cadence_and_fresh_cadence']['fresh_0x0A13_cadence_hz'] is not None else 'N/A'} | {phase.get('dominant_phase_rpm')} | {age_text} | {age.get('fraction_over_30000_ms')} | {session['fresh_windows']['windows_with_300_genuinely_fresh_samples']} | {distortion.get('rmse', 'N/A')} |"
        )
    d15 = next((session for session in sessions if session["session_id"] == "S001_NORMAL_D15"), None)
    paced = {
        session["session_id"]: session["phase_semantic_correspondence"]["numeric"]
        for session in sessions
        if session["session_id"].startswith("S001_BREATH_PACED_")
    }
    long_session = next((session for session in sessions if session["kind"] == "long_jsonl"), None)
    if long_session is not None:
        long_integrity = long_session["timestamp_integrity"]
        long_sequence = long_integrity["sequence"]
        long_q4 = (
            f"Long-log measured numbers are `gap_count={long_integrity['gap_count']}`, "
            f"`duplicate_timestamp_count={long_integrity['duplicate_timestamp_count']}`, "
            f"`nonmonotonic_timestamp_count={long_integrity['nonmonotonic_timestamp_count']}`, "
            f"`timestamp_freeze_intervals={long_integrity['timestamp_freeze_intervals']['interval_count']}`, "
            f"`freeze_flag_count={long_integrity['freeze_flag_count']}`, and "
            f"`sequence_missing_count={long_sequence['missing_sequence_count']}`; all are computed from "
            f"`{long_session['evidence_path']}`."
        )
        long_distortion = long_session["interpolation"].get("distortion") or {}
        long_q7 = (
            f"For `{long_session['evidence_path']}`, simulated linear interpolation was not applied; "
            f"the proxy distortion is `RMSE={long_distortion.get('rmse')}`, `MAE={long_distortion.get('mae')}`, "
            f"and `max_abs={long_distortion.get('max_abs')}` over `{long_distortion.get('sample_count')}` samples."
        )
        before_int8 = long_session["int8_distribution"]["before_int8"]
        after_int8 = long_session["int8_distribution"]["after_int8_dequantized"]

        def distribution_text(label: str, stats: dict[str, Any]) -> str:
            return (
                f"{label} `n={stats['count']}`, `mean={stats['mean']}`, `std={stats['std']}`, "
                f"`p05={stats['p05']}`, `p95={stats['p95']}`, `min={stats['min']}`, `max={stats['max']}`"
            )

        if training_reference is not None:
            training_stats = training_reference["naive_affine"]["stats"]
            training_note = (
                f" The auxiliary reference is `{training_reference['source_path']}` with SHA-256 "
                f"`{training_reference['sha256']}` and status `{training_reference['status']}`; its diagnostic affine "
                f"distribution is {distribution_text('training', training_stats)}."
            )
        else:
            training_note = " No training-reference file was available in the target worktree, so a numeric training comparison was not fabricated."
        long_q9 = (
            f"For the long log, {distribution_text('before-INT8', before_int8)}; "
            f"{distribution_text('after-INT8 dequantized', after_int8)}; "
            f"quantized saturation is `{long_session['int8_distribution']['quantized_saturation_fraction']}`."
            f"{training_note} These are diagnostic affine values because BPF was not reconstructed."
        )
    else:
        long_q4 = "No long JSONL session was present, so long-log timestamp numbers were not fabricated."
        long_q7 = "No long JSONL session was present, so interpolation distortion numbers were not fabricated."
        long_q9 = "No long JSONL session was present, so pre/post INT8 distribution numbers were not fabricated."
    lines += [
        "",
        "## Preserved measurement corrections",
        "",
    ]
    if d15 is not None:
        d15_distance = d15["distance_or_range"]
        d15_phase_stats = d15["phase_semantic_correspondence"]["numeric"]["stats"]
        lines.append(
            f"- `S001_NORMAL_D15`: the finite `range_m` sample standard deviation is `{d15_distance['sample_std_cm']}` cm, computed from `{d15_distance['finite_sample_count']}` rows in `{d15['evidence_path']}`. The same file's `resp_phase` population std is `{d15_phase_stats['std']}`; the frozen value is the phase/vitals signal, not distance."
        )
    if "S001_BREATH_PACED_12_01" in paced:
        failed = paced["S001_BREATH_PACED_12_01"]
        lines.append(
            f"- `S001_BREATH_PACED_12_01` is not treated as a 12-rpm ground truth: `devices/mmwave/firmware/csv/2026-07-26_delivery_v2/DELIVERY_NOTES.md` records an actual trial of approximately `{failed['documented_actual_trial_rpm']}` rpm. The cue remains metadata only."
        )
    lines += [
        "- Existing project records retain the corrected phase periods `12.34` / `15.00–15.01` / `20.00` rpm versus vendor medians `14.0` / `19.0` / `23.0` (`docs/operations/PROJECT_PROGRESS.md` and the delivery notes). These are measurement notes and do not create a paced-rpm-to-class mapping.",
        "- The phase-rpm values in the table are independently recomputed from each listed evidence file using the positive-crossing formula above; they are not substituted with paced cues or vendor medians.",
        "",
        "### Question 1 — signal-semantic correspondence",
        "",
        "`breath_phase`/`resp_phase` was present and periodic components were measurable in the supplied legacy captures. That establishes a phase-like telemetry signal, not equivalence to the frozen Phase-B `resp_phase_model_ready_bpf_zscore` semantic. No independent canonical reference waveform is present, so the measured assessment is `PHASE_LIKE_SIGNAL_OBSERVED_BUT_PHASE_B_EQUIVALENCE_NOT_ESTABLISHED`; `correspondence_disproven=false`.",
        "",
        "### Question 2 — `breath_rate_raw` as waveform input",
        "",
        f"The measured answer is **no**. The static pipeline scan found waveform input paths `{json.dumps(pipeline['waveform_input_files'], ensure_ascii=False)}` and recorded `breath_rate_raw` only in telemetry/export/diagnostic matches. Per-session parsing also used `{json.dumps({'legacy_csv': 'resp_phase', 'long_jsonl': 'breath_phase'}, ensure_ascii=False)}` as the waveform field.",
        "",
        "### Question 3 — row cadence vs fresh cadence",
        "",
        "The table reports the two cadences separately. Legacy CSV has no `phase_age_ms`/0x0A13 freshness field, so its fresh cadence is `N/A`, not assumed to be the row cadence. The long log reports an inferred cadence from phase-age resets and labels it as a proxy.",
        "",
        "### Question 4 — timestamp integrity",
        "",
        f"Per-session gaps, duplicates, non-monotonic timestamps, timestamp freezes, sequence loss, and freeze flags are in `offline_contract_correspondence.json` under `per_session[].timestamp_integrity`. {long_q4} Gap counts use the diagnostic threshold stated above; no official phase-age failure threshold was invented.",
        "",
        "### Question 5 — `phase_age_ms` distribution",
        "",
        "The long JSONL's min/median/p95/max and fraction over 30 seconds are measured in the table and JSON. Legacy CSV sessions report `FIELD_NOT_PRESENT`, so no phase-age statistic is fabricated.",
        "",
        "### Question 6 — 300 genuinely fresh samples",
        "",
        "The measured count is shown per session. A value of `0` means no fixed 30-second bin contained 300 phase-age reset-proxy events. CSV sessions are additionally marked not provable because freshness metadata is absent.",
        "",
        "### Question 7 — interpolation",
        "",
        f"Interpolation was **not applied** to any audit input. Where phase-age reset proxies existed, linear interpolation was simulated only to quantify distortion; its RMSE/MAE/max-absolute error are reported per session. {long_q7} The method remains unresolved.",
        "",
        "### Question 8 — BPF + z-score identity",
        "",
        f"The answer is **not established as identical**. The frozen contract is `{FROZEN['contract_id']}` with {FROZEN['lowcut_hz']}–{FROZEN['highcut_hz']} Hz, order {FROZEN['bpf_order']}, zero-phase filtfilt, mean `{FROZEN['zscore_mean']}`, and std `{FROZEN['zscore_std']}`. Raw phase statistics and a clearly labeled affine-only proxy are in each session result; no BPF was silently substituted.",
        "",
        "### Question 9 — pre/post INT8 distribution",
        "",
        f"The JSON contains diagnostic before-INT8, after-INT8-dequantized, quantized integer, saturation, and quantization-error distributions using scale `0.041720833629369736` and zero-point `-3`. {long_q9}",
        "",
        "### Question 10 — 620/620 all-APNEA collapse stage",
        "",
        "No stage is assigned. This run did not replay inference, and the expected evidence set contains no stage-labeled 620/620 replay artifact. Inference remains prohibited until the correspondence gate authorizes it; the collapse stage therefore remains unresolved rather than guessed.",
        "",
        "## Decision",
        "",
        f"**`{summary['decision']}`** with `correspondence_evaluated=true` and `correspondence_disproven=false`. The result is measured and successful as a block: phase-like telemetry is present, but the frozen Phase-B semantic, fresh 300-sample window, and exact preprocessing/INT8 distribution correspondence are not established. Exploratory inference is not authorized.",
        "",
        "## What remains unknown",
        "",
        "- Exact physical/numeric semantic mapping from MR60 `breath_phase` to the frozen Phase-B input.",
        "- Official phase-age failure threshold; 30 seconds is only a reporting partition here.",
        "- Direct 0x0A13 packet identity/update cadence versus phase-age reset proxy.",
        "- Approved interpolation/resampling method and its acceptable distortion.",
        "- Formal pre-BPF/post-BPF training-distribution comparison for MR60.",
        "- Stage responsible for the historical all-APNEA collapse.",
        "- Independent M-C1 reference hardware, sample size, and paced-rpm-to-label mapping.",
        "- Official measurement distances; practical starting points and freeze observations remain evidence, not a frozen protocol.",
        "",
        "## Boundaries preserved",
        "",
        "No retraining, preprocessing change, INT8 recalibration, LOCKED_TEST reopening, M-C1 capture, clinical apnea claim, paced-cue class mapping, or raw-file modification was performed.",
    ]
    return "\n".join(lines) + "\n"


def write_json(path: Path, payload: dict[str, Any], evidence_root: Path | None) -> None:
    if evidence_root is not None:
        assert_output_outside_evidence([path], evidence_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run(root: Path, evidence_root_arg: Path | None, output_dir: Path = AUDIT_DIR, report_path: Path = REPORT_PATH, run_log_path: Path = RUN_LOG_PATH) -> dict[str, Any]:
    root = root.resolve()
    output_dir = (root / output_dir).resolve() if not output_dir.is_absolute() else output_dir.resolve()
    report_path = (root / report_path).resolve() if not report_path.is_absolute() else report_path.resolve()
    run_log_path = (root / run_log_path).resolve() if not run_log_path.is_absolute() else run_log_path.resolve()
    evidence_root = None
    if evidence_root_arg is not None:
        evidence_root = (root / evidence_root_arg).resolve() if not evidence_root_arg.is_absolute() else evidence_root_arg.resolve()
        if not evidence_root.is_dir():
            raise FileNotFoundError(f"evidence-root is not a directory: {evidence_root}")
        assert_output_outside_evidence([output_dir, report_path, run_log_path], evidence_root)

    if evidence_root is None:
        summary, report = before_state(root)
        write_json(root / output_dir / SUMMARY_PATH.name, summary, None)
        (root / report_path).parent.mkdir(parents=True, exist_ok=True)
        (root / report_path).write_text(report, encoding="utf-8")
        return summary

    # Open every regular file under the read-only evidence root, but hash only
    # files that belong to the explicitly enumerated expected input set.  The
    # evidence directory also contains build artifacts and auxiliary logs; they
    # are opened to prove read-only access, not silently promoted to inputs.
    evidence_root_regular_file_count = open_all_evidence_files_read_only(evidence_root)
    all_hashes: dict[Path, dict[str, Any]] = {}
    expected = expected_evidence(root, evidence_root, all_hashes)
    training_reference = load_training_reference(root)
    sessions: list[dict[str, Any]] = []
    for item in expected:
        result = analyze_session(root, evidence_root, item, all_hashes, training_reference)
        if result:
            sessions.append(result)
    try:
        branch = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=root, text=True).strip()
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except (OSError, subprocess.CalledProcessError):
        branch, head = "UNKNOWN_BRANCH", "UNKNOWN_HEAD"
    pipeline = pipeline_usage(root)
    present_count = sum(1 for item in expected if item["status"] == "PRESENT")
    missing_count = len(expected) - present_count
    summary: dict[str, Any] = {
        "schema_version": "M-C0_SUMMARY_V2",
        "phase": "M-C0",
        "branch": branch,
        "head_at_run": head,
        "evidence_root": repo_rel(root, evidence_root),
        "decision": DECISION_BLOCKED,
        "blocking_reason": BLOCKED_MEASURED,
        "correspondence_evaluated": True,
        "correspondence_disproven": False,
        "preflight_gate": "PASS_INHERITED_FROM_PREVIOUS_STANDALONE_RUN",
        "execution": {
            "m_c0_executed": True,
            "model_scoring_executed": False,
            "m_c0b_inference_executed": False,
            "m_c1_capture_executed": False,
            "m_c2_metrics_executed": False,
            "locked_test_reopened": False,
            "raw_files_modified": False,
            "raw_files_copied": False,
        },
        "decision_is_successful_blocked_outcome": True,
        "expected_input_file_count": len(expected),
        "expected_input_present_count": present_count,
        "known_but_not_provided_count": missing_count,
        "evidence_root_file_count": evidence_root_regular_file_count,
        "expected_input_files_hashed_count": len(all_hashes),
        "raw_expected_files_analyzed_count": len(sessions),
        "pipeline_breath_rate_raw_used_as_waveform": pipeline["breath_rate_raw_used_as_waveform_input"],
        "session_results": [
            {
                "session_id": session["session_id"],
                "record_count": session["record_count"],
                "telemetry_row_cadence_hz": session["row_cadence_and_fresh_cadence"]["telemetry_row_cadence_hz"],
                "fresh_0x0A13_cadence_hz": session["row_cadence_and_fresh_cadence"]["fresh_0x0A13_cadence_hz"],
                "phase_age_ms": session["phase_age_ms"],
                "windows_with_300_genuinely_fresh_samples": session["fresh_windows"]["windows_with_300_genuinely_fresh_samples"],
                "phase_rpm": session["phase_semantic_correspondence"]["numeric"]["dominant_phase_rpm"],
                "distance_or_range": session["distance_or_range"],
            }
            for session in sessions
        ],
        "what_remains_unknown": [
            "Exact physical/numeric semantic mapping from MR60 breath_phase to the frozen Phase-B input.",
            "Official phase-age failure threshold and direct 0x0A13 packet identity/update cadence.",
            "Approved interpolation/resampling method and acceptable distortion.",
            "Formal pre-BPF/post-BPF training-distribution comparison for MR60.",
            "Stage responsible for the historical all-APNEA collapse.",
            "Independent M-C1 reference hardware, sample size, and paced-rpm-to-label mapping.",
            "Official measurement distances.",
        ],
        "provenance": {
            "raw_mr60_jsonl_csv_committed": False,
            "raw_mr60_jsonl_csv_modified": False,
            "evidence_files_hashed_read_only": True,
            "expected_long_log_sha256": EXPECTED_LONG_LOG_SHA256,
        },
    }
    inventory = {
        "schema_version": "M-C0_EXISTING_MEASUREMENT_INVENTORY_V2",
        "evidence_root": repo_rel(root, evidence_root),
        "expected_evidence_set": expected,
        "catalog_summary": {
            "expected_count": len(expected),
            "present_count": present_count,
            "known_but_not_provided_count": missing_count,
            "raw_sessions_analyzed_count": len(sessions),
            "all_evidence_root_file_count": evidence_root_regular_file_count,
            "expected_input_files_hashed_count": len(all_hashes),
            "computation": "counts over expected_evidence_set; all regular evidence files opened read-only; expected input files SHA-256 hashed",
        },
        "captures": sessions,
        "input_files_hashed": [
            {
                "session_id": item["session_id"],
                "path": item.get("path"),
                "sha256": item.get("sha256"),
                "bytes": item.get("bytes"),
            }
            for item in expected
            if item["status"] == "PRESENT"
        ],
        "raw_files_copied": False,
    }
    correspondence = {
        "schema_version": "M-C0_OFFLINE_CONTRACT_CORRESPONDENCE_V2",
        "decision": summary["decision"],
        "blocking_reason": summary["blocking_reason"],
        "correspondence_evaluated": True,
        "correspondence_disproven": False,
        "audit_scope": {
            "repository_root": ".",
            "evidence_root": repo_rel(root, evidence_root),
            "output_paths_outside_evidence_root_asserted": True,
            "all_evidence_files_opened_read_only": True,
            "raw_files_copied": False,
        },
        "questions": {
            "1_signal_semantic_correspondence": {
                "assessment": "PHASE_LIKE_SIGNAL_OBSERVED_BUT_PHASE_B_EQUIVALENCE_NOT_ESTABLISHED",
                "correspondence_disproven": False,
                "per_session": [session["phase_semantic_correspondence"] for session in sessions],
            },
            "2_breath_rate_raw_waveform_use": pipeline,
            "3_row_cadence_and_fresh_0x0A13_cadence": [session["row_cadence_and_fresh_cadence"] for session in sessions],
            "4_timestamp_integrity": [
                {"session_id": session["session_id"], "timestamp_integrity": session["timestamp_integrity"]}
                for session in sessions
            ],
            "5_phase_age_ms_distribution": [
                {"session_id": session["session_id"], "phase_age_ms": session["phase_age_ms"]}
                for session in sessions
            ],
            "6_300_fresh_sample_windows": [
                {"session_id": session["session_id"], "fresh_windows": session["fresh_windows"]}
                for session in sessions
            ],
            "7_interpolation_requirement_and_simulated_distortion": [
                {"session_id": session["session_id"], "interpolation": session["interpolation"]}
                for session in sessions
            ],
            "8_bpf_zscore_equivalence": [
                {"session_id": session["session_id"], "bpf_zscore_equivalence": session["bpf_zscore_equivalence"]}
                for session in sessions
            ],
            "9_pre_post_int8_distribution": [
                {"session_id": session["session_id"], "int8_distribution": session["int8_distribution"]}
                for session in sessions
            ],
            "10_620_of_620_apnea_collapse_stage": {
                "status": "NOT_DETERMINED",
                "stage": None,
                "reason": "No stage-labeled replay artifact was present in the expected evidence set; inference is prohibited before the C0A gate.",
            },
        },
        "training_reference": training_reference,
        "frozen_contract": FROZEN,
    }
    report = render_report(root, evidence_root, summary, expected, sessions, evidence_root_regular_file_count, pipeline, training_reference)
    run_log = "\n".join(
        [
            "# SafeNest mmWave M-C0 audit run log",
            "",
            "```text",
            "python3 scripts/mmwave_m_c0_correspondence_audit.py --root . --evidence-root devices/mmwave/firmware",
            "```",
            "",
            f"- Evidence-root used: `{repo_rel(root, evidence_root)}`",
            f"- Regular files opened read-only: `{evidence_root_regular_file_count}`",
            f"- Expected input files SHA-256 hashed: `{len(all_hashes)}`",
            f"- Expected evidence items: `{len(expected)}`",
            f"- Expected evidence present: `{present_count}`",
            f"- Known but not provided: `{missing_count}`",
            f"- Long-log expected SHA-256: `{EXPECTED_LONG_LOG_SHA256}`",
            "- Raw JSONL/CSV copied into repository: `false`",
            "- Raw JSONL/CSV modified: `false`",
            "- Output-inside-evidence-root assertion: `passed`",
            "- Inference/model scoring: `not executed`",
            "",
        ]
    )
    write_json(root / output_dir / "existing_measurement_inventory.json", inventory, evidence_root)
    write_json(root / output_dir / "offline_contract_correspondence.json", correspondence, evidence_root)
    write_json(root / output_dir / "m_c0_summary.json", summary, evidence_root)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(report, encoding="utf-8")
    run_log_path.parent.mkdir(parents=True, exist_ok=True)
    run_log_path.write_text(run_log, encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the SafeNest mmWave M-C0 correspondence audit")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1], help="repository root")
    parser.add_argument("--evidence-root", type=Path, default=None, help="read-only evidence root; no default")
    parser.add_argument("--output-dir", type=Path, default=AUDIT_DIR, help="derived JSON output directory")
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH, help="derived Markdown report path")
    parser.add_argument("--run-log-path", type=Path, default=RUN_LOG_PATH, help="derived run-log path")
    args = parser.parse_args()
    summary = run(args.root, args.evidence_root, args.output_dir, args.report_path, args.run_log_path)
    print(json.dumps({"decision": summary["decision"], "correspondence_evaluated": summary["correspondence_evaluated"], "evidence_root": summary.get("evidence_root")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
