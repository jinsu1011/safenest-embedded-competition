#!/usr/bin/env python3
"""SafeNest Pi field monitor — storage / AI input / link / risk / LCD (table view).

Read-only. Polls GET /health, /api/status, /api/state.

Examples (on Pi):
  python3 hil/pi_field_monitor.py
  python3 hil/pi_field_monitor.py --once
  python3 hil/pi_field_monitor.py --interval 3

Examples (from Mac):
  python3 hil/pi_field_monitor.py --base http://192.168.1.44:8000
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
import urllib.error
import urllib.request
from typing import Any


SENSORS = ("mmwave", "thermal", "co2", "pir")


def get_json(base: str, path: str, timeout: float) -> dict[str, Any]:
    url = base.rstrip("/") + path
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def cell(value: Any, width: int) -> str:
    text = "-" if value is None else str(value)
    if len(text) > width:
        text = text[: max(0, width - 1)] + "…"
    return text.ljust(width)


def table(headers: list[str], rows: list[list[Any]], widths: list[int] | None = None) -> str:
    if widths is None:
        widths = []
        for i, h in enumerate(headers):
            col = [str(h)] + [("-" if r[i] is None else str(r[i])) for r in rows]
            widths.append(min(28, max(len(c) for c in col)))
    sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    lines = [sep]
    lines.append("| " + " | ".join(cell(h, w) for h, w in zip(headers, widths)) + " |")
    lines.append(sep)
    for row in rows:
        lines.append("| " + " | ".join(cell(v, w) for v, w in zip(row, widths)) + " |")
    lines.append(sep)
    return "\n".join(lines)


def fmt_num(v: Any) -> str:
    if v is None:
        return "-"
    if isinstance(v, float):
        if abs(v) >= 100:
            return f"{v:.0f}"
        return f"{v:.2f}"
    return str(v)


def delta(curr: Any, prev: Any) -> str:
    if curr is None or prev is None:
        return "-"
    try:
        d = float(curr) - float(prev)
    except (TypeError, ValueError):
        return "-"
    if abs(d) < 1e-9:
        return "0"
    if d > 0:
        return f"+{fmt_num(d)}"
    return fmt_num(d)


def judge_flow(d: float | None, *, need_positive: bool = True) -> str:
    if d is None:
        return "?"
    if need_positive:
        return "YES" if d > 0 else "NO"
    return "OK" if d >= 0 else "DROP"


def sensor_block(status: dict[str, Any], name: str) -> dict[str, Any]:
    block = status.get(name)
    return block if isinstance(block, dict) else {}


def dig(mapping: Any, *keys: str, default: Any = None) -> Any:
    cur = mapping
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key, default)
    return cur


def snapshot(base: str, timeout: float) -> dict[str, Any]:
    health = get_json(base, "/health", timeout)
    status = get_json(base, "/api/status", timeout)
    try:
        state = get_json(base, "/api/state", timeout)
    except Exception:
        state = {}
    return {"t": time.time(), "health": health, "status": status, "state": state}


def render(curr: dict[str, Any], prev: dict[str, Any] | None, dt: float | None) -> str:
    h = curr["health"]
    s = curr["status"]
    lcd = curr.get("state") or {}
    rx = dig(h, "receiver", default={}) or {}
    th = dig(rx, "thermal_udp", default={}) or {}
    log = dig(rx, "sensor_logging", default={}) or {}
    db = dig(h, "database", default={}) or {}
    risk = dig(s, "risk", default={}) or {}

    prev_h = dig(prev or {}, "health", default={}) or {}
    prev_rx = dig(prev_h, "receiver", default={}) or {}
    prev_th = dig(prev_rx, "thermal_udp", default={}) or {}
    prev_log = dig(prev_rx, "sensor_logging", default={}) or {}
    prev_db = dig(prev_h, "database", default={}) or {}

    telem = rx.get("telemetry_packets")
    frames = th.get("completed_frames")
    written = dig(log, "written", default={}) or {}
    prev_written = dig(prev_log, "written", default={}) or {}
    snap_n = dig(db, "counts", "snapshots")
    event_n = dig(db, "counts", "events")

    d_telem = None if prev is None else (telem or 0) - (prev_rx.get("telemetry_packets") or 0)
    d_frames = None if prev is None else (frames or 0) - (prev_th.get("completed_frames") or 0)
    d_mm = None if prev is None else (written.get("mmwave") or 0) - (prev_written.get("mmwave") or 0)
    d_co2 = None if prev is None else (written.get("co2") or 0) - (prev_written.get("co2") or 0)
    d_thm = None if prev is None else (written.get("thermal") or 0) - (prev_written.get("thermal") or 0)
    d_snap = None if prev is None else (snap_n or 0) - (dig(prev_db, "counts", "snapshots") or 0)

    cols = shutil.get_terminal_size((100, 24)).columns
    title = "SafeNest field monitor"
    stamp = time.strftime("%Y-%m-%d %H:%M:%S")
    dt_s = f"{dt:.1f}s" if dt is not None else "-"

    lines: list[str] = []
    lines.append(f"{title}  |  {stamp}  |  Δ window {dt_s}  |  cols≈{cols}")
    lines.append("")

    # --- overview judgments ---
    lines.append("## Verdict")
    verdict_rows = [
        ["TCP telem flowing", judge_flow(d_telem), f"conn={rx.get('connections')} telem={telem} Δ={delta(telem, prev_rx.get('telemetry_packets'))}"],
        ["UDP thermal flowing", judge_flow(d_frames), f"frames={frames} Δ={delta(frames, prev_th.get('completed_frames'))}"],
        ["Storage mmWave write", judge_flow(d_mm), f"written={written.get('mmwave')} Δ={delta(written.get('mmwave'), prev_written.get('mmwave'))}"],
        ["Storage CO2 write", judge_flow(d_co2), f"written={written.get('co2')} Δ={delta(written.get('co2'), prev_written.get('co2'))}"],
        ["Storage thermal write", judge_flow(d_thm), f"written={written.get('thermal')} Δ={delta(written.get('thermal'), prev_written.get('thermal'))}"],
        ["DB snapshots grow", judge_flow(d_snap), f"snapshots={snap_n} events={event_n} Δsnap={delta(snap_n, dig(prev_db, 'counts', 'snapshots'))}"],
        ["Logging worker", "YES" if log.get("running") else "NO", f"enabled={log.get('enabled')} q={log.get('queue_size')}/{log.get('queue_capacity')} err={log.get('errors')}"],
    ]
    # AI input: any sensor not INPUT_UNAVAILABLE / BLOCKED with LIVE-ish status
    ai_ok = []
    ai_bad = []
    for name in SENSORS:
        ai = dig(sensor_block(s, name), "ai", default={}) or {}
        st = dig(sensor_block(s, name), "state", default={}) or {}
        ai_state = ai.get("state")
        sens = st.get("status")
        if sens in {"LIVE", "DEGRADED"} and ai_state not in {None, "INPUT_UNAVAILABLE"}:
            ai_ok.append(name)
        else:
            ai_bad.append(f"{name}:{sens}/{ai_state}")
    verdict_rows.append(
        [
            "AI has usable input",
            "YES" if ai_ok else "NO",
            ("ok=" + ",".join(ai_ok)) if ai_ok else ("fail=" + ",".join(ai_bad)),
        ]
    )
    verdict_rows.append(
        [
            "Risk formula",
            "YES" if risk.get("formula_id") == "SAFENEST_RISK_V1" else "NO",
            f"{risk.get('formula_id')} score={risk.get('risk_score')} level={risk.get('risk_level')} evid={risk.get('evidence_sufficient')}",
        ]
    )
    verdict_rows.append(
        [
            "LCD state",
            str(lcd.get("state") or "-").upper(),
            f"room={lcd.get('room')} rev={lcd.get('revision')}",
        ]
    )
    lines.append(table(["check", "ok?", "detail"], verdict_rows, [22, 5, min(70, max(40, cols - 40))]))
    lines.append("")

    # --- link / storage ---
    lines.append("## Link & storage")
    lines.append(
        table(
            ["metric", "now", "Δ", "note"],
            [
                ["system", f"{s.get('system')}/{s.get('system_health')}", "-", f"ready={h.get('ready')} offline={s.get('offline')}"],
                ["tcp:9000 conn", rx.get("connections"), delta(rx.get("connections"), prev_rx.get("connections")), f"disc={rx.get('disconnects')} gaps={rx.get('sequence_gaps')} proto_err={rx.get('protocol_errors')}"],
                ["telemetry pkts", telem, delta(telem, prev_rx.get("telemetry_packets")), f"thermal_tcp_unexpected={rx.get('unexpected_tcp_thermal_packets')}"],
                ["udp:5005 frames", frames, delta(frames, prev_th.get("completed_frames")), f"dgram={th.get('received_datagrams')} incomplete={th.get('incomplete_frames')} fps={fmt_num(th.get('effective_fps'))}"],
                ["log written mm", written.get("mmwave"), delta(written.get("mmwave"), prev_written.get("mmwave")), f"accepted={dig(log,'accepted','mmwave')} dropped={dig(log,'dropped','mmwave')}"],
                ["log written co2", written.get("co2"), delta(written.get("co2"), prev_written.get("co2")), f"accepted={dig(log,'accepted','co2')} dropped={dig(log,'dropped','co2')}"],
                ["log written thm", written.get("thermal"), delta(written.get("thermal"), prev_written.get("thermal")), f"accepted={dig(log,'accepted','thermal')} dropped={dig(log,'dropped','thermal')}"],
                ["db snapshots", snap_n, delta(snap_n, dig(prev_db, "counts", "snapshots")), f"path={db.get('path')}"],
                ["db events", event_n, delta(event_n, dig(prev_db, "counts", "events")), f"schema={db.get('schema_version')} avail={db.get('available')}"],
            ],
            [16, 14, 10, min(55, max(28, cols - 50))],
        )
    )
    lines.append("")

    # --- per-sensor / AI / risk / LCD ---
    lines.append("## Sensors / AI / risk component")
    sens_rows: list[list[Any]] = []
    for name in SENSORS:
        block = sensor_block(s, name)
        st = dig(block, "state", default={}) or {}
        ai = dig(block, "ai", default={}) or {}
        rc = dig(block, "risk_component", default={}) or {}
        rt = dig(block, "runtime_status", default={}) or dig(s, "runtime_status", "sensors", name, default={}) or {}
        vals = dig(st, "values", default={}) or {}
        meta = dig(ai, "metadata", default={}) or {}
        # compact value hint
        hint_bits = []
        for k in ("presence", "presence_available", "co2_ppm", "motion", "max_c", "human_detected_raw"):
            if k in vals and vals[k] is not None:
                hint_bits.append(f"{k}={vals[k]}")
        if meta.get("canonical_window_status"):
            hint_bits.append(f"canon={meta.get('canonical_window_status')}")
        if meta.get("spectral_status"):
            hint_bits.append(f"spec={meta.get('spectral_status')}")
        sens_rows.append(
            [
                name,
                st.get("status"),
                fmt_num(st.get("age_seconds") if st.get("age_seconds") is not None else st.get("age_s")),
                ai.get("state"),
                ai.get("error") or rt.get("blocked_reason") or "-",
                fmt_num(ai.get("score")),
                fmt_num(ai.get("latency_ms")),
                rc.get("state") or dig(risk, "component_status", name),
                fmt_num(rc.get("score") if rc.get("score") is not None else dig(risk, "component_scores", name)),
                ",".join(hint_bits) if hint_bits else "-",
            ]
        )
    lines.append(
        table(
            ["sensor", "status", "age_s", "ai_state", "ai_err", "ai_score", "ai_ms", "risk_st", "risk_sc", "values"],
            sens_rows,
            [7, 10, 6, 16, 16, 8, 6, 12, 8, min(36, max(16, cols - 100))],
        )
    )
    lines.append("")

    lines.append("## Risk / LCD (display)")
    lines.append(
        table(
            ["field", "value"],
            [
                ["formula_id", risk.get("formula_id")],
                ["formula_version", risk.get("formula_version")],
                ["risk_score / level", f"{risk.get('risk_score')} / {risk.get('risk_level')}"],
                ["effective_weight", risk.get("effective_weight")],
                ["evidence_sufficient", risk.get("evidence_sufficient")],
                ["presence", f"{risk.get('presence_detected')} ({risk.get('presence_source')})"],
                ["degraded_mode", risk.get("degraded_mode")],
                ["reasons", ",".join(risk.get("reasons") or []) or "-"],
                ["LCD state", lcd.get("state")],
                ["LCD room", lcd.get("room")],
                ["LCD revision", lcd.get("revision")],
                ["pub_revision", s.get("publication_revision") or h.get("publication_revision")],
            ],
            [20, min(70, max(40, cols - 28))],
        )
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="SafeNest Pi field monitor (tables)")
    parser.add_argument("--base", default="http://127.0.0.1:8000", help="API base URL")
    parser.add_argument("--interval", type=float, default=4.0, help="seconds between samples")
    parser.add_argument("--once", action="store_true", help="two samples then exit (still shows Δ)")
    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--no-clear", action="store_true")
    args = parser.parse_args()

    prev: dict[str, Any] | None = None
    try:
        while True:
            try:
                curr = snapshot(args.base, args.timeout)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
                print(f"[error] cannot fetch {args.base}: {exc}", file=sys.stderr)
                if args.once:
                    return 2
                time.sleep(args.interval)
                continue

            dt = None if prev is None else (curr["t"] - prev["t"])
            # need a previous sample for meaningful Δ; take one quiet sample first
            if prev is None:
                prev = curr
                if not args.no_clear:
                    print("\033[2J\033[H", end="")
                print(f"warming Δ sample against {args.base} …")
                time.sleep(args.interval)
                continue

            body = render(curr, prev, dt)
            if not args.no_clear:
                print("\033[2J\033[H", end="")
            print(body)
            prev = curr

            if args.once:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nstopped")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
