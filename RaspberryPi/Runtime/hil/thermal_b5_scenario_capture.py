"""Create synchronized OpenCV, terminal, raw, and JSON scenario evidence.

The source is an existing Runtime Thermal NPZ written by ``sensor_logger``.
This utility replays one saved frame through the diagnostic T-B5 candidate;
it does not claim live transport latency or temporal fall detection.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Final

import numpy as np

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from ai.thermal_b5_candidate import (
    B5_SHA256,
    VERIFIED_ORIENTATION_ID,
    VERIFIED_PHYSICAL_UNIT_ID,
    ThermalB5CandidateModel,
)
from hil.thermal_b5_pi_benchmark import load_frames


SCENARIOS: Final = {
    "EMPTY_ROOM": "01_empty_room",
    "STANDING": "02_standing",
    "SITTING": "03_sitting",
    "LYING_OR_HUMAN_FALL_PROXY": "04_lying_proxy",
    "POSTURE_TRANSITION": "05_posture_transition",
    "SENSOR_RESTART": "06_sensor_restart",
    "NETWORK_DELAY_PACKET_LOSS": "07_network_loss",
    "INVALID_FRAME": "08_invalid_frame",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render synchronized Thermal B5 saved-frame scenario evidence."
    )
    parser.add_argument("--input-npz", action="append", required=True)
    parser.add_argument("--scenario", choices=tuple(SCENARIOS), required=True)
    parser.add_argument("--frame-index", type=int, required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--raw-output-dir", required=True)
    parser.add_argument("--orientation-contract", required=True)
    parser.add_argument("--physical-unit-contract", required=True)
    return parser.parse_args()


def render(args: argparse.Namespace) -> dict[str, Any]:
    if args.orientation_contract != VERIFIED_ORIENTATION_ID:
        raise ValueError("orientation contract is not the reviewed canonical identity")
    if args.physical_unit_contract != VERIFIED_PHYSICAL_UNIT_ID:
        raise ValueError("physical-unit contract is not the reviewed MI48 identity")
    try:
        import cv2
    except ImportError as error:
        raise RuntimeError(
            "OpenCV is unavailable; obtain approval before installing opencv-python-headless "
            "in the Raspberry Pi SafeNest venv"
        ) from error

    rows = load_frames([Path(value).resolve() for value in args.input_npz])
    if args.frame_index < 0 or args.frame_index >= len(rows):
        raise IndexError(
            f"--frame-index {args.frame_index} is outside 0..{len(rows) - 1}"
        )
    item = rows[args.frame_index]
    model = ThermalB5CandidateModel(
        orientation_contract=args.orientation_contract,
        physical_unit_contract=args.physical_unit_contract,
    )
    prediction = model.predict(item["frame"])
    prefix = SCENARIOS[args.scenario]
    output_dir = Path(args.output_dir).resolve()
    raw_output_dir = Path(args.raw_output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    raw_output_dir.mkdir(parents=True, exist_ok=True)
    opencv_path = output_dir / f"{prefix}_opencv.png"
    terminal_path = output_dir / f"{prefix}_terminal.png"
    raw_path = raw_output_dir / f"{prefix}.npz"
    evidence_path = output_dir / f"{prefix}_evidence.json"

    celsius = item["frame"].astype(np.float64) / 10.0 - 273.15
    low, high = np.percentile(celsius, [2, 98])
    if high <= low:
        high = low + 1.0
    normalized = np.clip((celsius - low) * (255.0 / (high - low)), 0, 255).astype(np.uint8)
    heatmap = cv2.applyColorMap(normalized, cv2.COLORMAP_INFERNO)
    heatmap = cv2.resize(heatmap, (640, 496), interpolation=cv2.INTER_NEAREST)
    cv2.putText(
        heatmap,
        f"{args.scenario}  seq={item['frame_sequence']}  {prediction.class_name}",
        (12, 28),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.58,
        (255, 255, 255),
        2,
        cv2.LINE_AA,
    )
    if not cv2.imwrite(str(opencv_path), heatmap):
        raise OSError(f"failed to write {opencv_path}")

    lines = [
        "SafeNest Thermal T-B5 candidate evidence",
        f"scenario: {args.scenario}",
        "mode: SAVED_RUNTIME_NPZ_REPLAY (not live E2E)",
        f"source: {item['source_file']} frame_index={item['frame_index']}",
        f"timestamp: {item['timestamp']:.6f} sequence: {item['frame_sequence']}",
        f"class: {prediction.class_name} confidence: {prediction.confidence:.6f}",
        f"latency_ms: {prediction.latency_ms:.6f}",
        "validity: VALID freshness: SOURCE_TIMESTAMP_PRESERVED",
        f"low_saturation: {prediction.metadata['input_low_saturation_ratio']:.6f}",
        f"high_saturation: {prediction.metadata['input_high_saturation_ratio']:.6f}",
        f"model_sha256: {B5_SHA256}",
        "HUMAN_FALL semantic: LYING-derived posture proxy",
    ]
    terminal = np.zeros((720, 1280, 3), dtype=np.uint8)
    for index, line in enumerate(lines):
        cv2.putText(
            terminal,
            line,
            (28, 48 + index * 48),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.66,
            (120, 255, 160),
            1,
            cv2.LINE_AA,
        )
    if not cv2.imwrite(str(terminal_path), terminal):
        raise OSError(f"failed to write {terminal_path}")

    np.savez_compressed(
        raw_path,
        frames=item["frame"][None, ...],
        timestamps=np.asarray([item["timestamp"]], dtype=np.float64),
        frame_sequences=np.asarray([item["frame_sequence"]], dtype=np.uint32),
        model_sha256=np.asarray([B5_SHA256]),
        scenario=np.asarray([args.scenario]),
    )
    evidence = {
        "schema": "safenest.thermal_b5.scenario_evidence.v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "scenario": args.scenario,
        "mode": "SAVED_RUNTIME_NPZ_REPLAY",
        "live_sensor_execution": False,
        "source_file": item["source_file"],
        "source_frame_index": item["frame_index"],
        "source_timestamp": item["timestamp"],
        "frame_sequence": item["frame_sequence"],
        "validity": "VALID",
        "freshness": "SOURCE_TIMESTAMP_PRESERVED_NOT_LIVE_ASSERTED",
        "class_name": prediction.class_name,
        "confidence": prediction.confidence,
        "latency_ms_inference_only": prediction.latency_ms,
        "model_sha256": B5_SHA256,
        "preprocessing_identity": prediction.metadata["preprocessing_identity"],
        "physical_unit_identity": prediction.metadata["physical_unit_identity"],
        "orientation_identity": prediction.metadata["orientation_identity"],
        "low_saturation_ratio": prediction.metadata["input_low_saturation_ratio"],
        "high_saturation_ratio": prediction.metadata["input_high_saturation_ratio"],
        "outputs": {
            "opencv_image": str(opencv_path),
            "terminal_image": str(terminal_path),
            "raw_npz": str(raw_path),
        },
        "limitations": [
            "not a live end-to-end latency measurement",
            "scenario label requires operator/ground-truth manifest review",
            "HUMAN_FALL is a LYING-derived posture proxy",
        ],
    }
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {**evidence, "evidence_json": str(evidence_path)}


def main() -> int:
    evidence = render(parse_args())
    print(json.dumps(evidence, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
