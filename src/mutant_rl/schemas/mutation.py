"""Compound mutation and topology schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class MutationOperatorType(StrEnum):
    """Semantic category of mutation operator."""
    COMPOUND_AST = "compound_ast"
    CROSS_FILE_CONTRACT = "cross_file_contract"
    SCHEMA_MIGRATION = "schema_migration"
    CONFIG_CODE_MISMATCH = "config_code_mismatch"
    STATE_MACHINE_LIFECYCLE = "state_machine_lifecycle"
    ASYNC_RACE_CONDITION = "async_race_condition"
    ERROR_HANDLING_DEGRADE = "error_handling_degrade"


class MutationTarget(BaseModel):
    """Specification of an edit location in source or config."""
    file_path: str
    target_symbol: str = ""
    start_line: int
    end_line: int
    original_snippet: str
    mutated_snippet: str
    is_config_target: bool = False


class CoupledMutation(BaseModel):
    """Atomically coupled multi-site mutation spanning code and configs."""
    mutation_id: str
    name: str
    operator_type: MutationOperatorType
    targets: list[MutationTarget] = Field(min_length=1)
    diff_unified: str = ""
    semantic_summary: str = ""
    preserves_syntax: bool = True

    @property
    def touches_multiple_files(self) -> bool:
        unique_paths = {t.file_path for t in self.targets}
        return len(unique_paths) > 1

    @property
    def touches_config(self) -> bool:
        return any(t.is_config_target for t in self.targets)

    @property
    def is_compound(self) -> bool:
        return self.touches_multiple_files or self.touches_config or len(self.targets) > 1


class MutationTopology(BaseModel):
    """Topological graph structure of mutated repository components."""
    environment_id: str
    primary_code_nodes: list[str] = Field(default_factory=list)
    config_nodes: list[str] = Field(default_factory=list)
    cross_file_edges: list[tuple[str, str]] = Field(default_factory=list)
    graph_density: float = Field(default=0.0, ge=0.0, le=1.0)
    spans_multi_file: bool = False
    config_code_ratio: float = Field(default=0.0, ge=0.0)
