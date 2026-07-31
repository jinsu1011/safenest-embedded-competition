#!/usr/bin/env python3
"""Capture ESP JSONL output without modifying sensor records."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import serial


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", default="/dev/cu.usbserial-10")
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--duration", type=float, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--receipt-output", type=Path)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.receipt_output:
        args.receipt_output.parent.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + args.duration
    records = 0
    with serial.Serial(args.port, args.baud, timeout=0.2) as stream:
        stream.reset_input_buffer()
        # Opening can occur in the middle of a USB serial line. Discard only
        # that partial line; every subsequent sensor record is preserved.
        stream.readline()
        with args.output.open("wb") as output, (
            args.receipt_output.open("a", encoding="utf-8")
            if args.receipt_output
            else open("/dev/null", "w", encoding="utf-8")
        ) as receipts:
            while time.monotonic() < deadline:
                raw = stream.readline()
                if raw:
                    output.write(raw)
                    output.flush()
                    records += 1
                    if args.receipt_output:
                        try:
                            item = json.loads(raw)
                        except (UnicodeDecodeError, json.JSONDecodeError):
                            item = {}
                        receipts.write(
                            json.dumps(
                                {
                                    "kind": "telemetry",
                                    "host_monotonic_ns": time.monotonic_ns(),
                                    "seq": item.get("seq"),
                                    "esp_ts_monotonic_ms": item.get("ts_monotonic_ms"),
                                }
                            )
                            + "\n"
                        )
                        receipts.flush()
    print(f"captured_records={records} path={args.output}")


if __name__ == "__main__":
    main()
