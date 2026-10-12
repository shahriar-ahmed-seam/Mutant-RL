"""Sim-to-Real calibration and divergence audit metrics."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class CalibrationStatus(StrEnum):
    """Overall health status of synthetic-to-real policy transfer."""
    HEALTHY_CALIBRATED = "healthy_calibrated"
    WARNING_DIVERGENCE = "warning_divergence"
    SIM_TO_REAL_COLLAPSE = "sim_to_real_collapse"


class SimToRealMetrics(BaseModel):
    """Core mathematical telemetry tracking the sim-to-real divergence gap."""
    evaluation_window: int = Field(default=100, description="Number of evaluated instances")
    synthetic_volume_count: int = Field(default=0, ge=0)
    real_pr_volume_count: int = Field(default=0, ge=0)
    synthetic_reward_mean: float = Field(default=0.0, ge=0.0, le=1.0)
    synthetic_resolve_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    real_pr_resolve_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    sim_to_real_gap: float = Field(
        default=0.0,
        description=(
            "R_synth - R_real. High gap indicates policy overfitting on generator shortcuts."
        ),
    )
    wasserstein_action_divergence: float = Field(
        default=0.0,
        ge=0.0,
        description="Distance between action-type distributions on synthetic vs real PRs."
    )
    generator_fingerprint_leak_rate: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Proportion of synthetic tasks quarantined for diff text or symbol leaks."
    )
    shortcut_learning_index: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Aggregate tendency of policy to perform single-line reverts or diff scrapes."
    )
    calibration_status: CalibrationStatus = CalibrationStatus.HEALTHY_CALIBRATED
    stopping_signal_triggered: bool = Field(
        default=False,
        description="Active stop signal when sim_to_real_gap exceeds safe threshold."
    )
    stopping_reason: str | None = None
