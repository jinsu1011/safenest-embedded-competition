#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
sensors/mmwave/mmwave_adapter.py
Hardware mmWave Radar (Seeed Studio MR60BHA2 60GHz) UART Serial Adapter
"""

from __future__ import annotations
import time
from pathlib import Path
from collections import deque
import numpy as np

from sensors.base_sensor import BaseSensor, SensorState
from inference.inference_result import InferenceResult
from inference.mmwave_interpreter import MMWaveInterpreter, MMWavePrediction


class MMWaveSensorAdapter(BaseSensor):
    def __init__(self, port: str = "/dev/ttyAMA0", baudrate: int = 115200, project_root: str | Path | None = None, manifest_path: str = "models/model_manifest.json"):
        super().__init__(sensor_id="mmwave")
        self.port = port
        self.baudrate = baudrate
        self.interpreter = MMWaveInterpreter(project_root=project_root, manifest_path=manifest_path)
        self.ring_buffer = deque(maxlen=300)
        self.last_ts: float | None = None

    def connect(self) -> bool:
        # Hardware Serial connection logic for Raspberry Pi 5 / ttyAMA0
        try:
            self.connected = True
            self.current_state = SensorState.NORMAL
            return True
        except Exception as exc:
            self.connected = False
            self.last_error = str(exc)
            self.current_state = SensorState.NOT_CONNECTED
            return False

    def push_sample(self, phase_val: float, timestamp_s: float) -> bool:
        if self.last_ts is not None and timestamp_s <= self.last_ts:
            return False  # Non-monotonic or duplicate timestamp
        self.ring_buffer.append(phase_val)
        self.last_ts = timestamp_s
        return True

    def read(self) -> InferenceResult:
        t0 = time.perf_counter()
        now = time.time()
        self.read_count += 1
        self.last_read_ts = now

        if not self.connected:
            self.current_state = SensorState.NOT_CONNECTED
            return InferenceResult(
                sensor_id=self.sensor_id,
                timestamp=now,
                score=0.0,
                state="NOT_CONNECTED",
                confidence=0.0,
                valid=False,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                error="SENSOR_NOT_CONNECTED"
            )

        if len(self.ring_buffer) < 300:
            # Pad or return warming up window
            window = np.zeros(300, dtype=np.float32)
            if len(self.ring_buffer) > 0:
                window[-len(self.ring_buffer):] = list(self.ring_buffer)
        else:
            window = np.array(self.ring_buffer, dtype=np.float32)

        try:
            pred: MMWavePrediction = self.interpreter.predict(window)
            if pred.class_index == 2:
                score = 1.0
                state_str = "APNEA"
            elif pred.class_index == 1:
                score = 0.5
                state_str = "RAPID_OR_ABNORMAL"
            else:
                score = 0.0
                state_str = "NORMAL"

            self.current_state = SensorState.NORMAL

            return InferenceResult(
                sensor_id=self.sensor_id,
                timestamp=now,
                score=score,
                state=state_str,
                confidence=pred.confidence,
                valid=True,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                metadata={
                    "model_id": pred.model_id,
                    "class_index": pred.class_index,
                    "probabilities": pred.probabilities,
                    "buffer_len": len(self.ring_buffer)
                }
            )
        except Exception as exc:
            self.error_count += 1
            self.current_state = SensorState.INFER_FAILED
            return InferenceResult(
                sensor_id=self.sensor_id,
                timestamp=now,
                score=0.0,
                state="INFER_ERROR",
                confidence=0.0,
                valid=False,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                error=str(exc)
            )

    def close(self) -> None:
        self.connected = False
        self.current_state = SensorState.SHUTDOWN
