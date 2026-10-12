# Changelog

All notable changes to Mutant-RL are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] - 2026-10-12

### Added
- Foundation architecture and canonical Pydantic v2 domain schemas (`EnvironmentInstance`, `CoupledMutation`, `DiffFingerprint`, `BlackboxBehaviorSpec`, `PolicyTrajectory`, `SimToRealMetrics`).
- Compound mutation engine with `CrossFileContractMutator`, `ConfigCodeMismatchMutator`, and `SchemaMigrationMutator`.
- Dependency graph analyzer extracting cross-module call edges and YAML/TOML/JSON configuration bindings.
- Decoupled regression test oracle synthesizer eliminating coverage bias.
- Multi-tier diff fingerprint leak detector evaluating n-gram overlap, lexical Jaccard distance, AST symbol leakage, and line number disclosures.
- Behavioral issue synthesizer deriving blackbox issue prompts from observed runtime symptoms without diff leakage.
- Automated leak quarantine manager with redaction and rejection mechanisms.
- Trajectory evaluation engine computing Total Variation action distribution divergence ($D_{\text{TV}}$) and shortcut exploitation indices ($I_{\text{shortcut}}$).
- Sim-to-Real gap auditor tracking transfer drift and firing automated emergency stopping signals.
- Empirical real PR anchor calibrator tuning mutation operator weights.
- `mutant-rl` Typer CLI featuring Rich tables and status telemetry for generation, leak auditing, trajectory auditing, and service hosting.
- High-throughput FastAPI REST API server with OpenAPI endpoints (`/health`, `/api/metrics`, `/api/generate`, `/api/audit/leak`, `/api/audit/trajectories`).
- Anti-AI-slop developer telemetry console conforming to Datadog/Grafana developer standards.
- Dockerfile and docker-compose.yml container orchestration.
- Comprehensive deterministic test suite achieving 100% test pass rate.
