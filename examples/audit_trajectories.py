"""Demonstration of Sim-to-Real gap calculation and shortcut learning detection."""

from __future__ import annotations

from mutant_rl.pipeline import MutantPipeline
from mutant_rl.schemas.trajectory import (
    ActionStep,
    AgentActionType,
    PolicyTrajectory,
)


def main() -> None:
    # 1. Construct synthetic rollouts exhibiting shortcut heuristics
    synth_rollouts = [
        PolicyTrajectory(
            trajectory_id=f"synth_{i}",
            instance_id=f"task_{i}",
            agent_model="test-policy",
            steps=[
                ActionStep(
                    step_index=0,
                    action_type=AgentActionType.GIT_REVERT,
                    is_revert_action=True,
                ),
                ActionStep(
                    step_index=1,
                    action_type=AgentActionType.EDIT_FILE,
                    lines_edited_count=1,
                ),
            ],
            resolved=(i < 8),
            reward=1.0 if (i < 8) else 0.0,
        )
        for i in range(10)
    ]

    # 2. Construct empirical real PR rollouts where simple reverts fail
    real_rollouts = [
        PolicyTrajectory(
            trajectory_id=f"real_{i}",
            instance_id=f"pr_{i}",
            agent_model="test-policy",
            steps=[
                ActionStep(step_index=0, action_type=AgentActionType.VIEW_FILE),
                ActionStep(step_index=1, action_type=AgentActionType.RUN_COMMAND),
            ],
            resolved=(i < 3),
            reward=1.0 if (i < 3) else 0.0,
        )
        for i in range(10)
    ]

    # 3. Audit Sim-to-Real gap
    pipeline = MutantPipeline()
    metrics = pipeline.audit_trajectories(synth_rollouts, real_rollouts)

    print("Sim-to-Real Telemetry Audit:")
    print(f"Synthetic Resolve Rate: {metrics.synthetic_resolve_rate:.2%}")
    print(f"Real PR Resolve Rate:   {metrics.real_pr_resolve_rate:.2%}")
    print(f"Sim-to-Real Gap:        {metrics.sim_to_real_gap:.2%}")
    print(f"TV Action Divergence:   {metrics.wasserstein_action_divergence:.4f}")
    print(f"Shortcut Index:         {metrics.shortcut_learning_index:.4f}")
    print(f"Calibration Status:     {metrics.calibration_status.value}")
    print(f"Stopping Signal Active: {metrics.stopping_signal_triggered}")
    if metrics.stopping_reason:
        print(f"Reason: {metrics.stopping_reason}")


if __name__ == "__main__":
    main()
