# Contributing to Mutant-RL

We welcome contributions to Mutant-RL. This document outlines the engineering standards, code review workflows, and testing requirements required for all pull requests.

---

## Code of Conduct and Standards

1. **Deterministic Testing**: Every contribution modifying core algorithms, mutation operators, leak detectors, or metric calculations must include deterministic unit tests (`pytest`).
2. **Strict Zero-Emoji Rule**: Documentation files (`README.md`, `docs/*`, `CONTRIBUTING.md`, `CHANGELOG.md`, `SECURITY.md`) must not contain emojis. Use formal technical terminology (e.g., `PASSED`, `FAILED`, `[Verified]`, `[Antipattern]`).
3. **Mermaid Blueprints**: System architectures and dataflow diagrams must be rendered using GitHub-flavored Mermaid (`mermaid`) rather than plain text or ASCII boxes.
4. **Anti-AI-Slop UI Standards**: Front-end components must adhere to Datadog/Grafana/Linear developer tool aesthetics (dark neutral canvas `#090b0e`, 1px hairline borders `rgba(255, 255, 255, 0.08)`, sharp border radii, monospace badges, zero glowing gradient blobs).

---

## Development Setup

```bash
git clone https://github.com/shahriar-ahmed-seam/Mutant-RL.git
cd Mutant-RL
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

---

## Quality Assurance Workflow

Before opening a pull request, verify that all linters and test suites pass:

```bash
# Run test suite
pytest -v

# Run linter and formatter checks
ruff check src tests examples
ruff format --check src tests examples
```

---

## Commit and Pull Request Conventions

1. Work strictly on descriptive topic branches off `main` (`feat/...`, `fix/...`, `docs/...`).
2. Prefix commit messages with standard Conventional Commit tags:
   - `feat(mutator): ...`
   - `fix(evaluator): ...`
   - `docs(core): ...`
   - `test(sanitizer): ...`
3. Reference corresponding issue numbers in pull request descriptions.
