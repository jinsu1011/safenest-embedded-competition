"""Team telemetry → SW-01 StreamBundle semantic bridge (M-PROT-5B).

Does not invent UART decoding. Maps existing SafeNest TCP v1 / snapshot
fields onto frozen SW-01 Sample semantics.

Required: phase-like waveform + monotonic source timestamp.
Vendor scalar RR is never used as a B23 model input.
"""

from __future__ import annotations

import math
from typing import Any, Mapping

from ai.mmwave_prototype.mmwave_sw01_interface_checker import Sample, StreamBundle
from gateway.protocol import TelemetryPayload

INTERFACE_IDENTITY = "safenest.telemetry.v1"
CONFIGURATION_IDENTITY = "mr60_tcp_v1_phase_waveform"
OBSERVATION_KIND = "near_raw_phase"


def _finite(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(float(value))


def _int_or_none(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return int(value)


def observation_timestamp_s(ts_monotonic_ms: object, phase_age_ms: object) -> float | None:
    """Source event time = ts_monotonic_ms - phase_age_ms, in seconds.

    Packet receive time is not used when source timing is present.
    """

    if not (_finite(ts_monotonic_ms) and _finite(phase_age_ms)):
        return None
    return (float(ts_monotonic_ms) - float(phase_age_ms)) / 1000.0


def bundle_from_sensor(
    sensor: Mapping[str, object],
    *,
    device_identity: str | None = None,
) -> StreamBundle:
    values = sensor.get("values") if isinstance(sensor.get("values"), Mapping) else {}
    if not isinstance(values, Mapping):
        values = {}
    phase = values.get("breath_phase")
    t = observation_timestamp_s(values.get("ts_monotonic_ms"), values.get("phase_age_ms"))
    seq = _int_or_none(sensor.get("sequence"))
    session = values.get("session_id")
    health_ok = True
    if values.get("respiration_valid") is False:
        health_ok = False
    device = device_identity or _string(sensor.get("device_id")) or "safenest-mmwave"
    sample = Sample(
        t=t,
        phase=float(phase) if _finite(phase) else None,
        seq=seq,
        health_ok=health_ok,
        session_id=session if isinstance(session, str) and session else None,
        reset_flag=False,
        scalar_rr=None,
    )
    return StreamBundle(
        device_identity=device,
        interface_identity=INTERFACE_IDENTITY,
        configuration_identity=CONFIGURATION_IDENTITY,
        observation_kind=OBSERVATION_KIND,
        samples=[sample],
    )


def bundle_from_packet(packet: TelemetryPayload) -> StreamBundle:
    t = observation_timestamp_s(packet.ts_monotonic_ms, packet.phase_age_ms)
    health_ok = True
    if isinstance(packet.valid, dict) and packet.valid.get("respiration") is False:
        health_ok = False
    sample = Sample(
        t=t,
        phase=float(packet.breath_phase) if _finite(packet.breath_phase) else None,
        seq=int(packet.header.sequence),
        health_ok=health_ok,
        session_id=packet.session_id if packet.session_id else None,
        reset_flag=False,
        scalar_rr=None,
    )
    return StreamBundle(
        device_identity=packet.device_id,
        interface_identity=INTERFACE_IDENTITY,
        configuration_identity=CONFIGURATION_IDENTITY,
        observation_kind=OBSERVATION_KIND,
        samples=[sample],
    )


def presence_from_sensor(sensor: Mapping[str, object]) -> tuple[bool, bool]:
    """Return (presence_available, presence_gate_satisfied).

    Presence is taken only from the team explicit occupancy field.
    It is never inferred from RR, breathing probability, quality, or amplitude.
    """

    values = sensor.get("values") if isinstance(sensor.get("values"), Mapping) else {}
    if not isinstance(values, Mapping):
        return False, False
    available = values.get("presence_available") is True
    presence = values.get("presence")
    if not available or not isinstance(presence, bool):
        return False, False
    return True, bool(presence)


def _string(value: object) -> str | None:
    return value if isinstance(value, str) and value else None


def json_safe_receipt(receipt: Any) -> dict[str, Any]:
    payload = receipt.to_json() if hasattr(receipt, "to_json") else dict(receipt)
    return _json_safe(payload)


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)
