"""OpenCV rendering for the latest validated 80x62 thermal frame."""

from __future__ import annotations

from typing import Any

import numpy as np

from gateway.protocol import THERMAL_HEIGHT, THERMAL_WIDTH, ThermalFrame


class ThermalImageError(RuntimeError):
    """A thermal frame could not be converted into a display image."""


class ThermalImageDependencyError(ThermalImageError):
    """OpenCV is not installed in the Raspberry Pi runtime."""


def normalized_grayscale(frame: ThermalFrame) -> np.ndarray:
    """Decode one big-endian uint16 frame and normalize it to uint8."""

    if (frame.width, frame.height) != (THERMAL_WIDTH, THERMAL_HEIGHT):
        raise ThermalImageError(
            f"unsupported thermal dimensions: {frame.width}x{frame.height}"
        )
    expected_bytes = frame.width * frame.height * 2
    if len(frame.pixel_bytes) != expected_bytes:
        raise ThermalImageError(
            f"thermal pixel payload must be {expected_bytes} bytes, "
            f"got {len(frame.pixel_bytes)}"
        )

    pixels = np.frombuffer(frame.pixel_bytes, dtype=">u2").reshape(
        frame.height, frame.width
    )
    minimum = float(pixels.min())
    maximum = float(pixels.max())
    if minimum != float(frame.minimum_raw) or maximum != float(frame.maximum_raw):
        raise ThermalImageError(
            "thermal frame min/max metadata does not match the pixel payload"
        )
    if maximum <= minimum:
        return np.zeros((frame.height, frame.width), dtype=np.uint8)

    normalized = (pixels.astype(np.float32) - minimum) * (255.0 / (maximum - minimum))
    return np.clip(np.rint(normalized), 0, 255).astype(np.uint8)


def encode_thermal_jpeg(
    frame: ThermalFrame,
    *,
    output_size: tuple[int, int] = (640, 496),
    jpeg_quality: int = 90,
    cv2_module: Any | None = None,
) -> bytes:
    """Create a colorized JPEG using OpenCV's INFERNO color map."""

    if output_size[0] <= 0 or output_size[1] <= 0:
        raise ValueError("output_size dimensions must be positive")
    if not 1 <= jpeg_quality <= 100:
        raise ValueError("jpeg_quality must be in the range 1..100")
    if cv2_module is None:
        try:
            import cv2 as cv2_module
        except ImportError as error:
            raise ThermalImageDependencyError(
                "OpenCV is unavailable; install requirements-backend.txt"
            ) from error

    grayscale = normalized_grayscale(frame)
    color_map = getattr(
        cv2_module,
        "COLORMAP_INFERNO",
        getattr(cv2_module, "COLORMAP_JET", None),
    )
    if color_map is None:
        raise ThermalImageError("OpenCV does not provide a supported color map")

    colorized = cv2_module.applyColorMap(grayscale, color_map)
    resized = cv2_module.resize(
        colorized,
        output_size,
        interpolation=cv2_module.INTER_CUBIC,
    )
    encoded, buffer = cv2_module.imencode(
        ".jpg",
        resized,
        [int(cv2_module.IMWRITE_JPEG_QUALITY), int(jpeg_quality)],
    )
    if not encoded:
        raise ThermalImageError("OpenCV failed to encode the thermal JPEG")
    return bytes(buffer)
