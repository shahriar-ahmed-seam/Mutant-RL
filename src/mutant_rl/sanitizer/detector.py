"""Diff fingerprint leak detection across problem statements and patches."""

from __future__ import annotations

import re

from mutant_rl.schemas.leakage import (
    DetectedLeak,
    DiffFingerprint,
    LeakageType,
)


class DiffFingerprintLeakDetector:
    """Analyzes problem statement text for inadvertent diff leakage or fix clues."""

    def __init__(self, max_allowed_ngram_overlap: float = 0.25, max_allowed_jaccard: float = 0.30):
        self.max_allowed_ngram_overlap = max_allowed_ngram_overlap
        self.max_allowed_jaccard = max_allowed_jaccard

    def audit_statement(
        self, problem_statement: str, patch_unified: str
    ) -> tuple[DiffFingerprint, list[DetectedLeak]]:
        """Audits statement text against ground-truth patch."""
        detected_leaks: list[DetectedLeak] = []

        # 1. Extract patch tokens and symbols
        patch_tokens, patch_symbols = self._extract_patch_tokens_and_symbols(patch_unified)
        statement_tokens = self._tokenize(problem_statement)

        # 2. Token Jaccard overlap
        if statement_tokens and patch_tokens:
            intersection = statement_tokens.intersection(patch_tokens)
            union = statement_tokens.union(patch_tokens)
            jaccard_score = round(len(intersection) / max(1, len(union)), 4)
        else:
            jaccard_score = 0.0

        # 3. 3-gram and 4-gram overlap
        ngram_score = self._compute_ngram_overlap(problem_statement, patch_unified)

        # 4. Symbol path and direct identifier leakage
        symbol_leaks = 0
        statement_lower = problem_statement.lower()
        for symbol in patch_symbols:
            if len(symbol) > 3 and symbol.lower() in statement_lower:
                symbol_leaks += 1
                detected_leaks.append(
                    DetectedLeak(
                        leak_type=LeakageType.EXACT_SYMBOL_PATH,
                        token_or_phrase=symbol,
                        severity=0.85,
                        context_window=self._extract_context(problem_statement, symbol),
                    )
                )

        # 5. Line number and file path leakage
        line_num_leaks = 0
        line_patterns = re.findall(r"(?:line|lines)\s+(\d+)", problem_statement, re.IGNORECASE)
        for num in line_patterns:
            line_num_leaks += 1
            detected_leaks.append(
                DetectedLeak(
                    leak_type=LeakageType.LINE_NUMBER_SPECIFICATION,
                    token_or_phrase=f"line {num}",
                    severity=0.70,
                    context_window=f"Mentioned line {num}",
                )
            )

        # 6. Patch reconstruction risk
        risk = min(
            1.0,
            (ngram_score * 0.4)
            + (jaccard_score * 0.3)
            + (min(1.0, symbol_leaks * 0.2))
            + (min(0.2, line_num_leaks * 0.1)),
        )

        passes = (
            ngram_score <= self.max_allowed_ngram_overlap
            and jaccard_score <= self.max_allowed_jaccard
            and symbol_leaks == 0
            and line_num_leaks == 0
        )

        fingerprint = DiffFingerprint(
            n_gram_overlap_score=ngram_score,
            token_jaccard_score=jaccard_score,
            symbol_leak_count=symbol_leaks,
            line_number_leak_count=line_num_leaks,
            patch_reconstruction_risk=round(risk, 4),
            passes_leak_quarantine=passes,
        )

        return fingerprint, detected_leaks

    def _tokenize(self, text: str) -> set[str]:
        words = re.findall(r"[a-zA-Z0-9_]{3,}", text)
        return {w.lower() for w in words}

    def _extract_patch_tokens_and_symbols(self, patch: str) -> tuple[set[str], set[str]]:
        added_lines = [
            line[1:].strip()
            for line in patch.splitlines()
            if line.startswith("+") and not line.startswith("+++")
        ]
        text = " ".join(added_lines)
        tokens = self._tokenize(text)

        # Extract explicit python function or class names
        symbols = set(re.findall(r"(?:def|class)\s+([a-zA-Z0-9_]+)", text))
        # Extract variables in assignments
        symbols.update(re.findall(r"([a-zA-Z0-9_]+)\s*=", text))

        return tokens, symbols

    def _compute_ngram_overlap(self, text_a: str, text_b: str, n: int = 3) -> float:
        words_a = re.findall(r"[a-zA-Z0-9_]+", text_a.lower())
        words_b = re.findall(r"[a-zA-Z0-9_]+", text_b.lower())

        if len(words_a) < n or len(words_b) < n:
            return 0.0

        ngrams_a = {tuple(words_a[i : i + n]) for i in range(len(words_a) - n + 1)}
        ngrams_b = {tuple(words_b[i : i + n]) for i in range(len(words_b) - n + 1)}

        overlap = ngrams_a.intersection(ngrams_b)
        return round(len(overlap) / max(1, len(ngrams_a)), 4)

    def _extract_context(self, text: str, token: str, window: int = 30) -> str:
        idx = text.lower().find(token.lower())
        if idx == -1:
            return token
        start = max(0, idx - window)
        end = min(len(text), idx + len(token) + window)
        return text[start:end].strip()
