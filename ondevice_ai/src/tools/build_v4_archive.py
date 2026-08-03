#!/usr/bin/env python3
"""Build a compact, reproducible SafeNest v4 source/model delivery archive."""

from __future__ import annotations

import hashlib
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / "output" / "SafeNest_v4.0_commercialization_package.zip"
CORE_INCLUDES = (
    "README.md", "ondevice_ai/README.md", "ondevice_ai/docs/walkthrough.md",
    "ondevice_ai/requirements-mac.txt", "ondevice_ai/requirements-pi.txt",
    "ondevice_ai/src/inference/__init__.py", "ondevice_ai/src/inference/thermal_interpreter.py",
    "ondevice_ai/src/inference/infer_pi_thermal.py", "ondevice_ai/src/inference/co2_interpreter.py",
    "ondevice_ai/src/inference/mmwave_interpreter.py", "ondevice_ai/src/inference/model_registry.py",
    "ondevice_ai/src/risk/__init__.py", "ondevice_ai/src/risk/risk_rules.py",
    "ondevice_ai/src/risk/risk_engine.py", "ondevice_ai/config/risk_engine.json",
    "ondevice_ai/src/integrated_node/run_demo.py", "ondevice_ai/src/integrated_node/virtual_sensor_streamer.py",
    "ondevice_ai/src/integrated_node/safenest_integrated_plotter.py",
    "ondevice_ai/src/integrated_node/safenest_risk_engine.py", "shared/contracts/base_sensor.py",
    "ondevice_ai/models/model_manifest.json", "ondevice_ai/models/thermal/thermal_fall_int8_v0.1.0.tflite",
    "ondevice_ai/models/co2/co2_occupancy_int8_v0.1.0.tflite",
    "ondevice_ai/models/co2/co2_scaling_metadata_v0.1.0.json",
    "ondevice_ai/models/mmwave/mmwave_resp_int8_v0.1.0.tflite",
    "ondevice_ai/models/mmwave/sensor_stats_metadata_v0.1.0.json",
    "ondevice_ai/models/mmwave/source_sensor_stats_metadata_20260713.json",
    "ondevice_ai/benchmarks/benchmark_thermal.py", "ondevice_ai/src/tools/build_v4_archive.py",
    "ondevice_ai/src/tools/test_thermal_tflite.py", "ondevice_ai/src/training/thermal_prep.py",
    "ondevice_ai/src/training/thermal_train.py",
)


def archive_inputs() -> tuple[str, ...]:
    tests = tuple(
        path.relative_to(ROOT).as_posix()
        for test_root in (ROOT / "ondevice_ai/tests", ROOT / "devices/mmwave/tests")
        for path in sorted(test_root.glob("test_*.py"))
    )
    device_sources = tuple(
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / "devices").glob("*/src/*.py"))
    )
    return tuple(sorted(set(CORE_INCLUDES + tests + device_sources)))


def main() -> None:
    includes = archive_inputs()
    missing = [name for name in includes if not (ROOT / name).is_file()]
    if missing:
        raise FileNotFoundError(f"archive inputs missing: {missing}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = OUTPUT.with_suffix(OUTPUT.suffix + ".tmp")
    checksums = []
    with zipfile.ZipFile(temporary_output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in includes:
            print(f"packing {name}", flush=True)
            payload = (ROOT / name).read_bytes()
            checksums.append(f"{hashlib.sha256(payload).hexdigest()}  {name}")
            info = zipfile.ZipInfo(f"SafeNest_v4.0/{name}", date_time=(2026, 7, 28, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, payload)
        sums_info = zipfile.ZipInfo(
            "SafeNest_v4.0/SHA256SUMS.txt", date_time=(2026, 7, 28, 0, 0, 0)
        )
        sums_info.compress_type = zipfile.ZIP_DEFLATED
        sums_info.external_attr = 0o644 << 16
        archive.writestr(sums_info, "\n".join(checksums) + "\n")
    temporary_output.replace(OUTPUT)
    digest = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    (OUTPUT.with_suffix(OUTPUT.suffix + ".sha256")).write_text(
        f"{digest}  {OUTPUT.name}\n", encoding="utf-8"
    )
    print(f"{OUTPUT} ({OUTPUT.stat().st_size} bytes)")
    print(f"sha256={digest}")


if __name__ == "__main__":
    main()
