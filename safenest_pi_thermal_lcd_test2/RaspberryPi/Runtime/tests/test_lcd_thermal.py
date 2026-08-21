from __future__ import annotations

from pathlib import Path
import unittest

import numpy as np

from backend.thermal_image import (
    ThermalImageError,
    encode_thermal_jpeg,
    normalized_grayscale,
)
from backend.views import lcd_thermal_document
from gateway.protocol import PacketHeader, ThermalFrame
from paths import LCD_STATIC, RUNTIME_ROOT


def thermal_frame(*, sequence: int = 7, constant: int | None = None) -> ThermalFrame:
    if constant is None:
        values = [1_000 + index for index in range(80 * 62)]
    else:
        values = [constant] * (80 * 62)
    pixels = b"".join(value.to_bytes(2, "big") for value in values)
    return ThermalFrame(
        PacketHeader(2, sequence, 9_936),
        80,
        62,
        sequence,
        12_345,
        min(values),
        max(values),
        pixels,
    )


def publication(sequence: int = 7) -> dict[str, object]:
    return {
        "timestamp": 100.0,
        "publication_revision": 3,
        "state": {
            "revision": 3,
            "system": "ONLINE",
            "sensors": {
                "thermal": {
                    "status": "LIVE",
                    "current": True,
                    "values": {"frame_sequence": sequence},
                }
            },
        },
        "ai": {
            "ai": {
                "thermal": {
                    "available": True,
                    "state": "HUMAN_NORMAL",
                    "confidence": 0.91,
                    "latency_ms": 3.2,
                    "model_id": "thermal_fall_int8",
                    "model_version": "0.1.0",
                    "metadata": {
                        "frame_sequence": sequence,
                        "probabilities": [0.02, 0.91, 0.07],
                    },
                }
            }
        },
        "risk": {},
        "emergency": {},
    }


class FakeOpenCV:
    COLORMAP_INFERNO = 11
    INTER_CUBIC = 22
    IMWRITE_JPEG_QUALITY = 33

    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def applyColorMap(self, grayscale, color_map):
        self.calls.append(("color", grayscale.shape, color_map))
        return np.repeat(grayscale[..., None], 3, axis=2)

    def resize(self, image, output_size, interpolation):
        self.calls.append(("resize", image.shape, output_size, interpolation))
        return np.zeros((output_size[1], output_size[0], 3), dtype=np.uint8)

    def imencode(self, extension, image, parameters):
        self.calls.append(("encode", extension, image.shape, parameters))
        return True, np.asarray([0xFF, 0xD8, 0xFF, 0xD9], dtype=np.uint8)


class ThermalImageTests(unittest.TestCase):
    def test_big_endian_frame_is_normalized_to_uint8(self) -> None:
        grayscale = normalized_grayscale(thermal_frame())
        self.assertEqual(grayscale.shape, (62, 80))
        self.assertEqual(grayscale.dtype, np.uint8)
        self.assertEqual(int(grayscale[0, 0]), 0)
        self.assertEqual(int(grayscale[-1, -1]), 255)

    def test_constant_frame_is_valid_black_image(self) -> None:
        grayscale = normalized_grayscale(thermal_frame(constant=2_500))
        self.assertTrue(np.all(grayscale == 0))

    def test_metadata_mismatch_fails_closed(self) -> None:
        frame = thermal_frame()
        broken = ThermalFrame(
            frame.header,
            frame.width,
            frame.height,
            frame.frame_sequence,
            frame.uptime_ms,
            frame.minimum_raw,
            frame.maximum_raw + 1,
            frame.pixel_bytes,
        )
        with self.assertRaisesRegex(ThermalImageError, "min/max metadata"):
            normalized_grayscale(broken)

    def test_opencv_pipeline_colorizes_resizes_and_encodes(self) -> None:
        fake_cv2 = FakeOpenCV()
        encoded = encode_thermal_jpeg(
            thermal_frame(),
            output_size=(320, 248),
            cv2_module=fake_cv2,
        )
        self.assertEqual(encoded, b"\xff\xd8\xff\xd9")
        self.assertEqual(fake_cv2.calls[0], ("color", (62, 80), 11))
        self.assertEqual(fake_cv2.calls[1][2:], ((320, 248), 22))
        self.assertEqual(fake_cv2.calls[2][0:2], ("encode", ".jpg"))


class LCDThermalContractTests(unittest.TestCase):
    def test_document_pairs_frame_and_inference(self) -> None:
        frame = thermal_frame(sequence=9)
        document = lcd_thermal_document(
            publication(9),
            frame,
            thermal_state={"status": "LIVE", "current": True},
        )
        self.assertEqual(document["schema"], "safenest.lcd.thermal.v1")
        self.assertTrue(document["frame"]["current"])
        self.assertIn("sequence=9", document["frame"]["image_url"])
        self.assertFalse(document["frame"]["temperature_calibrated"])
        self.assertEqual(document["inference"]["label_ko"], "사람 감지 · 정상 자세")
        self.assertTrue(document["inference"]["matches_displayed_frame"])

    def test_no_frame_or_ai_is_explicitly_unavailable(self) -> None:
        document = lcd_thermal_document(None, None)
        self.assertFalse(document["frame"]["available"])
        self.assertFalse(document["inference"]["available"])
        self.assertEqual(document["inference"]["state"], "INPUT_UNAVAILABLE")

    def test_lcd_and_backend_source_expose_both_panels(self) -> None:
        html = (LCD_STATIC / "display.html").read_text(encoding="utf-8")
        app = (RUNTIME_ROOT / "backend" / "app.py").read_text(encoding="utf-8")
        self.assertIn("OpenCV 열화상", html)
        self.assertIn("ON-DEVICE AI", html)
        self.assertIn("HUMAN_NORMAL", html)
        self.assertIn('fetch("/api/lcd/thermal"', html)
        self.assertIn('@app.get("/api/lcd/thermal/image.jpg")', app)
        self.assertIn("encode_thermal_jpeg(frame)", app)


if __name__ == "__main__":
    unittest.main()
