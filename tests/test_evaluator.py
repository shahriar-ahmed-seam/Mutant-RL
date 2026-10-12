"""Unit tests for Sim-to-Real gap auditor, shortcut detector, and calibrator."""

from mutant_rl.evaluator import (
    RealPRAnchorCalibrator,
    ShortcutDetector,
    SimToRealGapAuditor,
    TrajectoryDistributionDivergence,
)
from mutant_rl.schemas.environment import EnvironmentInstance, InstanceType
from mutant_rl.schemas.metrics import CalibrationStatus
from mutant_rl.schemas.trajectory import (
    ActionStep,
    AgentActionType,
    PolicyTrajectory,
)


def test_shortcut_detector_exploit():
    # Construct a policy trajectory that exploits shortcuts: immediately reverts
    steps = [
        ActionStep(step_index=0, action_type=AgentActionType.GIT_REVERT, is_revert_action=True),
        ActionStep(step_index=1, action_type=AgentActionType.EDIT_FILE, lines_edited_count=1),
    ]
    traj = PolicyTrajectory(
        trajectory_id="t_exploit",
        instance_id="inst_1",
        agent_model="policy-beta",
        steps=steps,
        resolved=True,
        reward=1.0,
    )

    detector = ShortcutDetector()
    metrics = detector.analyze_trajectory(traj)

    assert metrics.is_shortcutting is True
    assert metrics.revert_recent_commit_ratio == 0.5
    assert metrics.localized_one_line_edit_ratio == 1.0
    assert metrics.shortcut_exploitation_index > 0.40


def test_shortcut_detector_clean():
    # Construct a legitimate policy trajectory: views files, runs bash tests, edits multi-line
    steps = [
        ActionStep(step_index=0, action_type=AgentActionType.VIEW_FILE),
        ActionStep(step_index=1, action_type=AgentActionType.VIEW_FILE),
        ActionStep(step_index=2, action_type=AgentActionType.EDIT_FILE, lines_edited_count=15),
        ActionStep(step_index=3, action_type=AgentActionType.RUN_COMMAND, command_str="pytest"),
    ]
    traj = PolicyTrajectory(
        trajectory_id="t_clean",
        instance_id="inst_2",
        agent_model="policy-beta",
        steps=steps,
        resolved=True,
        reward=1.0,
    )

    detector = ShortcutDetector()
    metrics = detector.analyze_trajectory(traj)

    assert metrics.is_shortcutting is False
    assert metrics.revert_recent_commit_ratio == 0.0
    assert metrics.localized_one_line_edit_ratio == 0.0


def test_trajectory_distribution_divergence():
    synth_trajs = [
        PolicyTrajectory(
            trajectory_id="s1",
            instance_id="si1",
            agent_model="m1",
            steps=[
                ActionStep(step_index=0, action_type=AgentActionType.GIT_REVERT),
                ActionStep(step_index=1, action_type=AgentActionType.EDIT_FILE),
            ],
        )
    ]
    real_trajs = [
        PolicyTrajectory(
            trajectory_id="r1",
            instance_id="ri1",
            agent_model="m1",
            steps=[
                ActionStep(step_index=0, action_type=AgentActionType.VIEW_FILE),
                ActionStep(step_index=1, action_type=AgentActionType.RUN_COMMAND),
            ],
        )
    ]

    divergence_calc = TrajectoryDistributionDivergence()
    tv = divergence_calc.compute_total_variation_distance(synth_trajs, real_trajs)
    jsd = divergence_calc.compute_jensen_shannon_divergence(synth_trajs, real_trajs)

    assert tv > 0.5
    assert jsd > 0.5


def test_sim_to_real_gap_auditor_triggers_stop():
    # Synthetic resolve rate = 90%, Real resolve rate = 10% -> Gap = 80% (sim-to-real collapse!)
    synth_trajs = [
        PolicyTrajectory(
            trajectory_id=f"s_{i}",
            instance_id=f"inst_s_{i}",
            agent_model="m1",
            steps=[
                ActionStep(
                    step_index=0,
                    action_type=AgentActionType.EDIT_FILE,
                    lines_edited_count=1,
                )
            ],
            resolved=(i < 9),  # 9 of 10 resolved
            reward=1.0 if (i < 9) else 0.0,
        )
        for i in range(10)
    ]
    real_trajs = [
        PolicyTrajectory(
            trajectory_id=f"r_{i}",
            instance_id=f"inst_r_{i}",
            agent_model="m1",
            steps=[ActionStep(step_index=0, action_type=AgentActionType.VIEW_FILE)],
            resolved=(i < 1),  # 1 of 10 resolved
            reward=1.0 if (i < 1) else 0.0,
        )
        for i in range(10)
    ]

    auditor = SimToRealGapAuditor(max_allowed_gap=0.25)
    metrics = auditor.audit_trajectories(synth_trajs, real_trajs)

    assert metrics.synthetic_resolve_rate == 0.90
    assert metrics.real_pr_resolve_rate == 0.10
    assert metrics.sim_to_real_gap == 0.80
    assert metrics.calibration_status == CalibrationStatus.SIM_TO_REAL_COLLAPSE
    assert metrics.stopping_signal_triggered is True
    assert "exceeds safety threshold" in (metrics.stopping_reason or "")


def test_real_pr_anchor_calibrator():
    real_instances = [
        EnvironmentInstance(
            instance_id="pr_1",
            repo_name="org/repo",
            base_commit="abc",
            instance_type=InstanceType.REAL_PR,
            problem_statement="Bug report with ten words describing behavioral failure",
            files={"src/a.py": "", "src/b.py": "", "config.yaml": ""},
        ),
        EnvironmentInstance(
            instance_id="pr_2",
            repo_name="org/repo",
            base_commit="def",
            instance_type=InstanceType.REAL_PR,
            problem_statement="Another problem statement describing unexpected exit code zero",
            files={"src/c.py": "", "config.toml": ""},
        ),
    ]

    calibrator = RealPRAnchorCalibrator()
    weights = calibrator.calibrate_from_real_prs(real_instances)

    assert weights.min_files_per_mutation >= 2
    assert weights.config_code_mutation_ratio > 0.10
    assert weights.calibration_confidence > 0.50
