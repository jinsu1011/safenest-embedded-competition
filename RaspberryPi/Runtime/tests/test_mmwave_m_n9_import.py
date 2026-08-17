"""Team-repo overlay checks for the M-N9 mmWave INT8 import.

Does not rewire the live pipeline. Historical models.mmwave stays blocked.
"""

from __future__ import annotations

import hashlib
import json
import sys
import unittest
from pathlib import Path

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
if str(RUNTIME_ROOT) not in sys.path:
    sys.path.insert(0, str(RUNTIME_ROOT))

from paths import MODEL_MANIFEST, ONDEVICE_AI_ROOT, REPOSITORY_ROOT  # noqa: E402

EXPECTED_SHA = "3b008af4be0facc4037c2afd3fe39292fb794208eb4370dbe6916b2d15aa38a4"
SOURCE_SHA = "390f3be3d75987a79a0e0438ba8a9d5e9e19dc97"
BASE_ONDEVICE_SHA = "4129753e64e0f18a3491e5b6cc0454b0d36f1610"


class TestMmwaveMN9TeamImport(unittest.TestCase):
    def test_artifact_is_under_canonical_ondevice_ai_root(self) -> None:
        artifact = ONDEVICE_AI_ROOT / "models/mmwave/m_n9/MMWAVE_M_N9_FULL_INT8_V1.tflite"
        self.assertTrue(artifact.is_file())
        self.assertEqual(hashlib.sha256(artifact.read_bytes()).hexdigest(), EXPECTED_SHA)
        self.assertFalse((REPOSITORY_ROOT / "ondevice_ai").exists())

    def test_component_sources_records_overlay_without_rewriting_base_sha(self) -> None:
        payload = json.loads((REPOSITORY_ROOT / "COMPONENT_SOURCES.json").read_text(encoding="utf-8"))
        component = payload["components"]["ondevice_ai"]
        self.assertEqual(component["upstream_commit"], BASE_ONDEVICE_SHA)
        self.assertEqual(component["integration_path"], "RaspberryPi/Ondevice_AI")
        overlays = component["overlays"]
        self.assertEqual(len(overlays), 1)
        overlay = overlays[0]
        self.assertEqual(overlay["name"], "mmwave_m_n9_full_int8")
        self.assertEqual(overlay["upstream_commit"], SOURCE_SHA)
        self.assertFalse(overlay["runtime_promoted"])
        self.assertIn("mmwave_m_n9_full_int8", payload["model_promotion_policy"])
        self.assertIs(payload["model_promotion_policy"]["automatic_promotion_performed"], False)

    def test_runtime_default_mmwave_remains_blocked(self) -> None:
        manifest = json.loads(MODEL_MANIFEST.read_text(encoding="utf-8"))
        self.assertIs(manifest["models"]["mmwave"]["deployment_allowed"], False)
        self.assertEqual(
            manifest["models"]["mmwave"]["block_reason"],
            "CLASS_COLLAPSE_ON_REPOSITORY_NPZ",
        )
        self.assertFalse(manifest["mmwave_active_locked_artifact"]["runtime_wired"])
        locked = manifest["models"]["mmwave_m_n9"]
        self.assertEqual(locked["sha256"], EXPECTED_SHA)
        self.assertIs(locked["deployment_allowed"], False)


if __name__ == "__main__":
    unittest.main()
