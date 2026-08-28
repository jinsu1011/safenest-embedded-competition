"""Lazy, failure-isolated loading of the frozen TFLite adapters."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys
import threading
from typing import Callable

from paths import ONDEVICE_AI_ROOT


VENDOR_ROOT = ONDEVICE_AI_ROOT


class ModelRuntimeUnavailable(RuntimeError):
    """The model adapter or its TFLite runtime could not be loaded."""


class LazyModel:
    """Load a frozen interpreter only when a complete input first arrives."""

    # sensor_id -> (adapter filename, adapter class, manifest selector key)
    # The manifest key is separate because the CO2 selector was promoted to the
    # C-B6 reduced-feature contract while models.co2 is retained as history.
    _ADAPTERS = {
        "thermal": (
            "thermal_interpreter.py",
            "ThermalInterpreter",
            "thermal_public_sdt_fp32_active",
        ),
        # Legacy M-N9 adapter only. Default inference is B23 in pipeline.py.
        "mmwave": ("mmwave_m_n9_interpreter.py", "MN9Interpreter", "mmwave_m_n9"),
        "co2": ("co2_c_b6_interpreter.py", "CB6Interpreter", "co2_occupancy_c_b6"),
    }

    def __init__(self, sensor_id: str, factory: Callable[[], object] | None = None) -> None:
        if sensor_id not in self._ADAPTERS:
            raise ValueError(f"unknown model sensor: {sensor_id}")
        self.sensor_id = sensor_id
        self._factory = factory
        self._instance: object | None = None
        self._load_error: str | None = None
        self._lock = threading.Lock()

    @property
    def load_error(self) -> str | None:
        return self._load_error

    @property
    def model_selector(self) -> str:
        """Expose the frozen selector without forcing an early model load."""
        return self._ADAPTERS[self.sensor_id][2]

    @property
    def model_meta(self) -> dict:
        """Expose loaded manifest policy to the pipeline after prediction."""
        if self._instance is None:
            return {}
        metadata = getattr(self._instance, "model_meta", {})
        return metadata if isinstance(metadata, dict) else {}

    def predict(self, *args: object) -> object:
        instance = self._load()
        try:
            return instance.predict(*args)
        except Exception as error:
            raise ModelRuntimeUnavailable(
                f"{self.sensor_id} inference failed: {type(error).__name__}: {error}"
            ) from error

    def _load(self) -> object:
        if self._instance is not None:
            return self._instance
        if self._load_error is not None:
            raise ModelRuntimeUnavailable(self._load_error)
        with self._lock:
            if self._instance is not None:
                return self._instance
            if self._load_error is not None:
                raise ModelRuntimeUnavailable(self._load_error)
            try:
                self._instance = self._factory() if self._factory else self._load_frozen_adapter()
            except Exception as error:
                self._load_error = (
                    f"{self.sensor_id} model unavailable: {type(error).__name__}: {error}"
                )
                raise ModelRuntimeUnavailable(self._load_error) from error
            return self._instance

    def _load_frozen_adapter(self) -> object:
        self._assert_deployment_allowed()
        filename, class_name, selector = self._ADAPTERS[self.sensor_id]
        adapter_path = VENDOR_ROOT / "inference" / filename
        module_name = f"_safenest_frozen_{self.sensor_id}_interpreter"
        module = sys.modules.get(module_name)
        if module is None:
            spec = importlib.util.spec_from_file_location(module_name, adapter_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"cannot load adapter {adapter_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
            except Exception:
                sys.modules.pop(module_name, None)
                raise
        adapter_class = getattr(module, class_name)
        kwargs = {"project_root": VENDOR_ROOT}
        if self.sensor_id == "thermal":
            kwargs["model_key"] = selector
        return adapter_class(**kwargs)

    def _assert_deployment_allowed(self) -> None:
        manifest_path = VENDOR_ROOT / "models" / "model_manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        selector = self._ADAPTERS[self.sensor_id][2]
        active_selectors = manifest.get("active_runtime_selectors", {})
        if self.sensor_id == "thermal" and active_selectors.get("thermal") != selector:
            raise ModelRuntimeUnavailable(
                "MODEL_SELECTOR_DRIFT: sensor=thermal, "
                f"runtime={selector}, manifest={active_selectors.get('thermal')}"
            )
        metadata = manifest.get("models", {}).get(selector)
        if not isinstance(metadata, dict):
            raise ModelRuntimeUnavailable(
                f"MODEL_MANIFEST_ENTRY_MISSING: sensor={self.sensor_id}, selector={selector}"
            )
        if metadata.get("deployment_allowed") is False:
            reason = metadata.get("block_reason", "UNSPECIFIED")
            raise ModelRuntimeUnavailable(
                f"MODEL_RELEASE_BLOCKED: sensor={self.sensor_id}, selector={selector},"
                f" reason={reason}"
            )
