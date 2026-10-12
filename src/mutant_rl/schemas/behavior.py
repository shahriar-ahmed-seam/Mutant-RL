"""Behavioral specification and black-box symptom schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SymptomCategory(StrEnum):
    """Observable external behavioral regression categories."""

    RUNTIME_EXCEPTION = "runtime_exception"
    STATUS_CODE_FAILURE = "status_code_failure"
    ASSERTION_REGRESSION = "assertion_regression"
    SILENT_DATA_CORRUPTION = "silent_data_corruption"
    CONFIG_PARSE_FAILURE = "config_parse_failure"
    TIMEOUT_HANG = "timeout_hang"
    RESOURCE_LEAK = "resource_leak"


class BehavioralSymptom(BaseModel):
    """External observable symptom exhibited by the bug."""

    category: SymptomCategory
    description: str
    observed_exit_code: int = 1
    error_header: str = ""
    sanitized_stderr_snippet: str = ""
    reproduction_command: str = "pytest"


class BlackboxBehaviorSpec(BaseModel):
    """Formal behavioral symptom spec for issue prompt synthesis."""

    spec_id: str
    repo_name: str
    symptoms: list[BehavioralSymptom] = Field(min_length=1)
    user_workflow_narrative: str
    expected_outcome: str
    observed_outcome: str
    environment_flags: dict[str, str] = Field(default_factory=dict)
    reproduction_script_content: str = ""
