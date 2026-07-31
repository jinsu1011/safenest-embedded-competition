#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
inference/inference_result.py
SafeNest V4 On-Device AI Standardized Inference Output Schema
"""

from __future__ import annotations
from dataclasses import dataclass, asdict, field
import json
import time


@dataclass(frozen=True)
class InferenceResult:
    sensor_id: str
    timestamp: float
    score: float           # Normalized risk score in range [0.0, 1.0]
    state: str             # State string (e.g. "NORMAL", "HUMAN_FALL", "APNEA", "ELEVATED", "MOTION")
    confidence: float      # Model confidence or rule reliability [0.0, 1.0]
    valid: bool            # True if sensor telemetry and inference are healthy
    latency_ms: float      # Total latency (preprocessing + inference + postprocessing)
    error: str | None = None
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        # Validate score bounds
        if not (0.0 <= self.score <= 1.0):
            raise ValueError(f"InferenceResult score must be between 0.0 and 1.0, got {self.score}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"InferenceResult confidence must be between 0.0 and 1.0, got {self.confidence}")

    def to_dict(self) -> dict:
        data = asdict(self)
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


@dataclass(frozen=True)
class SafeNestRiskOutput:
    timestamp: float
    risk_score: float      # Overall R score in range [0.0, 100.0]
    level: str             # "NORMAL", "CAUTION", "DANGER", "FAULT"
    is_emergency: bool
    reasons: list[str]
    system_status: str     # "OK", "DEGRADED", "FAULT"
    sensors: dict[str, dict]
    fallback_used: bool = False
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
