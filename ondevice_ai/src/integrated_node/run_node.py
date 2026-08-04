#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
integrated_node/run_node.py
SafeNest V4 On-Device AI Main Production Integrated Execution Node

Outputs structured JSON Lines stream on stdout for UI / Dashboard consumption.
"""

from __future__ import annotations
import sys
import time
import signal
import argparse
from pathlib import Path

from devices.thermal.src.mock_sensor import MockThermalSensor
from devices.thermal.src.thermal44_driver import Thermal44Sensor
from devices.mmwave.src.mock_sensor import MockMMWaveSensor
from devices.mmwave.src.mmwave_adapter import MMWaveSensorAdapter
from devices.co2.src.mock_sensor import MockCO2Sensor
from devices.co2.src.co2_adapter import CO2SensorAdapter
from devices.pir.src.mock_sensor import MockPIRSensor
from devices.pir.src.pir_adapter import PIRSensorAdapter

from ondevice_ai.src.risk.risk_engine import SafeNestRiskEngine
from ondevice_ai.src.inference.inference_result import SafeNestRiskOutput


class SafeNestIntegratedNode:
    def __init__(self, mode: str = "mock", project_root: str | Path | None = None):
        self.mode = mode
        self.project_root = Path(project_root) if project_root else Path(__file__).resolve().parents[2]
        self.running = False

        if self.mode == "real":
            self.sensors = {
                "thermal44": Thermal44Sensor(project_root=self.project_root),
                "mmwave": MMWaveSensorAdapter(project_root=self.project_root),
                "co2": CO2SensorAdapter(project_root=self.project_root),
                "pir": PIRSensorAdapter()
            }
        else:
            self.sensors = {
                "thermal44": MockThermalSensor(project_root=self.project_root),
                "mmwave": MockMMWaveSensor(project_root=self.project_root),
                "co2": MockCO2Sensor(project_root=self.project_root),
                "pir": MockPIRSensor()
            }

        self.risk_engine = SafeNestRiskEngine()

    def start(self) -> None:
        self.running = True
        for name, sensor in self.sensors.items():
            connected = sensor.connect()
            print(f"🔌 [{name.upper()}] Sensor connected: {connected}", file=sys.stderr)

    def step(self) -> SafeNestRiskOutput:
        now = time.time()
        results = {}
        for name, sensor in self.sensors.items():
            results[name] = sensor.read()

        output = self.risk_engine.evaluate(results, now=now)
        return output

    def run_loop(self, interval_sec: float = 0.5) -> None:
        self.start()
        print(f"🚀 SafeNest V4 On-Device AI Node Running [Mode: {self.mode.upper()}]", file=sys.stderr)
        try:
            while self.running:
                output = self.step()
                # Output structured JSON Lines stream to stdout for UI consumption
                sys.stdout.write(output.to_json() + "\n")
                sys.stdout.flush()
                time.sleep(interval_sec)
        except KeyboardInterrupt:
            print("\n⚠️ Interrupted by user. Shutting down...", file=sys.stderr)
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self.running = False
        for name, sensor in self.sensors.items():
            try:
                sensor.close()
                print(f"🔒 [{name.upper()}] Sensor closed safely.", file=sys.stderr)
            except Exception as e:
                print(f"⚠️ Error closing {name}: {e}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="SafeNest V4 On-Device AI Node Entrypoint")
    parser.add_argument("--mode", choices=["mock", "real"], default="mock", help="Execution mode (mock or real)")
    parser.add_argument("--interval", type=float, default=0.5, help="Loop interval in seconds")
    args = parser.parse_args()

    node = SafeNestIntegratedNode(mode=args.mode)

    def signal_handler(sig, frame):
        print(f"\nReceived signal {sig}. Stopping node...", file=sys.stderr)
        node.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    node.run_loop(interval_sec=args.interval)


if __name__ == "__main__":
    main()
