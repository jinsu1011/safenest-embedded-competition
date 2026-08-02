#!/usr/bin/env python3
"""Bridge ESP MR60 JSONL directly into the SafeNest integration risk engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Iterator

if __package__ in (None, ""):
    project_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(project_root))

from src.sensors.mmwave.mr60_esp_adapter import MR60ESPAdapter
from src.integrated_node.safenest_risk_engine import SafeNestRiskEngine


class MR60IntegratedPipeline:
    """Own the raw ESP adapter and integration-node buffer as one pipeline."""

    def __init__(self, *, config_path: str | Path | None = None,
                 strict_provenance: bool = True,
                 risk_engine: SafeNestRiskEngine | None = None) -> None:
        self.adapter = MR60ESPAdapter(config_path, strict_provenance=strict_provenance)
        self.risk_engine = risk_engine or SafeNestRiskEngine()

    def process_line(self, line: str) -> dict:
        packet = self.adapter.process_json_line(line)
        return self._integrate(packet)

    def process_timeout(self) -> dict:
        return self._integrate(self.adapter.timeout_packet())

    def _integrate(self, packet: dict) -> dict:
        result = self.risk_engine.evaluate_risk(packet)
        mmwave = packet["mmwave_mr60"]
        derived = result.get("derived_metrics", {})
        return {
            "timestamp_s": packet.get("timestamp_s"),
            "mmwave_mr60": mmwave,
            "integration": {
                "received": True,
                "system_status": result.get("system_status"),
                "mmwave_status": "OK" if mmwave.get("valid") is True else "DEGRADED",
                "risk_status": result.get("status_str"),
                "buffer_samples": derived.get("mmwave_window_samples", 0),
                "buffer_ready": derived.get("mmwave_window_ready", False),
                "safety": {
                    "state": mmwave.get("state"),
                    "valid": mmwave.get("valid") is True,
                    "communication_valid": mmwave.get("communication_valid") is True,
                    "fault_reason": mmwave.get("fault_reason"),
                    "heart_verified": mmwave.get("heart_verified") is True,
                    "apnea_verified": mmwave.get("apnea_verified") is True,
                },
            },
            "risk_result": result,
        }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--port", help="ESP serial port, e.g. /dev/ttyUSB0")
    source.add_argument("--replay", type=Path, help="Recorded ESP JSONL")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--timeout", type=float, default=2.0)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--max-records", type=int, help="Stop after this many emitted records")
    parser.add_argument("--allow-legacy-provenance", action="store_true")
    return parser.parse_args()


def replay_lines(path: Path) -> Iterator[str | None]:
    with path.open(encoding="utf-8") as stream:
        yield from stream


def serial_lines(port: str, baud: int, timeout: float) -> Iterator[str | None]:
    try:
        import serial
    except ImportError as exc:
        raise SystemExit("pyserial is required for --port: pip install pyserial") from exc
    with serial.Serial(port, baudrate=baud, timeout=timeout) as stream:
        while True:
            raw = stream.readline()
            yield raw.decode("utf-8", errors="replace") if raw else None


def main() -> int:
    args = parse_args()
    pipeline = MR60IntegratedPipeline(
        config_path=args.config,
        strict_provenance=not args.allow_legacy_provenance,
    )
    lines = (
        serial_lines(args.port, args.baud, args.timeout)
        if args.port else replay_lines(args.replay)
    )
    emitted = 0
    for line in lines:
        output = pipeline.process_line(line) if line is not None else pipeline.process_timeout()
        print(json.dumps(output, ensure_ascii=False, separators=(",", ":")), flush=True)
        emitted += 1
        if args.max_records is not None and emitted >= args.max_records:
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
