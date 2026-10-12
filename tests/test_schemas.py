"""Unit tests for canonical domain schemas in Mutant-RL."""

import pytest
from pydantic import ValidationError

from mutant_rl.schemas import (
    ActionStep,
    AgentActionType,
    BehavioralSymptom,
    BlackboxBehaviorSpec,
    CalibrationStatus,
    CoupledMutation,
    DiffFingerprint,
    FileNode,
    FileType,
    MutationOperatorType,
    MutationTarget,
    PolicyTrajectory,
    ShortcutHeuristicMetrics,
    SimToRealMetrics,
    SymptomCategory,
)


def test_file_node_inference():
    node = FileNode(
        path="config/settings.yaml",
        content="database:\n  port: 5432\n",
    )
    assert node.file_type == FileType.YAML
    assert node.is_config is True
    assert node.line_count == 2


def test_coupled_mutation_properties():
    target1 = MutationTarget(
        file_path="src/gateway.py",
        target_symbol="connect",
        start_line=10,
        end_line=12,
        original_snippet="def connect(timeout=5):",
        mutated_snippet="def connect(timeout=0):",
        is_config_target=False,
    )
    target2 = MutationTarget(
        file_path="config/limits.toml",
        target_symbol="timeout",
        start_line=2,
        end_line=2,
        original_snippet="timeout = 5",
        mutated_snippet="timeout = 0",
        is_config_target=True,
    )

    mutation = CoupledMutation(
        mutation_id="mut_001",
        name="timeout_drift",
        operator_type=MutationOperatorType.CONFIG_CODE_MISMATCH,
        targets=[target1, target2],
        diff_unified="--- a/src/gateway.py\n+++ b/src/gateway.py\n...",
        semantic_summary="Coupled config-code timeout zeroing",
    )

    assert mutation.touches_multiple_files is True
    assert mutation.touches_config is True
    assert mutation.is_compound is True


def test_leak_fingerprint_validation():
    fingerprint = DiffFingerprint(
        n_gram_overlap_score=0.12,
        token_jaccard_score=0.08,
        symbol_leak_count=0,
        line_number_leak_count=0,
        patch_reconstruction_risk=0.15,
        passes_leak_quarantine=True,
    )
    assert fingerprint.passes_leak_quarantine is True

    with pytest.raises(ValidationError):
        # Score must be <= 1.0
        DiffFingerprint(
            n_gram_overlap_score=1.5,
            token_jaccard_score=0.1,
            patch_reconstruction_risk=0.2,
        )


def test_sim_to_real_metrics_divergence():
    metrics = SimToRealMetrics(
        evaluation_window=50,
        synthetic_volume_count=1000,
        real_pr_volume_count=100,
        synthetic_reward_mean=0.88,
        synthetic_resolve_rate=0.85,
        real_pr_resolve_rate=0.20,
        sim_to_real_gap=0.65,
        calibration_status=CalibrationStatus.SIM_TO_REAL_COLLAPSE,
        stopping_signal_triggered=True,
        stopping_reason="Sim-to-Real gap 0.65 exceeds safety threshold 0.25",
    )
    assert metrics.stopping_signal_triggered is True
    assert metrics.calibration_status == CalibrationStatus.SIM_TO_REAL_COLLAPSE


def test_trajectory_and_shortcut_detection():
    step1 = ActionStep(
        step_index=0,
        action_type=AgentActionType.VIEW_FILE,
        target_path="src/gateway.py",
    )
    step2 = ActionStep(
        step_index=1,
        action_type=AgentActionType.GIT_REVERT,
        is_revert_action=True,
        lines_edited_count=1,
    )

    shortcut = ShortcutHeuristicMetrics(
        revert_recent_commit_ratio=0.5,
        localized_one_line_edit_ratio=0.5,
        blind_diff_grep_ratio=0.0,
        shallow_exploration_score=0.7,
        shortcut_exploitation_index=0.6,
        is_shortcutting=True,
    )

    traj = PolicyTrajectory(
        trajectory_id="traj_101",
        instance_id="inst_001",
        agent_model="claude-3-5-sonnet",
        steps=[step1, step2],
        resolved=True,
        reward=1.0,
        shortcut_metrics=shortcut,
    )

    assert len(traj.steps) == 2
    assert traj.shortcut_metrics.is_shortcutting is True


def test_blackbox_behavior_spec():
    symptom = BehavioralSymptom(
        category=SymptomCategory.RUNTIME_EXCEPTION,
        description="Connection refused on port binding",
        observed_exit_code=1,
        error_header="ConnectionRefusedError: Errno 111",
        sanitized_stderr_snippet="Failed to bind on socket ::1",
    )
    spec = BlackboxBehaviorSpec(
        spec_id="spec_001",
        repo_name="org/gateway",
        symptoms=[symptom],
        user_workflow_narrative="Running client.start() triggers sudden socket refusal",
        expected_outcome="Daemon listens on specified port",
        observed_outcome="Process aborts with exit code 1",
    )
    assert len(spec.symptoms) == 1
    assert spec.symptoms[0].observed_exit_code == 1
