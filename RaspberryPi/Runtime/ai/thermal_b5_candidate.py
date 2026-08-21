"""Strict diagnostic adapter for the locked Thermal T-B5 candidate.

This adapter is intentionally absent from ``LazyModel`` and from the
production model manifest.  It exists so a Raspberry Pi candidate/HIL run can
exercise the exact MI48 -> Celsius -> P1 -> INT8 contract without reusing the
historical per-frame min/max interpreter.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Any, Callable, Final

import numpy as np

from paths import ONDEVICE_AI_ROOT


B5_ROOT: Final = ONDEVICE_AI_ROOT / "models" / "rp_x0_b_complete" / "thermal"
B5_MODEL: Final = B5_ROOT / "SMALL_CNN_BASELINE_V1_P1_full_int8.tflite"
B5_SHA256: Final = "fa9730c29535477a3994c11e664474a0ca0116afaaa172889f47446ab2ac46be"
B5_SIZE_BYTES: Final = 318_280
B5_INPUT_SHAPE: Final = (1, 62, 80, 1)
B5_OUTPUT_SHAPE: Final = (1, 3)
B5_INPUT_SCALE: Final = 0.31791284680366516
B5_INPUT_ZERO_POINT: Final = -125
B5_OUTPUT_SCALE: Final = 0.00390625
B5_OUTPUT_ZERO_POINT: Final = -128
P1_PROFILE_ID: Final = "P1_TRAIN_FITTED_GLOBAL_ZSCORE"
VERIFIED_PHYSICAL_UNIT_ID: Final = "MI48_UINT16_0P1_KELVIN"
PHYSICAL_CONVERSION_ID: Final = "MI48_UINT16_0P1_KELVIN_TO_CELSIUS"
VERIFIED_ORIENTATION_ID: Final = "NATIVE_ROWS_62_COLS_80_MATCHES_TRAINING_CANONICAL"


class ThermalB5CandidateError(RuntimeError):
    """The candidate input, artifact, or interpreter violated its lock."""


@dataclass(frozen=True)
class ThermalB5Prediction:
    class_index: int
    class_name: str
    confidence: float
    probabilities: list[float]
    latency_ms: float
    model_id: str
    model_version: str
    metadata: dict[str, object]


class ThermalB5CandidateModel:
    """Candidate-only T-B5 interpreter with the frozen P1 contract."""

    def __init__(
        self,
        *,
        model_path: str | Path = B5_MODEL,
        lock_root: str | Path = B5_ROOT,
        orientation_contract: str | None = None,
        physical_unit_contract: str | None = None,
        interpreter_factory: Callable[[Path], object] | None = None,
    ) -> None:
        self.model_path = Path(model_path).resolve()
        self.lock_root = Path(lock_root).resolve()
        self.orientation_contract = orientation_contract
        self.physical_unit_contract = physical_unit_contract
        self.runtime_metadata = {
            "runtime_role": "DIAGNOSTIC_ONLY",
            "production_selected": False,
            "model_identity": B5_SHA256,
            "preprocessing_identity": P1_PROFILE_ID,
            "physical_unit_identity": physical_unit_contract or "UNVERIFIED",
            "physical_conversion_identity": PHYSICAL_CONVERSION_ID,
            "orientation_identity": orientation_contract or "UNVERIFIED",
        }
        self.p1 = _read_json(self.lock_root / "p1_preprocessing.json")
        self.identity = _read_json(self.lock_root / "identity.json")
        self.class_document = _read_json(self.lock_root / "class_map.json")
        self.class_map = {
            int(key): str(value)
            for key, value in self.class_document.items()
            if str(key).isdigit()
        }
        self._validate_locks()

        factory = interpreter_factory or _make_interpreter
        self.interpreter = factory(self.model_path)
        allocate = getattr(self.interpreter, "allocate_tensors", None)
        if callable(allocate):
            allocate()
        self.input_info = self.interpreter.get_input_details()[0]
        self.output_info = self.interpreter.get_output_details()[0]
        self._validate_tensor_contract()

    def predict(self, raw_frame: object) -> ThermalB5Prediction:
        if self.orientation_contract != VERIFIED_ORIENTATION_ID:
            raise ThermalB5CandidateError(
                "THERMAL_ORIENTATION_NOT_VERIFIED_FOR_TRAINING_CANONICAL"
            )
        if self.physical_unit_contract != VERIFIED_PHYSICAL_UNIT_ID:
            raise ThermalB5CandidateError(
                "THERMAL_PHYSICAL_UNIT_NOT_VERIFIED_FOR_CELSIUS_CONVERSION"
            )
        raw = np.asarray(raw_frame)
        if raw.shape != (62, 80):
            raise ThermalB5CandidateError(
                f"thermal raw frame shape must be (62, 80), got {raw.shape}"
            )
        if raw.dtype == np.bool_ or not np.issubdtype(raw.dtype, np.number):
            raise ThermalB5CandidateError("thermal raw frame must be numeric uint16 words")
        if not np.all(np.isfinite(raw)):
            raise ThermalB5CandidateError("thermal raw frame contains NaN or infinity")
        if np.any(raw < 0) or np.any(raw > 0xFFFF):
            raise ThermalB5CandidateError("thermal raw frame is outside uint16 range")
        if not np.all(raw == np.rint(raw)):
            raise ThermalB5CandidateError("thermal raw frame must contain integer words")
        raw_u16 = raw.astype(np.uint16)
        if np.any(raw_u16 == np.uint16(0xFFFF)):
            raise ThermalB5CandidateError("THERMAL_INVALID_PIXEL_SENTINEL_0XFFFF")

        celsius = raw_u16.astype(np.float64) / 10.0 - 273.15
        mean = float(self.p1["mean"])
        std = float(self.p1["effective_std"])
        zscore = (celsius - mean) / std
        prequant = np.rint(zscore / B5_INPUT_SCALE + B5_INPUT_ZERO_POINT)
        low_count = int(np.count_nonzero(prequant < -128))
        high_count = int(np.count_nonzero(prequant > 127))
        quantized = np.clip(prequant, -128, 127).astype(np.int8)[None, ..., None]

        started = time.perf_counter()
        self.interpreter.set_tensor(self.input_info["index"], quantized)
        self.interpreter.invoke()
        raw_output = np.asarray(self.interpreter.get_tensor(self.output_info["index"]))
        latency_ms = (time.perf_counter() - started) * 1000.0
        if raw_output.shape != B5_OUTPUT_SHAPE:
            raise ThermalB5CandidateError(
                f"thermal output shape changed: {raw_output.shape} != {B5_OUTPUT_SHAPE}"
            )
        dequantized = (
            raw_output.astype(np.float64) - B5_OUTPUT_ZERO_POINT
        ) * B5_OUTPUT_SCALE
        values = np.clip(dequantized.reshape(-1), 0.0, None)
        if not np.all(np.isfinite(values)) or float(values.sum()) <= 0:
            raise ThermalB5CandidateError("thermal model output is invalid")
        probabilities = values / float(values.sum())
        class_index = int(np.argmax(probabilities))
        total_pixels = int(raw_u16.size)
        return ThermalB5Prediction(
            class_index=class_index,
            class_name=self.class_map.get(class_index, f"CLASS_{class_index}"),
            confidence=float(probabilities[class_index]),
            probabilities=[float(value) for value in probabilities],
            latency_ms=float(latency_ms),
            model_id="SMALL_CNN_BASELINE_V1_P1_FULL_INT8",
            model_version="T-B5",
            metadata={
                "runtime_role": "DIAGNOSTIC_ONLY",
                "production_selected": False,
                "model_identity": B5_SHA256,
                "preprocessing_identity": P1_PROFILE_ID,
                "physical_unit_identity": VERIFIED_PHYSICAL_UNIT_ID,
                "physical_conversion_identity": PHYSICAL_CONVERSION_ID,
                "physical_conversion_applied": True,
                "temperature_calibrated": False,
                "orientation_identity": VERIFIED_ORIENTATION_ID,
                "orientation_transform": "NONE",
                "input_scale": B5_INPUT_SCALE,
                "input_zero_point": B5_INPUT_ZERO_POINT,
                "input_low_saturation_count": low_count,
                "input_low_saturation_ratio": low_count / total_pixels,
                "input_high_saturation_count": high_count,
                "input_high_saturation_ratio": high_count / total_pixels,
                "celsius_minimum": float(celsius.min()),
                "celsius_maximum": float(celsius.max()),
                "raw_output_int8": [int(value) for value in raw_output.reshape(-1)],
                "dequantized_output": [float(value) for value in dequantized.reshape(-1)],
            },
        )

    def _validate_locks(self) -> None:
        if not self.model_path.is_file():
            raise ThermalB5CandidateError(f"candidate model missing: {self.model_path}")
        if self.model_path.stat().st_size != B5_SIZE_BYTES:
            raise ThermalB5CandidateError("candidate model size does not match T-B5 lock")
        actual_sha = hashlib.sha256(self.model_path.read_bytes()).hexdigest()
        if actual_sha != B5_SHA256:
            raise ThermalB5CandidateError(
                f"candidate model SHA-256 mismatch: {actual_sha} != {B5_SHA256}"
            )
        if self.p1.get("profile_id") != P1_PROFILE_ID:
            raise ThermalB5CandidateError("P1 preprocessing identity mismatch")
        if self.p1.get("fit_role") != "TRAIN":
            raise ThermalB5CandidateError("P1 statistics were not fitted on TRAIN")
        if not math.isclose(float(self.p1["mean"]), 22.769290618485442, abs_tol=1e-12):
            raise ThermalB5CandidateError("P1 mean mismatch")
        if not math.isclose(float(self.p1["effective_std"]), 2.8684523405441222, abs_tol=1e-12):
            raise ThermalB5CandidateError("P1 standard deviation mismatch")
        if self.identity.get("selected_candidate_id") != "FULL_INT8":
            raise ThermalB5CandidateError("candidate identity is not FULL_INT8")
        if self.identity.get("production_manifest_unchanged") is not True:
            raise ThermalB5CandidateError("candidate lock no longer records non-production status")
        if self.class_map != {
            0: "NOT_HUMAN",
            1: "HUMAN_NORMAL",
            2: "HUMAN_FALL",
        }:
            raise ThermalB5CandidateError("candidate class map mismatch")
        if "LYING" not in str(self.class_document.get("semantic_restriction", "")):
            raise ThermalB5CandidateError("HUMAN_FALL proxy semantic restriction missing")

    def _validate_tensor_contract(self) -> None:
        checks = (
            ("input", self.input_info, B5_INPUT_SHAPE, "int8", B5_INPUT_SCALE, B5_INPUT_ZERO_POINT),
            ("output", self.output_info, B5_OUTPUT_SHAPE, "int8", B5_OUTPUT_SCALE, B5_OUTPUT_ZERO_POINT),
        )
        for label, details, shape, dtype, scale, zero_point in checks:
            actual_shape = tuple(int(value) for value in details["shape"])
            actual_dtype = np.dtype(details["dtype"]).name
            actual_scale, actual_zero = _quantization(details)
            if actual_shape != shape:
                raise ThermalB5CandidateError(f"{label} shape mismatch: {actual_shape} != {shape}")
            if actual_dtype != dtype:
                raise ThermalB5CandidateError(f"{label} dtype mismatch: {actual_dtype} != {dtype}")
            if not math.isclose(actual_scale, scale, rel_tol=0, abs_tol=1e-12):
                raise ThermalB5CandidateError(f"{label} scale mismatch: {actual_scale} != {scale}")
            if actual_zero != zero_point:
                raise ThermalB5CandidateError(
                    f"{label} zero-point mismatch: {actual_zero} != {zero_point}"
                )


def _make_interpreter(model_path: Path) -> object:
    try:
        from ai_edge_litert.interpreter import Interpreter
    except ImportError:
        try:
            from tflite_runtime.interpreter import Interpreter
        except ImportError:
            try:
                from tensorflow.lite.python.interpreter import Interpreter
            except ImportError as error:
                raise ThermalB5CandidateError(
                    "LiteRT/TFLite interpreter is unavailable; install the approved Pi requirements"
                ) from error
    return Interpreter(model_path=str(model_path), num_threads=1)


def _quantization(details: dict[str, Any]) -> tuple[float, int]:
    parameters = details.get("quantization_parameters") or {}
    scales = parameters.get("scales")
    zero_points = parameters.get("zero_points")
    if scales is not None and len(scales) == 1:
        return float(scales[0]), int(zero_points[0])
    scale, zero_point = details["quantization"]
    return float(scale), int(zero_point)


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ThermalB5CandidateError(f"candidate lock file missing: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ThermalB5CandidateError(f"candidate lock must be an object: {path}")
    return document
