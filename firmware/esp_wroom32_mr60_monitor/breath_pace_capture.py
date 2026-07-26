#!/usr/bin/env python3
"""SafeNest paced-breathing capture for KPI breath accuracy (±2 rpm).

Announces inhale cues at a fixed breath-per-minute (BPM) rate while streaming
ESP telemetry to a unified JSONL log. Beep and voice cues are logged with
host_monotonic_ns timestamps so offline analysis can compare user pacing to
sensor breath_rate_raw + breath_phase.

Safety: no breath-hold or hyperventilation requested. Subject follows a
comfortable pace guided by 'Yuna' Korean voice. If uncomfortable, stop.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import threading
import time
from pathlib import Path

import serial


VOICE = "Yuna"


def say_async(text: str) -> None:
    subprocess.Popen(["say", "-v", VOICE, text])


def say_blocking(text: str) -> None:
    subprocess.run(["say", "-v", VOICE, text])


def play_sound(path: str) -> None:
    subprocess.Popen(["afplay", path])


def sensor_reader(ser: serial.Serial, out_file, stop_event: threading.Event) -> None:
    ser.reset_input_buffer()
    ser.readline()
    while not stop_event.is_set():
        raw = ser.readline()
        if not raw:
            continue
        host_ns = time.monotonic_ns()
        try:
            item = json.loads(raw.decode("utf-8", errors="strict").strip())
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        if "seq" not in item:
            continue
        item["kind"] = "sensor"
        item["host_monotonic_ns"] = host_ns
        out_file.write(json.dumps(item, ensure_ascii=False) + "\n")
        out_file.flush()


def log_cue(out_file, event: str, cycle: int, target_bpm: int) -> None:
    entry = {
        "kind": "cue", "event": event, "cycle": cycle,
        "target_bpm": target_bpm,
        "host_monotonic_ns": time.monotonic_ns(),
    }
    out_file.write(json.dumps(entry, ensure_ascii=False) + "\n")
    out_file.flush()


def countdown(seconds: int) -> None:
    for s in range(seconds, 0, -1):
        say_async(f"{s}초")
        time.sleep(1.0)


def pace_loop(out_file, target_bpm: int, pace_seconds: float) -> None:
    period = 60.0 / target_bpm
    cycle = 0
    start = time.monotonic()
    deadline = start + pace_seconds
    while True:
        now = time.monotonic()
        if now >= deadline:
            break
        cycle += 1
        log_cue(out_file, "inhale", cycle, target_bpm)
        play_sound("/System/Library/Sounds/Tink.aiff")
        # Sleep until next cycle onset
        next_time = start + cycle * period
        remaining = next_time - time.monotonic()
        if remaining > 0:
            time.sleep(remaining)


def run(port: str, baud: int, target_bpm: int, pace_seconds: float,
        warmup_seconds: float, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with serial.Serial(port, baud, timeout=0.2) as ser, output.open("w", encoding="utf-8") as out:
        stop = threading.Event()
        reader = threading.Thread(target=sensor_reader, args=(ser, out, stop), daemon=True)
        reader.start()

        time.sleep(2.0)
        play_sound("/System/Library/Sounds/Glass.aiff")
        say_blocking(
            f"메트로놈 분당 {target_bpm}회 호흡 시험을 시작합니다. "
            f"신호에 맞춰 편안하게 호흡하세요. 억지로 참지 마세요. 준비하세요."
        )
        countdown(5)

        # Optional warmup with pacing so subject can settle
        if warmup_seconds > 0:
            say_blocking("워밍업. 신호에 맞춰 호흡하세요")
            pace_loop(out, target_bpm, warmup_seconds)

        play_sound("/System/Library/Sounds/Ping.aiff")
        say_blocking(f"측정 시작. {int(pace_seconds)}초간 진행합니다.")
        pace_loop(out, target_bpm, pace_seconds)

        play_sound("/System/Library/Sounds/Hero.aiff")
        say_blocking(f"분당 {target_bpm}회 캡처가 완료되었습니다. 잠시 편하게 쉬세요.")

        stop.set()
        reader.join(timeout=2.0)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True)
    parser.add_argument("--baud", type=int, default=115200)
    parser.add_argument("--bpm", type=int, required=True,
                        help="Target breaths per minute (12, 15, 20 etc.)")
    parser.add_argument("--seconds", type=float, default=180.0,
                        help="Measurement duration after warmup")
    parser.add_argument("--warmup", type=float, default=30.0,
                        help="Warmup seconds where pacing is on but data will be skipped in analysis")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.port, args.baud, args.bpm, args.seconds, args.warmup, args.output)


if __name__ == "__main__":
    main()
