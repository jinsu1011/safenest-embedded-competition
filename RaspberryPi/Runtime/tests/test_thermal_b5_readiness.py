from __future__ import annotations

import struct
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import numpy as np

from ai.thermal_b5_candidate import (
    B5_INPUT_SCALE,
    B5_INPUT_SHAPE,
    B5_INPUT_ZERO_POINT,
    B5_OUTPUT_SCALE,
    B5_OUTPUT_SHAPE,
    B5_OUTPUT_ZERO_POINT,
    P1_PROFILE_ID,
    VERIFIED_ORIENTATION_ID,
    VERIFIED_PHYSICAL_UNIT_ID,
    ThermalB5CandidateError,
    ThermalB5CandidateModel,
)
from gateway.thermal_raw_v1_adapter import (
    MI48_0P1_KELVIN_CONTRACT,
    NATIVE_62X80_ORIENTATION_CONTRACT,
    RAW_V1_FRAME_BYTES,
    RAW_V1_HEADER_WORDS,
    RAW_V1_PIXEL_WORDS,
    RawV1AdapterError,
    RawV1EvidenceContract,
    adapt_exact_raw_v1_datagram,
)
from gateway.thermal_udp import ThermalUDPReassembler
from hil.thermal_b5_pi_benchmark import load_frames


def evidence_contract() -> RawV1EvidenceContract:
    return RawV1EvidenceContract(
        evidence_id="TEST_ONLY_VERIFIED_RAW_V1_FIXTURE",
        physical_unit_contract=MI48_0P1_KELVIN_CONTRACT,
        orientation_contract=NATIVE_62X80_ORIENTATION_CONTRACT,
        max_age_seconds=0.5,
    )


def raw_v1_frame(*, invalid_pixel: bool = False) -> tuple[bytes, list[int]]:
    header = [0x1234] + [0] * (RAW_V1_HEADER_WORDS - 1)
    pixels = [2930 + (index % 21) for index in range(RAW_V1_PIXEL_WORDS)]
    if invalid_pixel:
        pixels[17] = 0xFFFF
    words = header + pixels
    payload = struct.pack(f"<{len(words)}H", *words)
    assert len(payload) == RAW_V1_FRAME_BYTES
    return payload, pixels


class FakeInterpreter:
    def __init__(self) -> None:
        self.input_tensor = None
        self.allocated = False

    def allocate_tensors(self) -> None:
        self.allocated = True

    def get_input_details(self):
        return [{
            "index": 0,
            "shape": np.array(B5_INPUT_SHAPE),
            "dtype": np.int8,
            "quantization": (B5_INPUT_SCALE, B5_INPUT_ZERO_POINT),
        }]

    def get_output_details(self):
        return [{
            "index": 1,
            "shape": np.array(B5_OUTPUT_SHAPE),
            "dtype": np.int8,
            "quantization": (B5_OUTPUT_SCALE, B5_OUTPUT_ZERO_POINT),
        }]

    def set_tensor(self, index, value) -> None:
        assert index == 0
        self.input_tensor = np.asarray(value).copy()

    def invoke(self) -> None:
        if self.input_tensor is None:
            raise AssertionError("input tensor was not set")

    def get_tensor(self, index):
        assert index == 1
        return np.array([[-128, -128, 127]], dtype=np.int8)


class RawV1AdapterTests(unittest.TestCase):
    def test_exact_little_endian_frame_roundtrips_through_sntu_crc(self) -> None:
        raw, pixels = raw_v1_frame()
        adaptation = adapt_exact_raw_v1_datagram(
            raw,
            contract=evidence_contract(),
            bridge_sequence=7,
            bridge_uptime_ms=123,
            received_at=10.0,
            now=10.1,
        )
        self.assertEqual(adaptation.header_word_0_observed, 0x1234)
        first_two = struct.unpack("!HH", adaptation.frame.pixel_bytes[:4])
        self.assertEqual(list(first_two), pixels[:2])
        self.assertAlmostEqual(adaptation.celsius_minimum, min(pixels) / 10.0 - 273.15)
        self.assertAlmostEqual(adaptation.celsius_maximum, max(pixels) / 10.0 - 273.15)
        self.assertEqual(adaptation.audit_dict()["physical_conversion"], "C = raw / 10.0 - 273.15")
        self.assertEqual(
            adaptation.orientation_contract,
            VERIFIED_ORIENTATION_ID,
        )
        self.assertEqual(
            adaptation.physical_unit_contract,
            MI48_0P1_KELVIN_CONTRACT,
        )

        reassembler = ThermalUDPReassembler()
        reconstructed = None
        for datagram in reversed(adaptation.sntu_datagrams):
            frame = reassembler.accept(datagram, ("127.0.0.1", 5005))
            if frame is not None:
                reconstructed = frame
        self.assertIsNotNone(reconstructed)
        self.assertEqual(reconstructed, adaptation.frame)
        self.assertGreater(reassembler.snapshot()["out_of_order_chunks"], 0)

    def test_raw_v1_partial_or_blind_chunk_is_rejected(self) -> None:
        raw, _ = raw_v1_frame()
        with self.assertRaisesRegex(RawV1AdapterError, "RAW_V1_EXACT_FRAME_REQUIRED"):
            adapt_exact_raw_v1_datagram(
                raw[:1460],
                contract=evidence_contract(),
                bridge_sequence=1,
                bridge_uptime_ms=1,
                received_at=1.0,
                now=1.0,
            )

    def test_raw_v1_stale_frame_and_future_timestamp_are_rejected(self) -> None:
        raw, _ = raw_v1_frame()
        with self.assertRaisesRegex(RawV1AdapterError, "RAW_V1_STALE"):
            adapt_exact_raw_v1_datagram(
                raw,
                contract=evidence_contract(),
                bridge_sequence=1,
                bridge_uptime_ms=1,
                received_at=1.0,
                now=1.6,
            )
        with self.assertRaisesRegex(RawV1AdapterError, "RAW_V1_TIMESTAMP_FROM_FUTURE"):
            adapt_exact_raw_v1_datagram(
                raw,
                contract=evidence_contract(),
                bridge_sequence=1,
                bridge_uptime_ms=1,
                received_at=2.0,
                now=1.0,
            )

    def test_raw_v1_invalid_sentinel_is_rejected_before_sntu(self) -> None:
        raw, _ = raw_v1_frame(invalid_pixel=True)
        with self.assertRaisesRegex(RawV1AdapterError, "0XFFFF"):
            adapt_exact_raw_v1_datagram(
                raw,
                contract=evidence_contract(),
                bridge_sequence=1,
                bridge_uptime_ms=1,
                received_at=1.0,
                now=1.0,
            )

    def test_raw_v1_requires_explicit_unit_and_orientation_evidence(self) -> None:
        with self.assertRaisesRegex(ValueError, "physical-unit evidence"):
            RawV1EvidenceContract(
                evidence_id="UNVERIFIED",
                physical_unit_contract="UNKNOWN",
                orientation_contract=NATIVE_62X80_ORIENTATION_CONTRACT,
            )
        with self.assertRaisesRegex(ValueError, "orientation evidence"):
            RawV1EvidenceContract(
                evidence_id="UNVERIFIED",
                physical_unit_contract=MI48_0P1_KELVIN_CONTRACT,
                orientation_contract="UNKNOWN",
            )


class ThermalB5CandidateTests(unittest.TestCase):
    def model(
        self,
        orientation=VERIFIED_ORIENTATION_ID,
        physical_unit=VERIFIED_PHYSICAL_UNIT_ID,
    ):
        fake = FakeInterpreter()
        model = ThermalB5CandidateModel(
            orientation_contract=orientation,
            physical_unit_contract=physical_unit,
            interpreter_factory=lambda _path: fake,
        )
        return model, fake

    def test_candidate_uses_celsius_p1_int8_and_emits_identity(self) -> None:
        model, fake = self.model()
        prediction = model.predict(np.full((62, 80), 2950, dtype=np.uint16))
        self.assertEqual(fake.input_tensor.shape, B5_INPUT_SHAPE)
        self.assertEqual(fake.input_tensor.dtype, np.int8)
        self.assertEqual(prediction.class_name, "HUMAN_FALL")
        self.assertEqual(prediction.metadata["preprocessing_identity"], P1_PROFILE_ID)
        self.assertFalse(prediction.metadata["production_selected"])
        self.assertEqual(prediction.metadata["orientation_transform"], "NONE")
        self.assertAlmostEqual(prediction.metadata["celsius_minimum"], 21.85)

    def test_candidate_rejects_unverified_orientation(self) -> None:
        model, _ = self.model(orientation=None)
        with self.assertRaisesRegex(ThermalB5CandidateError, "ORIENTATION_NOT_VERIFIED"):
            model.predict(np.full((62, 80), 2950, dtype=np.uint16))
        model, _ = self.model(physical_unit=None)
        with self.assertRaisesRegex(ThermalB5CandidateError, "PHYSICAL_UNIT_NOT_VERIFIED"):
            model.predict(np.full((62, 80), 2950, dtype=np.uint16))

    def test_candidate_rejects_invalid_pixel_before_invoke(self) -> None:
        model, fake = self.model()
        frame = np.full((62, 80), 2950, dtype=np.uint16)
        frame[0, 0] = 0xFFFF
        with self.assertRaisesRegex(ThermalB5CandidateError, "0XFFFF"):
            model.predict(frame)
        self.assertIsNone(fake.input_tensor)

    def test_candidate_rejects_non_numeric_input_before_invoke(self) -> None:
        model, fake = self.model()
        with self.assertRaisesRegex(ThermalB5CandidateError, "numeric uint16"):
            model.predict(np.full((62, 80), "bad", dtype="U3"))
        self.assertIsNone(fake.input_tensor)


class ThermalB5PiBenchmarkInputTests(unittest.TestCase):
    def test_benchmark_npz_contract_loads(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "frames.npz"
            np.savez(
                path,
                frames=np.full((2, 62, 80), 2950, dtype=np.uint16),
                timestamps=np.array([100.0, 100.1], dtype=np.float64),
                frame_sequences=np.array([1, 2], dtype=np.uint32),
            )
            rows = load_frames([path])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1]["frame_sequence"], 2)

    def test_benchmark_npz_rejects_nonfinite_timestamp(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "frames.npz"
            np.savez(
                path,
                frames=np.full((1, 62, 80), 2950, dtype=np.uint16),
                timestamps=np.array([np.nan], dtype=np.float64),
                frame_sequences=np.array([1], dtype=np.uint32),
            )
            with self.assertRaisesRegex(ValueError, "finite and non-negative"):
                load_frames([path])


if __name__ == "__main__":
    unittest.main()
