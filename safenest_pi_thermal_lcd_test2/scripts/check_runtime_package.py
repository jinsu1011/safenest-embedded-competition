#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED = (
    "README.md",
    "run_safenest.sh",
    "ESP32/Arduino/esp32_sensor_node/esp32_sensor_node.ino",
    "ESP32/Arduino/esp32_sensor_node/ESP32_UPDATE_CHANGELOG_KO.md",
    "ESP32/secret.h.example",
    "RaspberryPi/Runtime/backend/run_backend.py",
    "RaspberryPi/Runtime/backend/app.py",
    "RaspberryPi/Runtime/backend/thermal_image.py",
    "RaspberryPi/Runtime/docs/WEB_THERMAL_RUNBOOK_KO.md",
    "RaspberryPi/LCD/static/display.html",
    "RaspberryPi/Web/index.html",
    "RaspberryPi/Web/portal/preview.html",
    "RaspberryPi/Web/portal/thermal-client.js",
    "RaspberryPi/Web/guest/index.html",
    "RaspberryPi/Ondevice_AI/models/model_manifest.json",
)

def main() -> int:
    missing = [path for path in REQUIRED if not (ROOT / path).is_file()]
    manifest = json.loads((ROOT / "RaspberryPi/Ondevice_AI/models/model_manifest.json").read_text(encoding="utf-8"))
    model_root = ROOT / "RaspberryPi/Ondevice_AI"
    models = []
    for key, entry in manifest["models"].items():
        path = model_root / entry["path"]
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        models.append({"key": key, "path": str(path.relative_to(ROOT)), "match": actual == entry.get("sha256")})
    result = {"ok": not missing and bool(models) and all(item["match"] for item in models), "missing": missing, "models": models}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
