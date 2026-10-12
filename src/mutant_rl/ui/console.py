"""Anti-AI-Slop Telemetry Console HTML loader."""

from __future__ import annotations

from pathlib import Path


def get_console_html() -> str:
    """Returns the Anti-AI-Slop Developer Telemetry Console HTML."""
    template_path = Path(__file__).parent / "templates" / "console.html"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    return "<!DOCTYPE html><html><body>Mutant-RL Console</body></html>"
