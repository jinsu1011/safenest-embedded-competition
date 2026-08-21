"""Benchmark the locked Thermal B5 candidate on saved Pi Thermal NPZ frames.

This is a candidate/HIL utility, not a production entry point.  It records
the execution host, per-frame latency, saturation, validity, and model
identity to JSON/CSV.  Saved-frame execution must not be reported as live
sensor latency or end-to-end FPS.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from importlib import metadata as importlib_metadata
import json
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any

import numpy as np

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from ai.thermal_b5_candidate import (
    B5_SHA256,
    P1_PROFILE_ID,
    VERIFIED_ORIENTATION_ID,
    VERIFIED_PHYSICAL_UNIT_ID,
    ThermalB5CandidateModel,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the non-production Thermal T-B5 candidate on saved Runtime NPZ frames."
    )
    parser.add_argument(
        "--input-npz",
        action="append",
        required=True,
        help="Runtime Thermal NPZ containing frames/timestamps/frame_sequences; repeatable.",
    )
    parser.add_argument("--output-json", required=True)
    parser.add_argument("--output-csv", required=True)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument(
        "--orientation-contract",
        default=None,
        help=(
            "Must equal the reviewed contract identity "
            f"{VERIFIED_ORIENTATION_ID!r}. Do not guess this value."
        ),
    )
    parser.add_argument(
        "--physical-unit-contract",
        default=None,
        help=(
            "Must equal the reviewed contract identity "
            f"{VERIFIED_PHYSICAL_UNIT_ID!r}. Do not guess this value."
        ),
    )
    return parser.parse_args()


def load_frames(paths: list[Path]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in paths:
        with np.load(path, allow_pickle=False) as payload:
            required = {"frames", "timestamps", "frame_sequences"}
            missing = required - set(payload.files)
            if missing:
                raise ValueError(f"{path}: missing NPZ keys {sorted(missing)}")
            frames = payload["frames"]
            timestamps = payload["timestamps"]
            sequences = payload["frame_sequences"]
            if frames.dtype != np.uint16 or frames.ndim != 3 or frames.shape[1:] != (62, 80):
                raise ValueError(f"{path}: frames must be uint16 (N,62,80), got {frames.dtype} {frames.shape}")
            if timestamps.ndim != 1 or not np.issubdtype(timestamps.dtype, np.number):
                raise ValueError(f"{path}: timestamps must be a numeric vector")
            if not np.all(np.isfinite(timestamps)) or np.any(timestamps < 0):
                raise ValueError(f"{path}: timestamps must be finite and non-negative")
            if sequences.ndim != 1 or not np.issubdtype(sequences.dtype, np.integer):
                raise ValueError(f"{path}: frame_sequences must be an integer vector")
            if np.any(sequences < 0) or np.any(sequences > 0xFFFFFFFF):
                raise ValueError(f"{path}: frame_sequences must fit uint32")
            if len(timestamps) != len(frames) or len(sequences) != len(frames):
                raise ValueError(f"{path}: NPZ arrays have inconsistent lengths")
            for index, frame in enumerate(frames):
                rows.append(
                    {
                        "source_file": path.as_posix(),
                        "frame_index": index,
                        "timestamp": float(timestamps[index]),
                        "frame_sequence": int(sequences[index]),
                        "frame": np.array(frame, copy=True),
                    }
                )
    if not rows:
        raise ValueError("no Thermal frames were loaded")
    return rows


def benchmark(args: argparse.Namespace) -> dict[str, Any]:
    if args.warmup < 0 or args.repeat < 1:
        raise ValueError("--warmup must be non-negative and --repeat must be positive")
    if args.orientation_contract != VERIFIED_ORIENTATION_ID:
        raise ValueError(
            f"--orientation-contract must equal {VERIFIED_ORIENTATION_ID!r} after review"
        )
    if args.physical_unit_contract != VERIFIED_PHYSICAL_UNIT_ID:
        raise ValueError(
            f"--physical-unit-contract must equal {VERIFIED_PHYSICAL_UNIT_ID!r} after review"
        )
    frames = load_frames([Path(value).resolve() for value in args.input_npz])
    model = ThermalB5CandidateModel(
        orientation_contract=args.orientation_contract,
        physical_unit_contract=args.physical_unit_contract,
    )
    for _ in range(args.warmup):
        model.predict(frames[0]["frame"])

    resource_before = resource_snapshot()
    wall_started = time.perf_counter()
    cpu_started = time.process_time()
    records: list[dict[str, Any]] = []
    for repetition in range(args.repeat):
        for item in frames:
            base = {
                "source_file": item["source_file"],
                "frame_index": item["frame_index"],
                "frame_sequence": item["frame_sequence"],
                "source_timestamp": item["timestamp"],
                "repetition": repetition,
            }
            try:
                prediction = model.predict(item["frame"])
                records.append(
                    {
                        **base,
                        "valid": True,
                        "error": None,
                        "class_name": prediction.class_name,
                        "confidence": prediction.confidence,
                        "latency_ms": prediction.latency_ms,
                        "low_saturation_ratio": prediction.metadata[
                            "input_low_saturation_ratio"
                        ],
                        "high_saturation_ratio": prediction.metadata[
                            "input_high_saturation_ratio"
                        ],
                    }
                )
            except Exception as error:
                records.append(
                    {
                        **base,
                        "valid": False,
                        "error": f"{type(error).__name__}: {error}",
                        "class_name": None,
                        "confidence": None,
                        "latency_ms": None,
                        "low_saturation_ratio": None,
                        "high_saturation_ratio": None,
                    }
                )

    cpu_seconds = time.process_time() - cpu_started
    wall_seconds = time.perf_counter() - wall_started
    resource_after = resource_snapshot()
    valid = [row for row in records if row["valid"]]
    latencies = np.asarray([row["latency_ms"] for row in valid], dtype=np.float64)
    low_saturation = np.asarray(
        [row["low_saturation_ratio"] for row in valid], dtype=np.float64
    )
    high_saturation = np.asarray(
        [row["high_saturation_ratio"] for row in valid], dtype=np.float64
    )
    return {
        "schema_version": "1.0",
        "status": "BENCHMARK_EXECUTED_OFFLINE_SAVED_FRAMES",
        "production_selected": False,
        "live_sensor_execution": False,
        "end_to_end_latency_measured": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "model": {
            "sha256": B5_SHA256,
            "preprocessing_identity": P1_PROFILE_ID,
            "orientation_identity": args.orientation_contract,
            "physical_unit_identity": args.physical_unit_contract,
        },
        "host": host_snapshot(model),
        "input_file_count": len(args.input_npz),
        "source_frame_count": len(frames),
        "warmup_count": args.warmup,
        "repeat_count": args.repeat,
        "measurement_count": len(records),
        "valid_count": len(valid),
        "invalid_count": len(records) - len(valid),
        "invalid_rate": (len(records) - len(valid)) / len(records),
        "transport_drop_rate": None,
        "resource_measurement": {
            "before": resource_before,
            "after": resource_after,
            "wall_seconds": wall_seconds,
            "process_cpu_seconds": cpu_seconds,
            "process_cpu_percent_of_one_core": (
                100.0 * cpu_seconds / wall_seconds if wall_seconds > 0 else None
            ),
        },
        "latency_ms": (
            {
                "p50": float(np.percentile(latencies, 50)),
                "p95": float(np.percentile(latencies, 95)),
                "p99": float(np.percentile(latencies, 99)),
                "mean": float(latencies.mean()),
                "inference_only_fps_from_mean": float(1000.0 / latencies.mean()),
            }
            if len(latencies)
            else None
        ),
        "input_low_saturation_ratio": (
            {
                "median": float(np.percentile(low_saturation, 50)),
                "p95": float(np.percentile(low_saturation, 95)),
                "maximum": float(low_saturation.max()),
            }
            if len(low_saturation)
            else None
        ),
        "input_high_saturation_ratio": (
            {
                "median": float(np.percentile(high_saturation, 50)),
                "p95": float(np.percentile(high_saturation, 95)),
                "maximum": float(high_saturation.max()),
            }
            if len(high_saturation)
            else None
        ),
        "records": records,
        "limitations": [
            "Saved-frame benchmark; not live sensor transport latency or acquisition FPS.",
            "Process CPU is measured; system-wide CPU, drop rate, soak, and reboot recovery require live HIL.",
            "HUMAN_FALL is a LYING-derived posture proxy, not a temporal fall event.",
        ],
    }


def host_snapshot(model: ThermalB5CandidateModel) -> dict[str, Any]:
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "system": platform.system(),
        "kernel_release": platform.release(),
        "kernel_version": platform.version(),
        "python": sys.version,
        "cpu_count": os.cpu_count(),
        "cpu_model": cpu_model(),
        "interpreter_type": type(model.interpreter).__name__,
        "interpreter_package_versions": package_versions(),
        "process_rss_kb": process_rss_kb(),
        "process_peak_rss_kb": process_peak_rss_kb(),
        "soc_temperature_c": soc_temperature_c(),
    }


def resource_snapshot() -> dict[str, float | int | None]:
    return {
        "process_rss_kb": process_rss_kb(),
        "process_peak_rss_kb": process_peak_rss_kb(),
        "soc_temperature_c": soc_temperature_c(),
    }


def process_rss_kb() -> int | None:
    status = Path("/proc/self/status")
    if not status.is_file():
        return None
    for line in status.read_text(encoding="utf-8").splitlines():
        if line.startswith("VmRSS:"):
            return int(line.split()[1])
    return None


def process_peak_rss_kb() -> int | None:
    try:
        import resource
    except ImportError:
        return None
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def cpu_model() -> str | None:
    path = Path("/proc/cpuinfo")
    if not path.is_file():
        return platform.processor() or None
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.lower().startswith("model name") or line.lower().startswith("model"):
            return line.split(":", 1)[-1].strip() or None
    return None


def package_versions() -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for distribution in ("ai-edge-litert", "tflite-runtime", "tensorflow"):
        try:
            result[distribution] = importlib_metadata.version(distribution)
        except importlib_metadata.PackageNotFoundError:
            result[distribution] = None
    return result


def soc_temperature_c() -> float | None:
    path = Path("/sys/class/thermal/thermal_zone0/temp")
    if not path.is_file():
        return None
    return float(path.read_text(encoding="utf-8").strip()) / 1000.0


def write_outputs(result: dict[str, Any], json_path: Path, csv_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    fieldnames = [
        "source_file",
        "frame_index",
        "frame_sequence",
        "source_timestamp",
        "repetition",
        "valid",
        "error",
        "class_name",
        "confidence",
        "latency_ms",
        "low_saturation_ratio",
        "high_saturation_ratio",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(result["records"])


def main() -> int:
    args = parse_args()
    result = benchmark(args)
    write_outputs(result, Path(args.output_json), Path(args.output_csv))
    print(json.dumps({key: result[key] for key in (
        "status", "measurement_count", "valid_count", "invalid_count", "latency_ms"
    )}, ensure_ascii=False, indent=2))
    return 0 if result["invalid_count"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
