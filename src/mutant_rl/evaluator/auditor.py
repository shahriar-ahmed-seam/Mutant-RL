"""Sim-to-Real gap evaluation, stopping signal, and telemetry auditing."""

from __future__ import annotations

from mutant_rl.evaluator.divergence import TrajectoryDistributionDivergence
from mutant_rl.evaluator.shortcuts import ShortcutDetector
from mutant_rl.schemas.metrics import CalibrationStatus, SimToRealMetrics
from mutant_rl.schemas.trajectory import PolicyTrajectory


class SimToRealGapAuditor:
    """Continuously evaluates sim-to-real transfer and triggers automated stopping signals."""

    def __init__(
        self,
        max_allowed_gap: float = 0.25,
        max_allowed_divergence: float = 0.35,
        max_allowed_shortcut_index: float = 0.45,
    ) -> None:
        self.max_allowed_gap = max_allowed_gap
        self.max_allowed_divergence = max_allowed_divergence
        self.max_allowed_shortcut_index = max_allowed_shortcut_index
        self.shortcut_detector = ShortcutDetector()
        self.divergence_calc = TrajectoryDistributionDivergence()

    def audit_trajectories(
        self,
        synth_trajectories: list[PolicyTrajectory],
        real_trajectories: list[PolicyTrajectory],
        quarantined_count: int = 0,
    ) -> SimToRealMetrics:
        """Computes comprehensive sim-to-real metrics and stopping signal."""
        synth_vol = len(synth_trajectories)
        real_vol = len(real_trajectories)

        synth_resolved = sum(1 for t in synth_trajectories if t.resolved)
        real_resolved = sum(1 for t in real_trajectories if t.resolved)

        synth_rate = (synth_resolved / synth_vol) if synth_vol > 0 else 0.0
        real_rate = (real_resolved / real_vol) if real_vol > 0 else 0.0

        synth_rewards = [t.reward for t in synth_trajectories]
        mean_synth_reward = (sum(synth_rewards) / synth_vol) if synth_vol > 0 else 0.0

        gap = round(synth_rate - real_rate, 4)

        divergence = self.divergence_calc.compute_total_variation_distance(
            synth_trajectories, real_trajectories
        )

        # Average shortcut index across synthetic rollouts
        shortcut_indices: list[float] = []
        for t in synth_trajectories:
            metrics = self.shortcut_detector.analyze_trajectory(t)
            shortcut_indices.append(metrics.shortcut_exploitation_index)

        avg_shortcut = (
            round(sum(shortcut_indices) / len(shortcut_indices), 4) if shortcut_indices else 0.0
        )

        leak_rate = (
            round(quarantined_count / max(1, synth_vol + quarantined_count), 4)
            if (synth_vol + quarantined_count) > 0
            else 0.0
        )

        # Determine status and stopping signal
        stopping_triggered = False
        reason = None

        if gap > self.max_allowed_gap:
            status = CalibrationStatus.SIM_TO_REAL_COLLAPSE
            stopping_triggered = True
            reason = (
                f"Sim-to-Real gap ({gap:.2%}) exceeds safety threshold "
                f"({self.max_allowed_gap:.2%}). "
                "Policy is overfitting to synthetic shortcuts while real resolve rate remains flat."
            )
        elif divergence > self.max_allowed_divergence:
            status = CalibrationStatus.WARNING_DIVERGENCE
            if divergence > (self.max_allowed_divergence * 1.3):
                stopping_triggered = True
                status = CalibrationStatus.SIM_TO_REAL_COLLAPSE
                reason = (
                    f"Action distribution divergence ({divergence:.2f}) "
                    "indicates severe behavioral drift."
                )
            else:
                reason = f"Action divergence ({divergence:.2f}) approaching threshold."
        elif avg_shortcut > self.max_allowed_shortcut_index:
            status = CalibrationStatus.SIM_TO_REAL_COLLAPSE
            stopping_triggered = True
            reason = (
                f"Shortcut exploitation index ({avg_shortcut:.2f}) exceeds threshold. "
                "Policy is exploiting generator fingerprints."
            )
        elif gap > (self.max_allowed_gap * 0.6):
            status = CalibrationStatus.WARNING_DIVERGENCE
            reason = "Sim-to-Real gap in warning zone."
        else:
            status = CalibrationStatus.HEALTHY_CALIBRATED

        return SimToRealMetrics(
            evaluation_window=synth_vol + real_vol,
            synthetic_volume_count=synth_vol,
            real_pr_volume_count=real_vol,
            synthetic_reward_mean=round(mean_synth_reward, 4),
            synthetic_resolve_rate=round(synth_rate, 4),
            real_pr_resolve_rate=round(real_rate, 4),
            sim_to_real_gap=gap,
            wasserstein_action_divergence=divergence,
            generator_fingerprint_leak_rate=leak_rate,
            shortcut_learning_index=avg_shortcut,
            calibration_status=status,
            stopping_signal_triggered=stopping_triggered,
            stopping_reason=reason,
        )
