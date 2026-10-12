"""Shortcut learning and generator exploit detection in agent trajectories."""

from __future__ import annotations

from mutant_rl.schemas.trajectory import (
    AgentActionType,
    PolicyTrajectory,
    ShortcutHeuristicMetrics,
)


class ShortcutDetector:
    """Analyzes rollout action traces for shortcut heuristics and fingerprint exploits."""

    def __init__(self, exploit_threshold: float = 0.40) -> None:
        self.exploit_threshold = exploit_threshold

    def analyze_trajectory(self, trajectory: PolicyTrajectory) -> ShortcutHeuristicMetrics:
        """Evaluates whether the policy solved the task via spurious generator shortcuts."""
        steps = trajectory.steps
        if not steps:
            return ShortcutHeuristicMetrics(
                revert_recent_commit_ratio=0.0,
                localized_one_line_edit_ratio=0.0,
                blind_diff_grep_ratio=0.0,
                shallow_exploration_score=0.0,
                shortcut_exploitation_index=0.0,
                is_shortcutting=False,
            )

        total_steps = len(steps)
        revert_steps = 0
        one_line_edits = 0
        diff_greps = 0
        edit_steps = 0

        for s in steps:
            if s.is_revert_action or s.action_type in (
                AgentActionType.GIT_REVERT,
                AgentActionType.GIT_CHECKOUT,
            ):
                revert_steps += 1
            if s.action_type == AgentActionType.EDIT_FILE:
                edit_steps += 1
                if s.lines_edited_count == 1:
                    one_line_edits += 1
            if s.is_blind_diff_search or (
                s.action_type == AgentActionType.GREP_SEARCH
                and any(t in s.command_str.lower() for t in ["diff", "patch", "git log -p", "head"])
            ):
                diff_greps += 1

        revert_ratio = revert_steps / total_steps
        one_line_ratio = (one_line_edits / max(1, edit_steps)) if edit_steps > 0 else 0.0
        diff_grep_ratio = diff_greps / total_steps

        # Shallow exploration: if policy edited files without reading dependencies first
        view_count = sum(1 for s in steps if s.action_type == AgentActionType.VIEW_FILE)
        shallow_score = max(0.0, 1.0 - (view_count / max(1, edit_steps * 2)))

        # Weighted shortcut index
        index = (
            (revert_ratio * 0.40)
            + (one_line_ratio * 0.30)
            + (diff_grep_ratio * 0.20)
            + (shallow_score * 0.10)
        )
        index = min(1.0, max(0.0, round(index, 4)))

        is_shortcutting = index >= self.exploit_threshold

        return ShortcutHeuristicMetrics(
            revert_recent_commit_ratio=round(revert_ratio, 4),
            localized_one_line_edit_ratio=round(one_line_ratio, 4),
            blind_diff_grep_ratio=round(diff_grep_ratio, 4),
            shallow_exploration_score=round(shallow_score, 4),
            shortcut_exploitation_index=index,
            is_shortcutting=is_shortcutting,
        )
