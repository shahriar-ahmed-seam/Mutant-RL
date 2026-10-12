"""Behavioral issue statement synthesis without diff leakage."""

from __future__ import annotations

from mutant_rl.schemas.behavior import (
    BehavioralSymptom,
    BlackboxBehaviorSpec,
    SymptomCategory,
)
from mutant_rl.schemas.mutation import CoupledMutation


class BehavioralIssueSynthesizer:
    """Generates user-facing behavioral bug descriptions from observed runtime symptoms."""

    def synthesize_from_spec(self, spec: BlackboxBehaviorSpec) -> str:
        """Constructs an issue statement adhering to black-box behavioral reporting."""
        lines = [
            f"# Bug Report: Observed Regression in {spec.repo_name}",
            "",
            "## Description",
            spec.user_workflow_narrative,
            "",
            "## Expected Behavior",
            spec.expected_outcome,
            "",
            "## Observed Symptoms",
        ]

        for s in spec.symptoms:
            lines.append(f"- Category: {s.category.value}")
            lines.append(f"  Impact: {s.description}")
            if s.error_header:
                lines.append(f"  Error Log: {s.error_header}")
            if s.sanitized_stderr_snippet:
                lines.append("  ```")
                lines.append(f"  {s.sanitized_stderr_snippet}")
                lines.append("  ```")

        if spec.reproduction_script_content:
            lines.extend(
                [
                    "",
                    "## Minimal Reproduction",
                    "```python",
                    spec.reproduction_script_content.strip(),
                    "```",
                ]
            )

        return "\n".join(lines) + "\n"

    def synthesize_from_coupled_mutation(
        self, repo_name: str, mutation: CoupledMutation
    ) -> BlackboxBehaviorSpec:
        """Derives a BlackboxBehaviorSpec from a coupled mutation without leaking diff."""
        if mutation.touches_config:
            symptom = BehavioralSymptom(
                category=SymptomCategory.CONFIG_PARSE_FAILURE,
                description="Application fails initialization due to invalid configuration state",
                observed_exit_code=1,
                error_header="ConfigurationKeyError: Missing expected configuration property",
                sanitized_stderr_snippet="Service startup halted: configuration validation failed.",
            )
            narrative = (
                "After updating system configuration parameters, service bootstrapping "
                "fails immediately during environment startup."
            )
            expected = (
                "Service should cleanly start with provided parameters or fall back to defaults."
            )
            observed = "Initialization crashes with ConfigurationKeyError."
        else:
            symptom = BehavioralSymptom(
                category=SymptomCategory.RUNTIME_EXCEPTION,
                description="Workflow crashes unexpectedly during multi-stage pipeline execution",
                observed_exit_code=1,
                error_header="ContractViolationError: Incompatible parameter type encountered",
                sanitized_stderr_snippet="Pipeline execution failed during batch evaluation step.",
            )
            narrative = (
                "Running standard pipeline evaluation crashes unexpectedly on multi-module "
                "data exchange."
            )
            expected = "Pipeline evaluation completes and produces expected output summary."
            observed = "Execution fails with runtime error during data processing."

        return BlackboxBehaviorSpec(
            spec_id=f"spec_{mutation.mutation_id}",
            repo_name=repo_name,
            symptoms=[symptom],
            user_workflow_narrative=narrative,
            expected_outcome=expected,
            observed_outcome=observed,
            reproduction_script_content="from app import run_pipeline\nrun_pipeline()",
        )
