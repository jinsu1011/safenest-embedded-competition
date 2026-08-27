"""Active SafeNest mmWave path: SW-01 → M-PROT-3 → R1/R2 → frozen B23.

This is the default team runtime. The old M-N4/M-N9 240-sample path is
legacy/non-active and must not be called from here.
"""

from __future__ import annotations

import threading
from typing import Mapping

from ai.mmwave_b23_bridge import (
    bundle_from_packet,
    bundle_from_sensor,
    json_safe_receipt,
    presence_from_sensor,
)
from ai.mmwave_prototype.mmwave_m_prot_2_b23_runtime import (
    CANDIDATE_ID,
    PANEL_ID,
    PRIMARY_REPRESENTATION,
    SCALER_CONTENT_SHA256,
    SOURCE_ARTIFACT_SHA256,
)
from ai.mmwave_prototype.mmwave_m_prot_3_integration_runtime import (
    MProt3FailClosed,
    MProt3IntegrationRuntime,
)
from ai.result import AIResult
from gateway.protocol import TelemetryPayload
from paths import ONDEVICE_AI_ROOT

SOURCE = "pytorch"
MODEL_ID = CANDIDATE_ID
MODEL_VERSION = "m_prot_b23_pytorch_float32_v1"


class B23TeamRuntime:
    """Thread-safe wrapper around the frozen M-PROT-3 composer."""

    def __init__(self, root=None) -> None:
        self._lock = threading.RLock()
        self._runtime = MProt3IntegrationRuntime(root=root or ONDEVICE_AI_ROOT)
        self._last_ingest_error: str | None = None
        self._wire_observed = False

    @property
    def wire_observed(self) -> bool:
        return self._wire_observed

    @property
    def buffered_count(self) -> int:
        with self._lock:
            return self._runtime.composer.buffered_count

    def observe_packet(self, packet: TelemetryPayload) -> None:
        with self._lock:
            self._wire_observed = True
            try:
                self._runtime.ingest_bundle(bundle_from_packet(packet))
                self._last_ingest_error = None
            except MProt3FailClosed as exc:
                self._last_ingest_error = exc.code

    def observe_sensor(self, sensor: Mapping[str, object]) -> None:
        with self._lock:
            try:
                self._runtime.ingest_bundle(bundle_from_sensor(sensor))
                self._last_ingest_error = None
            except MProt3FailClosed as exc:
                self._last_ingest_error = exc.code

    def evaluate(self, sensor: Mapping[str, object], now: float) -> AIResult:
        with self._lock:
            if not self._wire_observed:
                self.observe_sensor(sensor)
            if self._last_ingest_error is not None:
                return _unavailable(now, self._last_ingest_error, self._last_ingest_error)
            presence_available, presence_true = presence_from_sensor(sensor)
            receipt = self._runtime.try_infer(
                presence_available=presence_available and presence_true,
                lineage_class="FIXTURE_NON_CAMPAIGN",
            )
            return map_receipt_to_ai_result(
                receipt,
                now=now,
                presence_available=presence_available,
                presence_true=presence_true,
            )


def map_receipt_to_ai_result(
    receipt: object,
    *,
    now: float,
    presence_available: bool,
    presence_true: bool,
) -> AIResult:
    payload = json_safe_receipt(receipt)
    proto = payload.get("prototype_receipt") if isinstance(payload.get("prototype_receipt"), dict) else {}
    metadata = {
        "runtime": "M_PROT_B23",
        "panel_id": PANEL_ID,
        "candidate_id": CANDIDATE_ID,
        "representation": PRIMARY_REPRESENTATION,
        "artifact_sha256": payload.get("artifact_sha256") or SOURCE_ARTIFACT_SHA256,
        "scaler_content_sha256": payload.get("scaler_content_sha256") or SCALER_CONTENT_SHA256,
        "window_ready": bool(payload.get("window_ready")),
        "r1_sample_count": payload.get("r1_sample_count"),
        "assembled_dim": payload.get("assembled_dim"),
        "fail_closed_code": payload.get("fail_closed_code"),
        "b23_status": payload.get("status"),
        "breathing_probability": proto.get("breathing_probability"),
        "breathing_decision": proto.get("breathing_decision"),
        "rr_bpm": proto.get("rr_bpm"),
        "rr_status": proto.get("rr_status"),
        "quality_probability": proto.get("quality_probability"),
        "quality_decision": proto.get("quality_decision"),
        "prototype_semantics": True,
        "PROTOTYPE_INTEGRATION_ONLY": True,
        "NOT_FINAL_SELECTED_MODEL": True,
        "risk_contribution_deferred": True,
        "apnea_emitted": False,
        "m_n9_fallback": False,
        "spectral_fallback": False,
        "vendor_rr_model_input": False,
        "PI_TORCH_NOT_LIVE_VERIFIED": True,
        "LIVE_HARDWARE_EXECUTED": False,
        "receipt": payload,
    }
    status = str(payload.get("status") or "UNAVAILABLE")
    fail = payload.get("fail_closed_code")

    if status == "WINDOW_NOT_READY" or fail == "WINDOW_NOT_READY":
        return _unavailable(now, "WINDOW_NOT_READY", "WINDOW_NOT_READY", metadata)
    if payload.get("window_ready") and presence_available and not presence_true:
        metadata["fail_closed_code"] = "PRESENCE_FALSE"
        return _unavailable(now, "PRESENCE_FALSE", "PRESENCE_FALSE", metadata)
    if status == "UNAVAILABLE" and fail == "PRESENCE_UNAVAILABLE":
        return _unavailable(now, "PRESENCE_UNAVAILABLE", "PRESENCE_UNAVAILABLE", metadata)
    if status == "QUALITY_SUPPRESSED" or fail == "QUALITY_FAIL":
        return _unavailable(now, "QUALITY_SUPPRESSED", fail or "QUALITY_FAIL", metadata)
    if status == "RR_UNAVAILABLE" or fail == "UNAVAILABLE_INVALID_DECODE":
        return _unavailable(now, "RR_UNAVAILABLE", fail or "UNAVAILABLE_INVALID_DECODE", metadata)
    if status == "PHYSIOLOGY_ELIGIBLE":
        confidence = proto.get("breathing_probability")
        return AIResult(
            sensor_id="mmwave",
            timestamp=now,
            available=True,
            source=SOURCE,
            state="PHYSIOLOGY_ELIGIBLE",
            score=0.0,
            confidence=float(confidence) if isinstance(confidence, (int, float)) else 0.0,
            model_id=MODEL_ID,
            model_version=MODEL_VERSION,
            metadata=metadata,
        )
    if status == "ABSENT":
        confidence = proto.get("breathing_probability")
        return AIResult(
            sensor_id="mmwave",
            timestamp=now,
            available=True,
            source=SOURCE,
            state="ABSENT",
            score=0.0,
            confidence=float(confidence) if isinstance(confidence, (int, float)) else 0.0,
            model_id=MODEL_ID,
            model_version=MODEL_VERSION,
            metadata={**metadata, "absent_is_not_apnea": True},
        )
    return _unavailable(now, status if status != "UNAVAILABLE" else "UNAVAILABLE", fail or status, metadata)


def _unavailable(now: float, state: str, error: str, metadata: dict | None = None) -> AIResult:
    return AIResult(
        sensor_id="mmwave",
        timestamp=now,
        available=False,
        source="unavailable",
        state=state,
        error=error,
        metadata=metadata or {},
    )
