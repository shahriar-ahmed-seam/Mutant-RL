"""Agent rollout trajectory and shortcut learning schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class AgentActionType(StrEnum):
    """Categorization of agent tool invocation."""

    EDIT_FILE = "edit_file"
    VIEW_FILE = "view_file"
    LIST_DIR = "list_dir"
    RUN_COMMAND = "run_command"
    GREP_SEARCH = "grep_search"
    GIT_REVERT = "git_revert"
    GIT_CHECKOUT = "git_checkout"
    OTHER = "other"


class ActionStep(BaseModel):
    """Discrete action step executed by the policy during a rollout."""

    step_index: int
    action_type: AgentActionType
    target_path: str = ""
    command_str: str = ""
    is_revert_action: bool = False
    is_blind_diff_search: bool = False
    lines_edited_count: int = 0
    duration_ms: float = 0.0


class ShortcutHeuristicMetrics(BaseModel):
    """Metrics quantifying whether policy is exploiting generator fingerprints."""

    revert_recent_commit_ratio: float = Field(ge=0.0, le=1.0)
    localized_one_line_edit_ratio: float = Field(ge=0.0, le=1.0)
    blind_diff_grep_ratio: float = Field(ge=0.0, le=1.0)
    shallow_exploration_score: float = Field(ge=0.0, le=1.0)
    shortcut_exploitation_index: float = Field(ge=0.0, le=1.0)
    is_shortcutting: bool = False


class PolicyTrajectory(BaseModel):
    """Complete trajectory trace of an agent solving an environment instance."""

    trajectory_id: str
    instance_id: str
    instance_type: str = "synthetic"  # synthetic or real_pr
    agent_model: str
    steps: list[ActionStep] = Field(default_factory=list)
    resolved: bool = False
    reward: float = 0.0
    wall_time_seconds: float = 0.0
    shortcut_metrics: ShortcutHeuristicMetrics | None = None
