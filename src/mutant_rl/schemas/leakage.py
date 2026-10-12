"""Leakage detection and fingerprint audit schemas."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class LeakageType(StrEnum):
    """Classification of generator fingerprint leakage."""
    EXACT_SYMBOL_PATH = "exact_symbol_path"
    DIFF_PATCH_VERBATIM = "diff_patch_verbatim"
    LINE_NUMBER_SPECIFICATION = "line_number_specification"
    INTERNAL_GENERATOR_PROMPT = "internal_generator_prompt"
    FIX_RECIPE_ECHO = "fix_recipe_echo"
    HIGH_NGRAM_OVERLAP = "high_ngram_overlap"


class DetectedLeak(BaseModel):
    """Specific leakage instance found in problem statement."""
    leak_type: LeakageType
    token_or_phrase: str
    severity: float = Field(ge=0.0, le=1.0)
    context_window: str


class DiffFingerprint(BaseModel):
    """Quantitative fingerprint metrics measuring diff text leakage in problem statement."""
    n_gram_overlap_score: float = Field(
        ge=0.0, le=1.0, description="3-gram/4-gram overlap with patch"
    )
    token_jaccard_score: float = Field(ge=0.0, le=1.0, description="Token set overlap with patch")
    symbol_leak_count: int = Field(default=0, ge=0)
    line_number_leak_count: int = Field(default=0, ge=0)
    patch_reconstruction_risk: float = Field(ge=0.0, le=1.0)
    passes_leak_quarantine: bool = True


class LeakAuditReport(BaseModel):
    """Comprehensive leakage audit for a synthesized issue statement."""
    instance_id: str
    fingerprint: DiffFingerprint
    detected_leaks: list[DetectedLeak] = Field(default_factory=list)
    is_compromised: bool = False
    quarantine_action: str = "allow"  # allow, sanitize, reject
    sanitized_statement: str | None = None
