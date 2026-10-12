"""Unit tests for sanitizer, leak detector, and quarantine manager."""

from mutant_rl.sanitizer import (
    BehavioralIssueSynthesizer,
    DiffFingerprintLeakDetector,
    LeakQuarantineManager,
)
from mutant_rl.schemas.behavior import (
    BehavioralSymptom,
    BlackboxBehaviorSpec,
    SymptomCategory,
)
from mutant_rl.schemas.mutation import (
    CoupledMutation,
    MutationOperatorType,
    MutationTarget,
)


def test_diff_fingerprint_leak_detector_clean():
    clean_statement = (
        "Client crashes with ConnectionError during execution of the data batch job. "
        "Expected the process to retry or log an error gracefully."
    )
    patch = (
        "--- a/src/net.py\n+++ b/src/net.py\n"
        "@@ -10,1 +10,1 @@\n"
        "-def dispatch_socket(timeout=0):\n"
        "+def dispatch_socket(timeout=30):\n"
    )

    detector = DiffFingerprintLeakDetector()
    fingerprint, leaks = detector.audit_statement(clean_statement, patch)

    assert fingerprint.passes_leak_quarantine is True
    assert fingerprint.symbol_leak_count == 0
    assert len(leaks) == 0


def test_diff_fingerprint_leak_detector_detected():
    leaked_statement = "Please fix dispatch_socket on line 10 in src/net.py by setting timeout=30"
    patch = (
        "--- a/src/net.py\n+++ b/src/net.py\n"
        "@@ -10,1 +10,1 @@\n"
        "-def dispatch_socket(timeout=0):\n"
        "+def dispatch_socket(timeout=30):\n"
    )

    detector = DiffFingerprintLeakDetector()
    fingerprint, leaks = detector.audit_statement(leaked_statement, patch)

    assert fingerprint.passes_leak_quarantine is False
    assert fingerprint.symbol_leak_count > 0
    assert fingerprint.line_number_leak_count > 0
    assert len(leaks) > 0


def test_behavioral_issue_synthesizer():
    symptom = BehavioralSymptom(
        category=SymptomCategory.RUNTIME_EXCEPTION,
        description="Unhandled exception during stream processing",
        observed_exit_code=1,
        error_header="StreamClosedError: Connection reset by peer",
    )
    spec = BlackboxBehaviorSpec(
        spec_id="spec_101",
        repo_name="org/streamer",
        symptoms=[symptom],
        user_workflow_narrative="Running stream_consume() fails midway through payload transfer",
        expected_outcome="Stream completes without premature teardown",
        observed_outcome="Terminates with exit code 1",
    )

    synthesizer = BehavioralIssueSynthesizer()
    issue_text = synthesizer.synthesize_from_spec(spec)

    assert "# Bug Report: Observed Regression in org/streamer" in issue_text
    assert "StreamClosedError: Connection reset by peer" in issue_text
    assert "stream_consume()" in issue_text


def test_leak_quarantine_manager_actions():
    manager = LeakQuarantineManager()
    patch = (
        "--- a/src/core.py\n+++ b/src/core.py\n"
        "@@ -5,1 +5,1 @@\n"
        "-def compute_total(val):\n"
        "+def compute_total(val, strict=True):\n"
    )

    clean_text = "The application exits with code 1 when processing numerical arrays."
    report_clean = manager.audit_and_quarantine("task_1", clean_text, patch)
    assert report_clean.quarantine_action == "allow"
    assert report_clean.is_compromised is False

    leaked_text = "There is a bug in compute_total causing problems."
    report_leaked = manager.audit_and_quarantine("task_2", leaked_text, patch)
    assert report_leaked.quarantine_action in ("sanitize", "reject")


def test_synthesizer_from_coupled_mutation():
    target = MutationTarget(
        file_path="src/service.py",
        target_symbol="execute",
        start_line=1,
        end_line=2,
        original_snippet="orig",
        mutated_snippet="mut",
    )
    mutation = CoupledMutation(
        mutation_id="mut_test_01",
        name="test_contract_drift",
        operator_type=MutationOperatorType.CROSS_FILE_CONTRACT,
        targets=[target],
        diff_unified="diff",
        semantic_summary="summary",
    )

    synthesizer = BehavioralIssueSynthesizer()
    spec = synthesizer.synthesize_from_coupled_mutation("org/service", mutation)

    assert spec.repo_name == "org/service"
    assert len(spec.symptoms) == 1
    assert spec.symptoms[0].observed_exit_code == 1
