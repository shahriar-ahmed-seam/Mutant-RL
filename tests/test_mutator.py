"""Unit tests for compound mutation engine and topology planner."""

from mutant_rl.mutator import (
    CompoundMutationEngine,
    ConfigCodeMismatchMutator,
    CrossFileContractMutator,
    DecoupledOracleSynthesizer,
    DependencyGraphAnalyzer,
)
from mutant_rl.schemas.environment import FileNode, FileType


def test_dependency_graph_analyzer():
    code_def = "def compute_metrics(threshold: float):\n    return {'score': threshold * 10}\n"
    code_caller = "def run_eval():\n    res = compute_metrics(0.5)\n    return res\n"
    files = {
        "src/calculator.py": FileNode(path="src/calculator.py", content=code_def),
        "src/runner.py": FileNode(path="src/runner.py", content=code_caller),
    }

    analyzer = DependencyGraphAnalyzer()
    analyzer.analyze_repository(files)

    assert ("src/runner.py", "src/calculator.py") in analyzer.edges
    assert len(analyzer.definitions["src/calculator.py"]) == 1
    assert analyzer.definitions["src/calculator.py"][0].symbol_name == "compute_metrics"


def test_cross_file_contract_mutator():
    code_def = "def compute_metrics(threshold: float):\n    return {'score': threshold * 10}\n"
    code_caller = "def run_eval():\n    res = compute_metrics(0.5)\n    return res\n"
    files = {
        "src/calculator.py": FileNode(path="src/calculator.py", content=code_def),
        "src/runner.py": FileNode(path="src/runner.py", content=code_caller),
    }

    engine = CompoundMutationEngine()
    mutation, topology = engine.generate_compound_mutation(files, min_files=2)

    assert mutation is not None
    assert mutation.touches_multiple_files is True
    assert mutation.is_compound is True
    assert topology.spans_multi_file is True
    assert len(mutation.targets) == 2

    # Check mutated application
    mutated_files = engine.apply_mutation(files, mutation)
    assert "enforce_strict: bool" in mutated_files["src/calculator.py"]

    # Check reverse ground truth patch
    patch = engine.generate_ground_truth_patch(files, mutated_files)
    assert "--- a/src/calculator.py" in patch
    assert "+++ b/src/calculator.py" in patch


def test_config_code_mismatch_mutator():
    config_yaml = "database:\n  timeout: 30\n  retries: 3\n"
    code_py = "import yaml\ndef get_conn():\n    val = 'timeout'\n    return val\n"
    files = {
        "config.yaml": FileNode(
            path="config.yaml",
            content=config_yaml,
            file_type=FileType.YAML,
            is_config=True,
        ),
        "src/db.py": FileNode(path="src/db.py", content=code_py, file_type=FileType.PYTHON),
    }

    analyzer = DependencyGraphAnalyzer()
    analyzer.analyze_repository(files)

    op = ConfigCodeMismatchMutator()
    assert op.can_apply(files, analyzer) is True

    mutation = op.mutate(files, analyzer)
    assert mutation is not None
    assert mutation.touches_config is True
    assert any(t.file_path == "config.yaml" for t in mutation.targets)


def test_decoupled_oracle_synthesizer():
    code_def = "def run_pipeline():\n    return 42\n"
    code_caller = "def main():\n    return run_pipeline()\n"
    files = {
        "src/core.py": FileNode(path="src/core.py", content=code_def),
        "src/main.py": FileNode(path="src/main.py", content=code_caller),
    }

    engine = CompoundMutationEngine(operators=[CrossFileContractMutator()])
    mutation, _ = engine.generate_compound_mutation(files, min_files=2)
    assert mutation is not None

    oracle_syn = DecoupledOracleSynthesizer()
    repro_test = oracle_syn.synthesize_reproduction_test(mutation, module_name="src.core")

    assert "test_contract_drift_run_pipeline_regression" in repro_test
    assert "Cross-module contract violation detected" in repro_test
