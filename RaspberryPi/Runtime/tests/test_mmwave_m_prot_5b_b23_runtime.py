"""M-PROT-5B team-runtime B23 port tests (offline/replay only).

Goes through OnDeviceAIPipeline. No Raspberry Pi, no MR60, no live hardware.
"""

from __future__ import annotations

import hashlib
import math
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from ai.mmwave_b23_runtime import B23TeamRuntime, MODEL_ID
from ai.mmwave_prototype.mmwave_m_prot_2_b23_runtime import (
    CANONICAL_PARAMETER_SHA256,
    SCALER_CONTENT_SHA256,
    SOURCE_ARTIFACT_SHA256,
    TRACE_SAMPLES,
    verify_artifact,
    verify_scaler,
)
from ai.pipeline import OnDeviceAIPipeline
from ai.runtime import LazyModel, ModelRuntimeUnavailable
from gateway.protocol import PacketHeader, TelemetryPayload
from paths import ONDEVICE_AI_ROOT
from state.manager import SensorStateManager

PHYSIOLOGY_OK = {"PHYSIOLOGY_ELIGIBLE", "ABSENT", "QUALITY_SUPPRESSED", "RR_UNAVAILABLE"}
ART_REL = Path("models/mmwave/m_prot_b23/candidate_seed_23.pt")
SCALER_REL = Path("models/mmwave/m_prot_b23/scaler_statistics.json")


class FakeThermal:
    def predict(self, pixels):
        return SimpleNamespace(
            class_name="NO_HUMAN",
            probabilities=[0.99, 0.005, 0.005],
            confidence=0.99,
            latency_ms=1.0,
            model_id="thermal-fake",
            model_version="test",
        )


class CountingMN9:
    def __init__(self) -> None:
        self.calls = []

    def predict(self, tensor):
        self.calls.append(tensor)
        raise AssertionError("old M-N9 path must not be called")


def telemetry(
    index: int,
    *,
    rate: float = 10.0,
    presence: bool | None = True,
    session: str = "sess-a",
    phase=None,
    ts_monotonic_ms=None,
    phase_age_ms: float = 3.0,
    seq=None,
    device_id: str = "mprot5b-fixture",
    valid_respiration: bool = True,
) -> TelemetryPayload:
    dt_ms = 1000.0 / rate
    event_ms = float(index) * dt_ms
    ts = event_ms + phase_age_ms if ts_monotonic_ms is None else float(ts_monotonic_ms)
    t_s = (ts - phase_age_ms) / 1000.0
    if phase is None:
        phase = math.sin(2 * math.pi * 0.25 * t_s)
    sequence = index + 1 if seq is None else seq
    return TelemetryPayload(
        header=PacketHeader(1, sequence, 8),
        device_id=device_id,
        uptime_ms=int(ts) + 10,
        respiration_rate_bpm=16.0,
        heart_rate_bpm=62.0,
        co2_ppm=800.0,
        pir_motion=False,
        valid={"respiration": valid_respiration, "heart": True, "co2": True},
        boot_id="boot-a",
        breath_phase=phase,
        ts_monotonic_ms=ts,
        phase_age_ms=phase_age_ms,
        human_detected_raw=presence,
        session_id=session,
    )


def feed(
    pipeline: OnDeviceAIPipeline,
    manager: SensorStateManager,
    packet: TelemetryPayload,
    index: int,
    *,
    rate: float = 10.0,
) -> float:
    wall = 10_000.0 + index / rate
    pipeline.observe_telemetry(packet)
    manager.ingest(
        packet,
        ("127.0.0.1", 5000),
        received_at=wall,
        monotonic_at=wall,
    )
    return wall


def ready_count(rate: float = 10.0) -> int:
    return int(round(29.9 * rate)) + 1


class B23PipelinePathTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manager = SensorStateManager()
        self.mn9 = CountingMN9()
        self.pipeline = OnDeviceAIPipeline(
            self.manager,
            {"mmwave": self.mn9, "thermal": FakeThermal()},
        )
        self.now = 10_000.0

    def _evaluate(self):
        return self.pipeline.evaluate(
            self.manager.snapshot(now=self.now, monotonic_now=self.now)
        )["ai"]["mmwave"]

    def _feed(self, packet: TelemetryPayload, index: int, *, rate: float = 10.0) -> None:
        self.now = feed(self.pipeline, self.manager, packet, index, rate=rate)

    def _assert_not_mn9(self, result: dict) -> None:
        self.assertEqual(self.mn9.calls, [])
        self.assertNotEqual(result.get("source"), "tflite")
        self.assertNotIn(result.get("state"), {"NORMAL", "RAPID_OR_ABNORMAL", "APNEA", "APNEA-proxy"})
        self.assertFalse(result.get("metadata", {}).get("m_n9_fallback"))
        self.assertFalse(result.get("metadata", {}).get("spectral_fallback"))
        self.assertFalse(result.get("metadata", {}).get("vendor_rr_model_input"))

    def test_a_valid_10hz_through_team_pipeline(self) -> None:
        n = ready_count(10.0)
        result = {"available": False}
        for i in range(n):
            self._feed(telemetry(i, rate=10.0), i, rate=10.0)
            result = self._evaluate()
        self._assert_not_mn9(result)
        self.assertGreaterEqual(self.pipeline._mmwave_b23.buffered_count, 300)
        if result["available"]:
            self.assertEqual(result["source"], "pytorch")
            self.assertEqual(result["model_id"], MODEL_ID)
            self.assertEqual(result["metadata"]["r1_sample_count"], TRACE_SAMPLES)
            self.assertEqual(result["metadata"]["assembled_dim"], 621)
            self.assertEqual(result["metadata"]["artifact_sha256"], SOURCE_ARTIFACT_SHA256)
            self.assertTrue(result["metadata"]["risk_contribution_deferred"])
            self.assertEqual(result["score"], 0.0)
        else:
            self.assertIn(
                result["state"],
                PHYSIOLOGY_OK | {"WINDOW_NOT_READY", "QUALITY_SUPPRESSED", "RR_UNAVAILABLE"},
            )
        ready = self._evaluate()
        self.assertTrue(ready["metadata"].get("window_ready") or ready["state"] == "WINDOW_NOT_READY")
        if ready["metadata"].get("window_ready") and ready["metadata"].get("r1_sample_count"):
            self.assertEqual(ready["metadata"]["r1_sample_count"], 300)
            self.assertEqual(ready["metadata"]["assembled_dim"], 621)

    def test_b_valid_20hz_r1_downsamples(self) -> None:
        n = 600
        self.assertGreater(n, 300)
        for i in range(n):
            self._feed(telemetry(i, rate=20.0), i, rate=20.0)
        result = self._evaluate()
        self._assert_not_mn9(result)
        if result["metadata"].get("window_ready") and result["metadata"].get("r1_sample_count"):
            self.assertEqual(result["metadata"]["r1_sample_count"], 300)

    def test_c_multi_bundle_continued_observations(self) -> None:
        for i in range(ready_count(10.0)):
            self._feed(telemetry(i, rate=10.0), i, rate=10.0)
        first = self._evaluate()
        extra = ready_count(10.0)
        for i in range(extra, extra + 20):
            self._feed(telemetry(i, rate=10.0), i, rate=10.0)
        second = self._evaluate()
        self._assert_not_mn9(second)
        self.assertTrue(first["metadata"].get("window_ready") or first["state"] == "WINDOW_NOT_READY")
        self.assertTrue(second["metadata"].get("window_ready") or second["state"] == "WINDOW_NOT_READY")

    def test_d_warmup_before_30s(self) -> None:
        self._feed(telemetry(0), 0)
        result = self._evaluate()
        self.assertFalse(result["available"])
        self.assertEqual(result["state"], "WINDOW_NOT_READY")
        self._assert_not_mn9(result)

    def test_e_repeated_inference_after_ready(self) -> None:
        n = ready_count(10.0)
        for i in range(n):
            self._feed(telemetry(i), i)
        a = self._evaluate()
        self._feed(telemetry(n), n)
        b = self._evaluate()
        self._assert_not_mn9(b)
        if a["metadata"].get("r1_sample_count"):
            self.assertEqual(a["metadata"]["r1_sample_count"], 300)
        if b["metadata"].get("r1_sample_count"):
            self.assertEqual(b["metadata"]["r1_sample_count"], 300)

    def test_missing_phase_fail_closed(self) -> None:
        pkt = telemetry(0)
        object.__setattr__(pkt, "breath_phase", None)
        self._feed(pkt, 0)
        result = self._evaluate()
        self.assertFalse(result["available"])
        self.assertIsNotNone(result["error"])
        self._assert_not_mn9(result)

    def test_timestamp_regression_fail_closed(self) -> None:
        self._feed(telemetry(5, rate=10.0), 5, rate=10.0)
        self._feed(telemetry(1, rate=10.0, seq=6), 6, rate=10.0)
        result = self._evaluate()
        self.assertFalse(result["available"])
        self._assert_not_mn9(result)

    def test_sequence_gap_fail_closed(self) -> None:
        self._feed(telemetry(0, seq=1), 0)
        self._feed(telemetry(1, seq=5), 1)
        result = self._evaluate()
        self.assertFalse(result["available"])
        self._assert_not_mn9(result)

    def test_large_timestamp_gap_does_not_bridge(self) -> None:
        self._feed(telemetry(0, rate=10.0), 0, rate=10.0)
        late = telemetry(1, rate=10.0, seq=2)
        object.__setattr__(late, "ts_monotonic_ms", 3.0 + 2000.0)
        self._feed(late, 1, rate=10.0)
        result = self._evaluate()
        self.assertFalse(result["available"])
        self._assert_not_mn9(result)

    def test_session_transition_does_not_bridge(self) -> None:
        for i in range(50):
            self._feed(telemetry(i, session="A"), i)
        for i in range(50, 80):
            self._feed(telemetry(i, session="B"), i)
        result = self._evaluate()
        self.assertFalse(result["available"])
        self._assert_not_mn9(result)

    def test_presence_unavailable(self) -> None:
        for i in range(ready_count(10.0)):
            self._feed(telemetry(i, presence=None), i)
        result = self._evaluate()
        self.assertFalse(result["available"])
        if result["metadata"].get("window_ready"):
            self.assertEqual(result["state"], "PRESENCE_UNAVAILABLE")
        self.assertNotEqual(result["state"], "NORMAL")
        self.assertNotEqual(result["state"], "APNEA")
        self._assert_not_mn9(result)

    def test_presence_false(self) -> None:
        for i in range(ready_count(10.0)):
            self._feed(telemetry(i, presence=False), i)
        result = self._evaluate()
        self.assertFalse(result["available"])
        if result["metadata"].get("window_ready"):
            self.assertEqual(result["state"], "PRESENCE_FALSE")
        self.assertNotEqual(result["state"], "APNEA")
        self.assertNotEqual(result["state"], "APNEA-proxy")
        self._assert_not_mn9(result)

    def test_below_10hz_r1_rejects_without_mn9(self) -> None:
        n = ready_count(8.0)
        for i in range(n):
            self._feed(telemetry(i, rate=8.0), i, rate=8.0)
        result = self._evaluate()
        self._assert_not_mn9(result)
        self.assertFalse(result["available"])
        if result["metadata"].get("window_ready"):
            self.assertIn("SOURCE_RATE_BELOW_TARGET", str(result.get("error") or result.get("state") or ""))

    def test_vendor_rr_is_not_model_input(self) -> None:
        pkt = telemetry(0)
        object.__setattr__(pkt, "breath_phase", None)
        object.__setattr__(pkt, "respiration_rate_bpm", 18.0)
        self._feed(pkt, 0)
        result = self._evaluate()
        self.assertFalse(result["available"])
        self._assert_not_mn9(result)

    def test_old_mn9_predict_never_called_on_default_path(self) -> None:
        n = ready_count(10.0)
        for i in range(n):
            self._feed(telemetry(i), i)
        self._evaluate()
        self.assertEqual(self.mn9.calls, [])
        src = Path(__file__).resolve().parents[1] / "ai" / "pipeline.py"
        text = src.read_text(encoding="utf-8")
        self.assertNotIn("MR60CanonicalWindowBuilder", text)
        self.assertNotIn("estimate_respiration", text)
        self.assertNotIn('self.models["mmwave"].predict', text)

    def test_legacy_lazy_model_cannot_load_mn9_by_default(self) -> None:
        with self.assertRaises(ModelRuntimeUnavailable) as ctx:
            LazyModel("mmwave").predict([[0.0]])
        self.assertIn("MODEL_RELEASE_BLOCKED", str(ctx.exception))


class B23IdentityTests(unittest.TestCase):
    def test_frozen_identities(self) -> None:
        verify_artifact(ONDEVICE_AI_ROOT)
        verify_scaler(ONDEVICE_AI_ROOT)
        art = ONDEVICE_AI_ROOT / ART_REL
        self.assertEqual(hashlib.sha256(art.read_bytes()).hexdigest(), SOURCE_ARTIFACT_SHA256)
        self.assertEqual(CANONICAL_PARAMETER_SHA256, "6db949c242e25888dd20c3fc8e2305af03448aa229e3ca73e4159216a266d78e")
        self.assertEqual(SCALER_CONTENT_SHA256, "5a2583b5b5064be5480b0cf56f2a2c12d40a4a2d005eb087dc8e12106881159c")

    def test_wrong_artifact_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dest = root / ART_REL
            dest.parent.mkdir(parents=True)
            data = bytearray((ONDEVICE_AI_ROOT / ART_REL).read_bytes())
            data[0] ^= 0xFF
            dest.write_bytes(bytes(data))
            shutil.copy2(ONDEVICE_AI_ROOT / SCALER_REL, root / SCALER_REL)
            runtime = B23TeamRuntime(root=root)
            manager = SensorStateManager()
            pipeline = OnDeviceAIPipeline(manager, {"mmwave": CountingMN9()})
            pipeline._mmwave_b23 = runtime
            now = 10_000.0
            for i in range(ready_count(10.0)):
                now = feed(pipeline, manager, telemetry(i), i)
            result = pipeline.evaluate(manager.snapshot(now=now, monotonic_now=now))["ai"]["mmwave"]
            self.assertFalse(result["available"])
            self.assertNotEqual(result["state"], "PHYSIOLOGY_ELIGIBLE")
            self.assertNotEqual(result.get("source"), "tflite")

    def test_wrong_scaler_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ART_REL).parent.mkdir(parents=True)
            shutil.copy2(ONDEVICE_AI_ROOT / ART_REL, root / ART_REL)
            scaler = root / SCALER_REL
            text = (ONDEVICE_AI_ROOT / SCALER_REL).read_text()
            scaler.write_text(text.replace(SCALER_CONTENT_SHA256, "0" * 64))
            runtime = B23TeamRuntime(root=root)
            manager = SensorStateManager()
            pipeline = OnDeviceAIPipeline(manager)
            pipeline._mmwave_b23 = runtime
            now = 10_000.0
            for i in range(ready_count(10.0)):
                now = feed(pipeline, manager, telemetry(i), i)
            result = pipeline.evaluate(manager.snapshot(now=now, monotonic_now=now))["ai"]["mmwave"]
            self.assertFalse(result["available"])
            self.assertNotEqual(result["state"], "PHYSIOLOGY_ELIGIBLE")


if __name__ == "__main__":
    unittest.main()
