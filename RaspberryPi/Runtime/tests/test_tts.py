from __future__ import annotations

from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest import mock

from backend.runtime import SafeNestRuntime
from backend.store import RuntimeStore
from services.tts import (
    AsyncRiskTTS,
    SpeechInterrupted,
    effective_risk_level,
    message_for_publication,
)
from storage.sensor_logger import SensorStorageConfig


def publication(
    level: str | None,
    *,
    reasons: tuple[str, ...] = (),
    floors: tuple[str, ...] = (),
    emergency_active: bool = False,
) -> dict[str, object]:
    return {
        "risk": {
            "risk_level": level,
            "reasons": reasons,
            "escalation_floors": floors,
        },
        "emergency": {"active": emergency_active},
    }


class MutableClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


class FakeSpeechBackend:
    def __init__(self, *, block_warning: bool = False) -> None:
        self.block_warning = block_warning
        self.started: list[tuple[str, str]] = []
        self.warning_started = threading.Event()
        self.interrupt_calls = 0
        self._condition = threading.Condition()

    def speak(self, text: str, level: str, cancel_event: threading.Event) -> None:
        with self._condition:
            self.started.append((level, text))
            self._condition.notify_all()
        if level == "WARNING" and self.block_warning:
            self.warning_started.set()
            if cancel_event.wait(1.0):
                raise SpeechInterrupted()

    def interrupt(self) -> None:
        self.interrupt_calls += 1

    def status(self):
        return {"engine": "fake", "audio_device": "fake"}

    def wait_for_count(self, count: int, timeout: float = 1.0) -> bool:
        deadline = time.monotonic() + timeout
        with self._condition:
            while len(self.started) < count:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._condition.wait(remaining)
            return True


class RiskAwareTTSTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = MutableClock()
        self.backend = FakeSpeechBackend()
        self.tts = AsyncRiskTTS(
            self.backend,
            warning_cooldown_seconds=60.0,
            danger_cooldown_seconds=30.0,
            clock=self.clock,
        )
        self.tts.start()

    def tearDown(self) -> None:
        self.tts.close()

    def test_normal_warning_duplicate_and_warning_cooldown(self) -> None:
        self.assertFalse(self.tts.handle_publication(publication("NORMAL")))
        self.assertTrue(self.tts.handle_publication(publication("WARNING")))
        self.assertTrue(self.backend.wait_for_count(1))
        self.assertFalse(self.tts.handle_publication(publication("WARNING")))
        self.assertEqual([item[0] for item in self.backend.started], ["WARNING"])

        self.clock.now = 60.0
        self.assertTrue(self.tts.handle_publication(publication("WARNING")))
        self.assertTrue(self.backend.wait_for_count(2))

    def test_warning_to_danger_interrupts_and_supersedes(self) -> None:
        self.tts.close()
        backend = FakeSpeechBackend(block_warning=True)
        self.tts = AsyncRiskTTS(backend, clock=self.clock)
        self.tts.start()
        self.assertTrue(self.tts.handle_publication(publication("WARNING")))
        self.assertTrue(backend.warning_started.wait(1.0))

        self.assertTrue(self.tts.handle_publication(publication("DANGER")))
        self.assertTrue(backend.wait_for_count(2))
        self.assertEqual([item[0] for item in backend.started], ["WARNING", "DANGER"])
        self.assertEqual(backend.interrupt_calls, 1)

    def test_danger_duplicate_reminder_and_normal_clear(self) -> None:
        self.assertTrue(self.tts.handle_publication(publication("DANGER")))
        self.assertTrue(self.backend.wait_for_count(1))
        self.assertFalse(self.tts.handle_publication(publication("DANGER")))
        self.clock.now = 30.0
        self.assertTrue(self.tts.handle_publication(publication("DANGER")))
        self.assertTrue(self.backend.wait_for_count(2))

        self.assertFalse(self.tts.handle_publication(publication("NORMAL")))
        self.assertEqual(self.tts.status()["effective_level"], "NORMAL")

    def test_indeterminate_is_silent_and_latched_emergency_remains_danger(self) -> None:
        self.assertFalse(self.tts.handle_publication(publication("INDETERMINATE")))
        self.assertEqual(self.backend.started, [])

        latched = publication(None, emergency_active=True)
        self.assertEqual(effective_risk_level(latched), "DANGER")
        self.assertTrue(self.tts.handle_publication(latched))
        self.assertTrue(self.backend.wait_for_count(1))
        self.assertFalse(self.tts.handle_publication(latched))
        self.assertNotIn("안전", self.backend.started[0][1])

    def test_existing_reason_taxonomy_selects_specific_messages(self) -> None:
        fall = publication(
            "DANGER", floors=("thermal_fall_confident",), emergency_active=True
        )
        apnea = publication(
            "DANGER", floors=("mmwave_apnea_hardware_verified",), emergency_active=True
        )
        co2 = publication("DANGER", reasons=("CO2_IMMEDIATE_DANGER",))
        respiration = publication("WARNING", reasons=("ABNORMAL_RESPIRATION_RPM",))
        self.assertIn("낙상", message_for_publication(fall, "DANGER"))
        self.assertIn("호흡 이상", message_for_publication(apnea, "DANGER"))
        self.assertIn("이산화탄소", message_for_publication(co2, "DANGER"))
        self.assertIn("호흡 이상", message_for_publication(respiration, "WARNING"))


class ExplodingTTS:
    def start(self) -> None:
        return None

    def handle_publication(self, _publication) -> bool:
        raise RuntimeError("injected TTS failure")

    def status(self):
        return {"mode": "test"}

    def close(self) -> None:
        return None


class ExplodingStartTTS(ExplodingTTS):
    def start(self) -> None:
        raise RuntimeError("injected TTS initialization failure")

    def handle_publication(self, _publication) -> bool:
        return False


class RuntimeTTSIsolationTests(unittest.TestCase):
    def test_tts_failure_does_not_prevent_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = RuntimeStore()
            runtime = SafeNestRuntime(
                sensor_port=0,
                store=store,
                storage_config=SensorStorageConfig(
                    root=Path(temporary),
                    enabled=False,
                ),
                tts=ExplodingTTS(),
            )
            result = runtime.evaluate_once()

        self.assertEqual(result["publication_revision"], 1)
        self.assertTrue(store.diagnostics()["ready"])
        self.assertEqual(
            store.diagnostics()["last_error"]["details"]["source"],
            "tts",
        )

    def test_tts_start_failure_does_not_prevent_runtime_start(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            store = RuntimeStore()
            runtime = SafeNestRuntime(
                sensor_host="127.0.0.1",
                sensor_port=0,
                thermal_udp_host="127.0.0.1",
                thermal_udp_port=0,
                store=store,
                storage_config=SensorStorageConfig(
                    root=Path(temporary),
                    enabled=False,
                ),
                tts=ExplodingStartTTS(),
            )
            with (
                mock.patch.object(runtime.server, "serve_forever"),
                mock.patch.object(runtime.server, "stop"),
                mock.patch.object(runtime.thermal_udp_server, "serve_forever"),
                mock.patch.object(runtime.thermal_udp_server, "stop"),
            ):
                runtime.start()
                try:
                    self.assertTrue(store.diagnostics()["ready"])
                    self.assertTrue(runtime.receiver_stats()["runtime_started"])
                finally:
                    runtime.stop()


if __name__ == "__main__":
    unittest.main()
