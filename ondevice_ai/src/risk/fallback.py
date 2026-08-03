#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
risk/fallback.py
SafeNest V4 Safe Fallback Handler for Sensor Faults & Missing Models
"""

from __future__ import annotations
import time
from typing import Dict, Any, List
from ondevice_ai.src.inference.inference_result import InferenceResult, SafeNestRiskOutput


class FallbackEngine:
    def __init__(
        self,
        weights: Dict[str, float] | None = None,
        stale_sec: float = 3.0
    ):
        if weights is None:
            self.weights = {
                "mmwave": 0.35,  # S1
                "co2": 0.35,     # S2
                "pir": 0.15,     # S3
                "thermal44": 0.15 # S4
            }
        else:
            self.weights = weights
        self.stale_sec = stale_sec

    def evaluate_fallback(
        self,
        sensor_results: Dict[str, InferenceResult],
        now: float | None = None
    ) -> SafeNestRiskOutput:
        t0 = time.perf_counter()
        current_time = now if now is not None else time.time()

        available_sensors: List[str] = []
        excluded_sensors: List[str] = []
        reasons: List[str] = []
        valid_scores: Dict[str, float] = {}

        # Inspect each expected sensor
        for sensor_key, weight in self.weights.items():
            result = sensor_results.get(sensor_key)
            if result is None:
                excluded_sensors.append(sensor_key)
                reasons.append(f"{sensor_key.upper()}_MISSING")
                continue

            # Check validity
            if not result.valid:
                excluded_sensors.append(sensor_key)
                reasons.append(f"{sensor_key.upper()}_INVALID_{result.error or 'UNKNOWN'}")
                continue

            # Check timestamp staleness
            if current_time - result.timestamp > self.stale_sec:
                excluded_sensors.append(sensor_key)
                reasons.append(f"{sensor_key.upper()}_STALE_TIMESTAMP")
                continue

            # Sensor is healthy & valid
            available_sensors.append(sensor_key)
            valid_scores[sensor_key] = result.score

        # Check emergency overrides first among valid results
        thermal_res = sensor_results.get("thermal44")
        if thermal_res and thermal_res.valid and thermal_res.score == 1.0:
            return SafeNestRiskOutput(
                timestamp=current_time,
                risk_score=100.0,
                level="DANGER",
                is_emergency=True,
                reasons=["EMERGENCY_HUMAN_FALL"] + reasons,
                system_status="DEGRADED" if excluded_sensors else "OK",
                sensors={k: v.to_dict() for k, v in sensor_results.items()},
                fallback_used=bool(excluded_sensors),
                metadata={
                    "fallback_latency_ms": (time.perf_counter() - t0) * 1000.0,
                    "available_sensors": available_sensors,
                    "excluded_sensors": excluded_sensors
                }
            )

        mmwave_res = sensor_results.get("mmwave")
        if (
            mmwave_res and mmwave_res.valid and mmwave_res.score == 1.0
            and mmwave_res.metadata.get("apnea_verified") is True
        ):
            return SafeNestRiskOutput(
                timestamp=current_time,
                risk_score=100.0,
                level="DANGER",
                is_emergency=True,
                reasons=["EMERGENCY_HARDWARE_APNEA"] + reasons,
                system_status="DEGRADED" if excluded_sensors else "OK",
                sensors={k: v.to_dict() for k, v in sensor_results.items()},
                fallback_used=bool(excluded_sensors),
                metadata={
                    "fallback_latency_ms": (time.perf_counter() - t0) * 1000.0,
                    "available_sensors": available_sensors,
                    "excluded_sensors": excluded_sensors
                }
            )

        # All sensors missing or invalid -> FAULT state
        if not available_sensors:
            return SafeNestRiskOutput(
                timestamp=current_time,
                risk_score=0.0,
                level="FAULT",
                is_emergency=False,
                reasons=["ALL_SENSORS_FAULT_OR_MISSING"] + reasons,
                system_status="FAULT",
                sensors={k: (v.to_dict() if v else {"valid": False, "error": "MISSING"}) for k, v in sensor_results.items()},
                fallback_used=True,
                metadata={
                    "fallback_latency_ms": (time.perf_counter() - t0) * 1000.0,
                    "available_sensors": [],
                    "excluded_sensors": excluded_sensors
                }
            )

        # Reweight valid sensors dynamically so missing sensors don't artificially lower risk to NORMAL
        total_valid_weight = sum(self.weights[k] for k in available_sensors)
        weighted_sum = sum(valid_scores[k] * (self.weights[k] / total_valid_weight) for k in available_sensors)
        r_score = float(weighted_sum * 100.0)
        r_score = min(max(r_score, 0.0), 100.0)

        if r_score >= 60.0:
            level = "DANGER"
        elif r_score >= 30.0:
            level = "CAUTION"
        else:
            level = "NORMAL"

        system_status = "DEGRADED" if excluded_sensors else "OK"

        return SafeNestRiskOutput(
            timestamp=current_time,
            risk_score=r_score,
            level=level,
            is_emergency=False,
            reasons=reasons if reasons else ["SYSTEM_HEALTHY"],
            system_status=system_status,
            sensors={k: (v.to_dict() if v else {"valid": False}) for k, v in sensor_results.items()},
            fallback_used=bool(excluded_sensors),
            metadata={
                "fallback_latency_ms": (time.perf_counter() - t0) * 1000.0,
                "available_sensors": available_sensors,
                "excluded_sensors": excluded_sensors,
                "reweighted_total_weight": total_valid_weight
            }
        )
