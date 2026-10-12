"""Environment and repository state schemas."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class InstanceType(StrEnum):
    """Source classification of the environment instance."""

    SYNTHETIC = "synthetic"
    REAL_PR = "real_pr"


class FileType(StrEnum):
    """File syntax classification."""

    PYTHON = "python"
    YAML = "yaml"
    TOML = "toml"
    JSON = "json"
    MARKDOWN = "markdown"
    OTHER = "other"


class FileNode(BaseModel):
    """Individual repository file model with structural metadata."""

    path: str
    content: str
    file_type: FileType = FileType.PYTHON
    ast_hash: str | None = None
    line_count: int = 0
    is_config: bool = False

    def model_post_init(self, __context: Any) -> None:
        if self.line_count == 0 and self.content:
            object.__setattr__(self, "line_count", len(self.content.splitlines()))
        if self.path.endswith((".yaml", ".yml")):
            object.__setattr__(self, "file_type", FileType.YAML)
            object.__setattr__(self, "is_config", True)
        elif self.path.endswith(".toml"):
            object.__setattr__(self, "file_type", FileType.TOML)
            object.__setattr__(self, "is_config", True)
        elif self.path.endswith(".json"):
            object.__setattr__(self, "file_type", FileType.JSON)
            object.__setattr__(self, "is_config", True)


class RepoState(BaseModel):
    """Snapshot representation of a target repository state."""

    repo_name: str
    base_commit: str
    files: dict[str, FileNode] = Field(default_factory=dict)
    test_suite_command: str = "pytest"
    initial_passing_tests: list[str] = Field(default_factory=list)


class EnvironmentInstance(BaseModel):
    """Canonical benchmark/training environment instance."""

    instance_id: str
    repo_name: str
    base_commit: str
    instance_type: InstanceType = InstanceType.SYNTHETIC
    problem_statement: str
    files: dict[str, str] = Field(default_factory=dict, description="Relative path to file content")
    patch: str = Field(default="", description="Ground-truth fix patch")
    test_patch: str = Field(default="", description="Reproduction or regression test patch")
    oracle_command: str = "pytest"
    metadata: dict[str, Any] = Field(default_factory=dict)
