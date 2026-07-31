#!/usr/bin/env python3
"""Export SafeNest MR60BHA2 JSONL logs as team-spec CSV per session.

Rules enforced from 한준우 spec (2026-07-25):
  - resp_phase 필드에는 ESP breath_phase 원값을 그대로 저장 (×100, Z-Score 등 금지)
  - 실제 측정 timestamp 보존 (재샘플링 금지)
  - 세션별 session_id 분리 (5분 인체 = 1 세션, 진입퇴장 10회 = 10 세션 개별)
  - 서로 다른 로그를 하나로 합치지 않음
  - presence=0 구간에 resp_phase=0을 임의 생성하지 않음
  - timestamp 중복/역행/NaN/Inf는 진단 리포트에 기록
  - 원본 파일과 CSV 사이 대응 관계는 매니페스트 JSON에 SHA256과 함께 저장

CSV 열: timestamp_s, resp_phase, subject_id, session_id, presence, label,
        breath_rpm, range_m, quality, signal_source, device_id
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CSV_HEADER = [
    "timestamp_s", "resp_phase", "subject_id", "session_id",
    "presence", "label", "breath_rpm", "range_m",
    "quality", "signal_source", "device_id",
]
SIGNAL_SOURCE = "MR60BHA2_breath_phase"
DEFAULT_SUBJECT = "S001"
DEFAULT_DEVICE = "safenest-node-01"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_bad_float(value: Any) -> bool:
    return isinstance(value, float) and (math.isnan(value) or math.isinf(value))


@dataclass
class SessionSpec:
    session_id: str
    label: str
    records: list[dict[str, Any]]
    origin_start_ms: int


def load_records(path: Path) -> list[dict[str, Any]]:
    sensor, beeps = [], []
    for line in path.open(encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        kind = item.get("kind")
        if kind == "beep":
            beeps.append(item)
        elif "seq" in item and item.get("ts_monotonic_ms") is not None:
            sensor.append(item)
    sensor.sort(key=lambda r: r["ts_monotonic_ms"])
    return sensor, beeps


def diagnostics(session: SessionSpec) -> dict[str, Any]:
    ts_ms = [r["ts_monotonic_ms"] for r in session.records]
    duplicates, backwards, bad_phase = [], [], []
    prev = None
    for idx, r in enumerate(session.records):
        t = r["ts_monotonic_ms"]
        if prev is not None:
            if t == prev:
                duplicates.append({"index": idx, "ts_ms": t})
            elif t < prev:
                backwards.append({"index": idx, "ts_ms": t, "prev_ms": prev})
        prev = t
        phase = r.get("breath_phase")
        if phase is None or is_bad_float(phase):
            bad_phase.append({"index": idx, "ts_ms": t, "value": phase})
    if len(ts_ms) < 2:
        rate = None
        max_gap = None
    else:
        gaps_ms = [b - a for a, b in zip(ts_ms, ts_ms[1:])]
        rate = 1000.0 / (sum(gaps_ms) / len(gaps_ms)) if gaps_ms else None
        max_gap = max(gaps_ms) if gaps_ms else None
    return {
        "session_id": session.session_id,
        "label": session.label,
        "records": len(session.records),
        "duration_s": (ts_ms[-1] - ts_ms[0]) / 1000.0 if len(ts_ms) >= 2 else None,
        "measured_rate_hz": rate,
        "max_gap_ms": max_gap,
        "timestamp_duplicates": duplicates,
        "timestamp_backwards": backwards,
        "bad_or_missing_phase": bad_phase,
    }


def write_csv(session: SessionSpec, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for r in session.records:
            t_s = (int(r["ts_monotonic_ms"]) - session.origin_start_ms) / 1000.0
            resp = r.get("breath_phase")
            presence_raw = r.get("human_detected_raw")
            if presence_raw is True:
                presence = 1
            elif presence_raw is False:
                presence = 0
            else:
                presence = ""
            breath = r.get("breath_rate_raw")
            breath_field = f"{breath:.2f}" if isinstance(breath, (int, float)) and breath > 0 else ""
            dist = r.get("distance_cm_raw")
            range_m = f"{dist / 100.0:.4f}" if isinstance(dist, (int, float)) and dist > 0 else ""
            resp_field = "" if (resp is None or is_bad_float(resp)) else f"{resp:.6f}"
            writer.writerow([
                f"{t_s:.4f}", resp_field, DEFAULT_SUBJECT, session.session_id,
                presence, session.label, breath_field, range_m,
                "", SIGNAL_SOURCE, r.get("device_id", DEFAULT_DEVICE),
            ])


def build_normal_session(sensor: list[dict[str, Any]], session_id: str,
                         warmup_seconds: float) -> SessionSpec:
    if not sensor:
        return SessionSpec(session_id, "NORMAL", [], 0)
    origin = int(sensor[0]["ts_monotonic_ms"])
    cutoff = origin + int(warmup_seconds * 1000)
    records = [r for r in sensor if int(r["ts_monotonic_ms"]) >= cutoff]
    if not records:
        return SessionSpec(session_id, "NORMAL", [], origin)
    return SessionSpec(session_id, "NORMAL", records, int(records[0]["ts_monotonic_ms"]))


def build_trial_sessions(sensor: list[dict[str, Any]],
                         beeps: list[dict[str, Any]]) -> list[SessionSpec]:
    enters = sorted([b for b in beeps if b.get("event") == "enter"],
                    key=lambda b: b["host_monotonic_ns"])
    if not enters:
        return []
    # Map host_monotonic_ns of enter beeps to nearest ESP ts_monotonic_ms
    # by scanning sensor records with host_monotonic_ns (present in trial log).
    def esp_ts_at(host_ns: int) -> int | None:
        best = None
        best_delta = None
        for r in sensor:
            host = r.get("host_monotonic_ns")
            if host is None:
                continue
            delta = abs(int(host) - int(host_ns))
            if best_delta is None or delta < best_delta:
                best_delta = delta
                best = int(r["ts_monotonic_ms"])
        return best

    enter_esp_ms = [esp_ts_at(b["host_monotonic_ns"]) for b in enters]
    sessions: list[SessionSpec] = []
    for i, enter_ms in enumerate(enter_esp_ms):
        if enter_ms is None:
            continue
        end_ms = enter_esp_ms[i + 1] if i + 1 < len(enter_esp_ms) else None
        trial_no = enters[i]["trial"]
        session_id = f"{DEFAULT_SUBJECT}_ENTRY_EXIT_{trial_no:02d}"
        records = [
            r for r in sensor
            if int(r["ts_monotonic_ms"]) >= enter_ms
            and (end_ms is None or int(r["ts_monotonic_ms"]) < end_ms)
        ]
        if not records:
            continue
        sessions.append(SessionSpec(session_id, "PRESENCE_TRANSITION",
                                    records, int(records[0]["ts_monotonic_ms"])))
    return sessions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--normal-jsonl", type=Path, required=True,
                        help="5-min stationary human log")
    parser.add_argument("--normal-warmup-s", type=float, default=60.0,
                        help="세션 앞의 워밍업/전이 초 (여기서부터 안정 기준선)")
    parser.add_argument("--normal-session-id", type=str,
                        default=f"{DEFAULT_SUBJECT}_NORMAL_5MIN_01")
    parser.add_argument("--trial-jsonl", type=Path, required=True,
                        help="Entry/exit trial log with beep markers")
    parser.add_argument("--out-dir", type=Path, required=True)
    args = parser.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "exported_at_iso": "2026-07-25",
        "signal_source": SIGNAL_SOURCE,
        "spec_reference": "han-junwoo mmwave csv 인수 조건 2026-07-25",
        "notes": {
            "resp_phase": "ESP breath_phase 원값. ×100, Z-Score, offset 제거 없음.",
            "timestamp_s": "세션 시작 시각을 0으로 리베이스한 초 단위. ESP ts_monotonic_ms 기반.",
            "presence_zero_policy": "presence=0 구간에 resp_phase 임의 생성 없음.",
            "class1": "RAPID_OR_ABNORMAL은 이 배치에 포함되지 않음.",
            "trial_split_rule": "enter 비프의 host_monotonic_ns를 센서 로그에 매핑하여 각 시도별 session_id 분리.",
        },
        "sources": [],
        "sessions": [],
        "diagnostics": [],
    }

    for label_name, jsonl_path in [("normal", args.normal_jsonl),
                                    ("trial", args.trial_jsonl)]:
        manifest["sources"].append({
            "role": label_name,
            "path": str(jsonl_path),
            "sha256": sha256_of(jsonl_path),
            "size_bytes": jsonl_path.stat().st_size,
        })

    normal_sensor, _ = load_records(args.normal_jsonl)
    normal_session = build_normal_session(
        normal_sensor, args.normal_session_id, args.normal_warmup_s
    )
    if normal_session.records:
        base = args.normal_jsonl.stem
        out_path = args.out_dir / f"{base}__{normal_session.session_id}.csv"
        write_csv(normal_session, out_path)
        manifest["sessions"].append({
            "session_id": normal_session.session_id,
            "label": normal_session.label,
            "records": len(normal_session.records),
            "csv_path": str(out_path),
            "csv_sha256": sha256_of(out_path),
            "origin_jsonl": str(args.normal_jsonl),
            "warmup_skipped_seconds": args.normal_warmup_s,
        })
        manifest["diagnostics"].append(diagnostics(normal_session))

    trial_sensor, trial_beeps = load_records(args.trial_jsonl)
    trial_sessions = build_trial_sessions(trial_sensor, trial_beeps)
    for session in trial_sessions:
        base = args.trial_jsonl.stem
        out_path = args.out_dir / f"{base}__{session.session_id}.csv"
        write_csv(session, out_path)
        manifest["sessions"].append({
            "session_id": session.session_id,
            "label": session.label,
            "records": len(session.records),
            "csv_path": str(out_path),
            "csv_sha256": sha256_of(out_path),
            "origin_jsonl": str(args.trial_jsonl),
        })
        manifest["diagnostics"].append(diagnostics(session))

    manifest_path = args.out_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"CSV 세션 수: {len(manifest['sessions'])}")
    print(f"매니페스트: {manifest_path}")


if __name__ == "__main__":
    main()
