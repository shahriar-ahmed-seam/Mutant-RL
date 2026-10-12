"""Leak quarantine management and problem statement sanitization."""

from __future__ import annotations

import re

from mutant_rl.sanitizer.detector import DiffFingerprintLeakDetector
from mutant_rl.schemas.leakage import LeakAuditReport


class LeakQuarantineManager:
    """Evaluates problem statements against patches and quarantines leaked tasks."""

    def __init__(self, detector: DiffFingerprintLeakDetector | None = None) -> None:
        self.detector = detector or DiffFingerprintLeakDetector()

    def audit_and_quarantine(
        self, instance_id: str, problem_statement: str, patch_unified: str
    ) -> LeakAuditReport:
        """Performs quarantine evaluation and applies sanitization when possible."""
        fingerprint, leaks = self.detector.audit_statement(problem_statement, patch_unified)

        if fingerprint.passes_leak_quarantine:
            return LeakAuditReport(
                instance_id=instance_id,
                fingerprint=fingerprint,
                detected_leaks=leaks,
                is_compromised=False,
                quarantine_action="allow",
                sanitized_statement=problem_statement,
            )

        # Attempt automated sanitization of leaked tokens
        sanitized = problem_statement
        for leak in leaks:
            escaped = re.escape(leak.token_or_phrase)
            sanitized = re.sub(
                escaped, "[REDACTED_SYMBOL]", sanitized, flags=re.IGNORECASE
            )

        # Re-audit sanitized statement
        re_fingerprint, _ = self.detector.audit_statement(sanitized, patch_unified)

        if re_fingerprint.passes_leak_quarantine:
            return LeakAuditReport(
                instance_id=instance_id,
                fingerprint=re_fingerprint,
                detected_leaks=leaks,
                is_compromised=False,
                quarantine_action="sanitize",
                sanitized_statement=sanitized,
            )

        # Unsalvageable leak: reject from training corpus
        return LeakAuditReport(
            instance_id=instance_id,
            fingerprint=fingerprint,
            detected_leaks=leaks,
            is_compromised=True,
            quarantine_action="reject",
            sanitized_statement=None,
        )
