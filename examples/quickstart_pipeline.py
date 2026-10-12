"""Quickstart demonstration of Mutant-RL end-to-end environment synthesis."""

from __future__ import annotations

from mutant_rl.pipeline import MutantPipeline
from mutant_rl.schemas.environment import FileNode, FileType


def main() -> None:
    # 1. Define sample repository components
    calculator_code = (
        "def compute_score(base_val: float, multiplier: float = 1.0) -> dict[str, float]:\n"
        "    return {'score': base_val * multiplier}\n"
    )
    runner_code = (
        "from src.calculator import compute_score\n"
        "\n"
        "def execute_job():\n"
        "    res = compute_score(10.0)\n"
        "    return res['score']\n"
    )
    config_yaml = "job:\n  multiplier: 2.5\n  timeout: 30\n"

    repo_files = {
        "src/calculator.py": FileNode(path="src/calculator.py", content=calculator_code),
        "src/runner.py": FileNode(path="src/runner.py", content=runner_code),
        "config.yaml": FileNode(
            path="config.yaml",
            content=config_yaml,
            file_type=FileType.YAML,
            is_config=True,
        ),
    }

    # 2. Run MutantPipeline synthesis
    pipeline = MutantPipeline()
    instance, audit, topology = pipeline.synthesize_calibrated_instance(
        repo_name="org/compute-service",
        files=repo_files,
        min_files=2,
    )

    if not instance:
        print("Synthesis failed to satisfy topology invariants.")
        return

    print("Synthesis Successful")
    print(f"Instance ID: {instance.instance_id}")
    print(f"Spans Multi-File: {topology.spans_multi_file}")
    print(f"Code/Config Ratio: {topology.config_code_ratio:.2f}")
    if audit:
        print(f"Quarantine Action: {audit.quarantine_action.upper()}")
        print(f"Diff N-Gram Overlap: {audit.fingerprint.n_gram_overlap_score:.2%}")

    print("\n--- Synthesized Problem Statement (Sample) ---")
    print("\n".join(instance.problem_statement.splitlines()[:10]))


if __name__ == "__main__":
    main()
