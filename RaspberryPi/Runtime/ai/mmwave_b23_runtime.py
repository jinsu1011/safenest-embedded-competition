"""Active SafeNest mmWave path: SW-01 → M-PROT-3 → R1/R2 → frozen B23.

This is the default team runtime. The old M-N4/M-N9 240-sample path is
legacy/non-active and must not be called from here.

Active path:
  ESP nested telemetry
  → parse breath_phase
  → parse physical ts (ts_monotonic_ms / 1000, no age subtraction)
  → parse nested mmwave.seq
  → boot/presence semantics
  → SW-01 / M-PROT-3 Sample
  → R1 300 @ 10 Hz
  → R2 621
  → B23

No M-N4 ts-age reconstruction. No M-N9 fallback.
"""

from __future__ import annotations

import math
import threading
from typing import Mapping

from ai.mmwave_b23_bridge import (
    json_safe_receipt,
    mprot3_session_id,
    phase_age_is_fresh,
    physical_timestamp_s,
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
from ai.mmwave_prototype.mmwave_sw01_interface_checker import Sample, StreamBundle
from ai.result import AIResult
from gateway.protocol import TelemetryPayload
from paths import ONDEVICE_AI_ROOT

SOURCE = "pytorch"
MODEL_ID = CANDIDATE_ID
MODEL_VERSION = "m_prot_b23_pytorch_float32_v1"


def _finite(value: object) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
    )


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


class B23TeamRuntime:
    """Thread-safe wrapper around the frozen M-PROT-3 composer."""

    def __init__(self, root=None) -> None:
        self._lock = threading.RLock()
        self._runtime = MProt3IntegrationRuntime(root=root or ONDEVICE_AI_ROOT)
        self._last_ingest_error: str | None = None
        self._wire_observed = False
        self._last_nested_seq: int | None = None
        self._last_boot_id: str | None = None
        self._phase_seq_prev: int | None = None
        self._phase_seq_curr: int | None = None
        self._phase_seq_delta: int | None = None
        self._missing_phase_event_count = 0
        self._republish_skip_count = 0

    @property
    def wire_observed(self) -> bool:
        return self._wire_observed

    @property
    def buffered_count(self) -> int:
        with self._lock:
            return self._runtime.composer.buffered_count

    @property
    def phase_seq_monitor(self) -> dict[str, int | None]:
        with self._lock:
            return self._monitor_locked()

    def observe_packet(self, packet: TelemetryPayload) -> None:
        with self._lock:
            self._wire_observed = True
            self._admit(
                phase=packet.breath_phase,
                ts_monotonic_ms=packet.ts_monotonic_ms,
                phase_age_ms=packet.phase_age_ms,
                nested_seq=_int_or_none(packet.mmwave_sequence),
                boot_id=packet.boot_id if isinstance(packet.boot_id, str) else None,
                packet_session_id=packet.session_id,
                device_id=packet.device_id,
                health_ok=not (
                    isinstance(packet.valid, dict) and packet.valid.get("respiration") is False
                ),
            )

    def observe_sensor(self, sensor: Mapping[str, object]) -> None:
        with self._lock:
            values = sensor.get("values") if isinstance(sensor.get("values"), Mapping) else {}
            if not isinstance(values, Mapping):
                values = {}
            boot = sensor.get("boot_id")
            self._admit(
                phase=values.get("breath_phase"),
                ts_monotonic_ms=values.get("ts_monotonic_ms"),
                phase_age_ms=values.get("phase_age_ms"),
                nested_seq=_int_or_none(values.get("mmwave_sequence")),
                boot_id=boot if isinstance(boot, str) else None,
                packet_session_id=values.get("session_id") if isinstance(values.get("session_id"), str) else None,
                device_id=sensor.get("device_id") if isinstance(sensor.get("device_id"), str) else None,
                health_ok=values.get("respiration_valid") is not False,
            )

    def evaluate(self, sensor: Mapping[str, object], now: float) -> AIResult:
        with self._lock:
            if not self._wire_observed:
                values = sensor.get("values") if isinstance(sensor.get("values"), Mapping) else {}
                if not isinstance(values, Mapping):
                    values = {}
                boot = sensor.get("boot_id")
                self._admit(
                    phase=values.get("breath_phase"),
                    ts_monotonic_ms=values.get("ts_monotonic_ms"),
                    phase_age_ms=values.get("phase_age_ms"),
                    nested_seq=_int_or_none(values.get("mmwave_sequence")),
                    boot_id=boot if isinstance(boot, str) else None,
                    packet_session_id=values.get("session_id") if isinstance(values.get("session_id"), str) else None,
                    device_id=sensor.get("device_id") if isinstance(sensor.get("device_id"), str) else None,
                    health_ok=values.get("respiration_valid") is not False,
                )
            if self._last_ingest_error is not None:
                return _unavailable(
                    now,
                    self._last_ingest_error,
                    self._last_ingest_error,
                    self._metadata_extras(),
                )
            if self._runtime.composer.buffered_count == 0:
                return _unavailable(
                    now,
                    "WINDOW_NOT_READY",
                    "WINDOW_NOT_READY",
                    self._metadata_extras(),
                )
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
                extras=self._metadata_extras(),
            )

    def _admit(
        self,
        *,
        phase: object,
        ts_monotonic_ms: object,
        phase_age_ms: object,
        nested_seq: int | None,
        boot_id: str | None,
        packet_session_id: str | None,
        device_id: str | None,
        health_ok: bool,
    ) -> None:
        boot_changed = (
            boot_id is not None
            and self._last_boot_id is not None
            and boot_id != self._last_boot_id
        )
        if boot_changed:
            self._last_nested_seq = None
            self._missing_phase_event_count = 0
            self._republish_skip_count = 0
            self._phase_seq_prev = None
            self._phase_seq_curr = None
            self._phase_seq_delta = None

        # Stale / null phase, missing physical time, or missing nested sequence
        # must not be admitted as a new B23 observation (and must not masquerade
        # as a repeated valid sample).
        if not _finite(phase):
            return
        if not phase_age_is_fresh(phase_age_ms):
            return
        t = physical_timestamp_s(ts_monotonic_ms)
        if t is None:
            return
        if nested_seq is None:
            return

        if (
            not boot_changed
            and self._last_nested_seq is not None
            and nested_seq == self._last_nested_seq
        ):
            self._republish_skip_count += 1
            self._note_seq(nested_seq)
            return

        if self._last_nested_seq is not None:
            delta = int(nested_seq) - int(self._last_nested_seq)
            if delta > 1:
                self._missing_phase_event_count += delta - 1

        bundle = StreamBundle(
            device_identity=device_id or "safenest-mmwave",
            interface_identity="safenest.telemetry.v1",
            configuration_identity="mr60_tcp_v1_phase_waveform",
            observation_kind="near_raw_phase",
            samples=[
                Sample(
                    t=t,
                    phase=float(phase),
                    seq=int(nested_seq),
                    health_ok=health_ok,
                    session_id=mprot3_session_id(
                        boot_id=boot_id,
                        packet_session_id=packet_session_id,
                    ),
                    reset_flag=boot_changed,
                    scalar_rr=None,
                )
            ],
        )
        try:
            self._runtime.ingest_bundle(bundle)
            self._last_ingest_error = None
            self._last_nested_seq = nested_seq
            self._last_boot_id = boot_id
            self._note_seq(nested_seq)
        except MProt3FailClosed as exc:
            self._last_ingest_error = exc.code
            self._last_nested_seq = None

    def _note_seq(self, nested_seq: int) -> None:
        prev = self._phase_seq_curr
        self._phase_seq_prev = prev
        self._phase_seq_curr = int(nested_seq)
        if prev is None:
            self._phase_seq_delta = None
        else:
            self._phase_seq_delta = int(nested_seq) - int(prev)

    def _monitor_locked(self) -> dict[str, int | None]:
        return {
            "previous_nested_phase_seq": self._phase_seq_prev,
            "current_nested_phase_seq": self._phase_seq_curr,
            "delta": self._phase_seq_delta,
            "missing_phase_event_count": self._missing_phase_event_count,
            "republish_skip_count": self._republish_skip_count,
        }

    def _metadata_extras(self) -> dict:
        return {
            "live_phase_seq_monitor": self._monitor_locked(),
            "live_phase_seq_jump_monitor": "PREPARED_FOR_M_PROT_5C",
            "physical_timestamp_semantic": "ts_monotonic_ms_is_physical_observation_timestamp",
            "phase_age_usage": "FRESHNESS_ONLY",
            "b23_source_sequence": "NESTED_MMWAVE_SEQ",
            "outer_sequence_role": "TRANSPORT_PUBLICATION_ONLY",
            "vendor_rr_model_input": False,
            "m_n9_fallback": False,
            "double_age_subtraction": "NOT_PRESENT_IN_NEW_B23_PATH",
            "mprot3_session_mapping": "boot:{boot_id}",
        }


def map_receipt_to_ai_result(
    receipt: object,
    *,
    now: float,
    presence_available: bool,
    presence_true: bool,
    extras: dict | None = None,
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
    if extras:
        metadata.update(extras)
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
