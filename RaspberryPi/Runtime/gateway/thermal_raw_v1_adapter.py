"""Explicit, fail-closed adapter from exact Thermal Raw V1 to SNTU v1.

Raw V1 and SNTU v1 are different wire contracts.  This module accepts only
one complete 10,080-byte Raw V1 datagram.  It intentionally does not attempt
to repair or bless the blind multi-datagram Raw V1 stream, because that stream
has no frame ID, chunk index, offset, or wire checksum.

The adapter is not wired into the production runtime.  Callers must provide a
reviewed physical-unit and orientation evidence identity before a frame can be
adapted.  The returned SNTU datagrams then use the existing SNTU CRC32 and
bounded reassembly contract.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from numbers import Real
import struct
from typing import Final
import zlib

from .protocol import (
    PACKET_THERMAL_U16_BE,
    THERMAL_HEIGHT,
    THERMAL_META,
    THERMAL_WIDTH,
    PacketHeader,
    ProtocolError,
    ThermalFrame,
    decode_thermal,
)
from .thermal_udp import encode_thermal_udp_frame


RAW_V1_HEADER_WORDS: Final = 80
RAW_V1_PIXEL_WORDS: Final = THERMAL_WIDTH * THERMAL_HEIGHT
RAW_V1_FRAME_WORDS: Final = RAW_V1_HEADER_WORDS + RAW_V1_PIXEL_WORDS
RAW_V1_FRAME_BYTES: Final = RAW_V1_FRAME_WORDS * 2
RAW_V1_WORDS: Final = struct.Struct(f"<{RAW_V1_FRAME_WORDS}H")

RAW_V1_TRANSPORT_ID: Final = "THERMAL_TEST_UDP_RAW_V1_EXACT_DATAGRAM"
SNTU_TRANSPORT_ID: Final = "SAFENEST_THERMAL_UDP_SNTU_V1"
MI48_0P1_KELVIN_CONTRACT: Final = "MI48_UINT16_0P1_KELVIN"
NATIVE_62X80_ORIENTATION_CONTRACT: Final = (
    "NATIVE_ROWS_62_COLS_80_MATCHES_TRAINING_CANONICAL"
)


class RawV1AdapterError(ProtocolError):
    """Raw V1 input cannot be safely represented as an SNTU v1 frame."""


@dataclass(frozen=True)
class RawV1EvidenceContract:
    """Human-reviewed identities required before transport adaptation.

    The current personal Raw V1 capture remains unverified for these fields,
    so no production default instance is provided.
    """

    evidence_id: str
    physical_unit_contract: str
    orientation_contract: str
    source_endianness: str = "little"
    header_word_0_semantics: str = "OBSERVATION_ONLY_NOT_FRAME_COUNTER"
    max_age_seconds: float = 0.5

    def __post_init__(self) -> None:
        if not self.evidence_id.strip():
            raise ValueError("Raw V1 evidence_id is required")
        if self.physical_unit_contract != MI48_0P1_KELVIN_CONTRACT:
            raise ValueError("Raw V1 physical-unit evidence is not approved")
        if self.orientation_contract != NATIVE_62X80_ORIENTATION_CONTRACT:
            raise ValueError("Raw V1 orientation evidence is not approved")
        if self.source_endianness != "little":
            raise ValueError("Raw V1 source endianness must be explicitly little-endian")
        if self.header_word_0_semantics != "OBSERVATION_ONLY_NOT_FRAME_COUNTER":
            raise ValueError("Raw V1 header word 0 must remain observation-only")
        if (
            isinstance(self.max_age_seconds, bool)
            or not isinstance(self.max_age_seconds, Real)
            or not math.isfinite(float(self.max_age_seconds))
            or self.max_age_seconds <= 0
        ):
            raise ValueError("Raw V1 freshness limit must be positive and finite")


@dataclass(frozen=True)
class RawV1Adaptation:
    frame: ThermalFrame
    logical_sntu_payload: bytes
    sntu_datagrams: tuple[bytes, ...]
    received_at: float
    adapted_at: float
    age_seconds: float
    evidence_id: str
    physical_unit_contract: str
    orientation_contract: str
    header_word_0_observed: int
    celsius_minimum: float
    celsius_maximum: float
    logical_crc32: int

    def audit_dict(self) -> dict[str, object]:
        result = asdict(self)
        result.pop("frame")
        result.pop("logical_sntu_payload")
        result.pop("sntu_datagrams")
        result.update(
            {
                "validity": "VALID",
                "freshness": "FRESH",
                "source_transport": RAW_V1_TRANSPORT_ID,
                "destination_transport": SNTU_TRANSPORT_ID,
                "source_frame_bytes": RAW_V1_FRAME_BYTES,
                "sntu_datagram_count": len(self.sntu_datagrams),
                "frame_sequence": self.frame.frame_sequence,
                "width": self.frame.width,
                "height": self.frame.height,
                "minimum_raw": self.frame.minimum_raw,
                "maximum_raw": self.frame.maximum_raw,
                "pixel_endianness": "big",
                "physical_conversion": "C = raw / 10.0 - 273.15",
                "orientation_transform": "NONE",
            }
        )
        return result


def adapt_exact_raw_v1_datagram(
    datagram: bytes,
    *,
    contract: RawV1EvidenceContract,
    bridge_sequence: int,
    bridge_uptime_ms: int,
    received_at: float,
    now: float,
) -> RawV1Adaptation:
    """Validate one exact Raw V1 datagram and encode it as SNTU v1.

    ``bridge_sequence`` and ``bridge_uptime_ms`` are bridge metadata.  Raw V1
    header word 0 is preserved only as an observation and is never promoted to
    a sensor frame counter.
    """

    if len(datagram) != RAW_V1_FRAME_BYTES:
        raise RawV1AdapterError(
            f"RAW_V1_EXACT_FRAME_REQUIRED: {len(datagram)} != {RAW_V1_FRAME_BYTES}"
        )
    sequence = _uint32(bridge_sequence, "bridge_sequence")
    uptime_ms = _uint32(bridge_uptime_ms, "bridge_uptime_ms")
    received = _timestamp(received_at, "received_at")
    adapted = _timestamp(now, "now")
    age = adapted - received
    if age < 0:
        raise RawV1AdapterError("RAW_V1_TIMESTAMP_FROM_FUTURE")
    if age > contract.max_age_seconds:
        raise RawV1AdapterError(
            f"RAW_V1_STALE: age={age:.6f}s ttl={contract.max_age_seconds:.6f}s"
        )

    words = RAW_V1_WORDS.unpack(datagram)
    header_word_0 = int(words[0])
    pixels = words[RAW_V1_HEADER_WORDS:]
    if len(pixels) != RAW_V1_PIXEL_WORDS:
        raise RawV1AdapterError("RAW_V1_PIXEL_SHAPE_INVALID")
    if any(value == 0xFFFF for value in pixels):
        raise RawV1AdapterError("RAW_V1_INVALID_PIXEL_SENTINEL_0XFFFF")

    minimum = min(pixels)
    maximum = max(pixels)
    pixel_bytes_be = struct.pack(f"!{RAW_V1_PIXEL_WORDS}H", *pixels)
    logical_payload = THERMAL_META.pack(
        THERMAL_WIDTH,
        THERMAL_HEIGHT,
        sequence,
        uptime_ms,
        minimum,
        maximum,
    ) + pixel_bytes_be
    header = PacketHeader(PACKET_THERMAL_U16_BE, sequence, len(logical_payload))
    frame = decode_thermal(header, logical_payload)
    datagrams = tuple(encode_thermal_udp_frame(logical_payload, sequence))
    return RawV1Adaptation(
        frame=frame,
        logical_sntu_payload=logical_payload,
        sntu_datagrams=datagrams,
        received_at=received,
        adapted_at=adapted,
        age_seconds=age,
        evidence_id=contract.evidence_id,
        physical_unit_contract=contract.physical_unit_contract,
        orientation_contract=contract.orientation_contract,
        header_word_0_observed=header_word_0,
        celsius_minimum=minimum / 10.0 - 273.15,
        celsius_maximum=maximum / 10.0 - 273.15,
        logical_crc32=zlib.crc32(logical_payload) & 0xFFFFFFFF,
    )


def _uint32(value: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 0xFFFFFFFF:
        raise RawV1AdapterError(f"{field} must fit uint32")
    return value


def _timestamp(value: float, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise RawV1AdapterError(f"{field} must be a real number")
    converted = float(value)
    if not math.isfinite(converted) or converted < 0:
        raise RawV1AdapterError(f"{field} must be finite and non-negative")
    return converted
