# Canonical Schema Specification (RFC-MRL-001)

This specification defines the canonical data protocols, field types, serialization invariants, and validation rules governing Mutant-RL environments and telemetry pipelines.

---

## 1. Environment Specification

### `EnvironmentInstance`
Represents an instantiated software engineering task environment ready for agent rollout execution.

| Field | Type | Required | Description | Validation Rule |
|---|---|---|---|---|
| `instance_id` | `string` | Yes | Unique task identifier | Non-empty ASCII string |
| `repo_name` | `string` | Yes | Repository namespace identifier | Format: `org/repo` |
| `base_commit` | `string` | Yes | Git base commit SHA or reference | Non-empty string |
| `instance_type` | `InstanceType` | Yes | Source classification: `synthetic` or `real_pr` | Enum member |
| `problem_statement` | `string` | Yes | User-visible task description | Must pass leak quarantine |
| `files` | `map<string, string>` | Yes | Relative paths to modified file contents | Path cannot be absolute |
| `patch` | `string` | Yes | Unified diff repair patch | Standard unified diff format |
| `test_patch` | `string` | Yes | Reproduction regression test patch | Valid Python syntax |
| `oracle_command` | `string` | Yes | Shell command to execute test oracle | Default: `pytest` |
| `metadata` | `map<string, any>` | No | Auxiliary pipeline telemetry | Key-value mapping |

---

## 2. Mutation and Topology Specification

### `CoupledMutation`
Represents an atomic compound mutation spanning multiple files or code-configuration interfaces.

| Field | Type | Required | Description | Invariant |
|---|---|---|---|---|
| `mutation_id` | `string` | Yes | Unique mutation identifier | Prefix: `mut_` |
| `name` | `string` | Yes | Descriptive operator label | Alphanumeric snake_case |
| `operator_type` | `MutationOperatorType` | Yes | Category of semantic operator | Valid enum member |
| `targets` | `list<MutationTarget>` | Yes | Discrete edit locations | Length $\ge 1$ |
| `diff_unified` | `string` | Yes | Combined unified diff across all targets | Valid diff header |
| `semantic_summary` | `string` | Yes | High-level summary of introduced regression | Non-empty |
| `preserves_syntax` | `boolean` | Yes | Whether all target files retain AST parseability | Must be `true` |

### `MutationTopology`
Represents the structural graph properties of the mutated codebase.

| Field | Type | Range | Description |
|---|---|---|---|
| `environment_id` | `string` | - | Target task ID |
| `primary_code_nodes` | `list<string>` | - | Source code files involved |
| `config_nodes` | `list<string>` | - | Configuration files involved |
| `cross_file_edges` | `list<tuple<string, string>>` | - | Dependency call edges between nodes |
| `graph_density` | `float` | $[0.0, 1.0]$ | Density of the dependency subgraph |
| `spans_multi_file` | `boolean` | - | Enforces multi-file span constraint |
| `config_code_ratio` | `float` | $\ge 0.0$ | Ratio of config nodes to code nodes |

---

## 3. Leakage Detection and Quarantine Specification

### `DiffFingerprint`
Quantitative measurements of inadvertent diff leakage in problem statements.

| Metric | Type | Valid Range | Quarantine Threshold |
|---|---|---|---|
| `n_gram_overlap_score` | `float` | $[0.0, 1.0]$ | $\le 0.25$ |
| `token_jaccard_score` | `float` | $[0.0, 1.0]$ | $\le 0.30$ |
| `symbol_leak_count` | `integer` | $\ge 0$ | $== 0$ |
| `line_number_leak_count` | `integer` | $\ge 0$ | $== 0$ |
| `patch_reconstruction_risk` | `float` | $[0.0, 1.0]$ | $\le 0.40$ |
| `passes_leak_quarantine` | `boolean` | - | Must satisfy all above |

---

## 4. Policy Trajectory and Telemetry Specification

### `PolicyTrajectory`
Execution trace of an agent attempting to solve an environment task.

| Field | Type | Description |
|---|---|---|
| `trajectory_id` | `string` | Rollout execution ID |
| `instance_id` | `string` | Associated environment task ID |
| `agent_model` | `string` | Model checkpoint identifier |
| `steps` | `list<ActionStep>` | Sequence of executed tool calls |
| `resolved` | `boolean` | Whether test harness passed |
| `reward` | `float` | Rollout reward value $\in [0.0, 1.0]$ |
| `wall_time_seconds` | `float` | Total rollout execution duration |
| `shortcut_metrics` | `ShortcutHeuristicMetrics` | Measured shortcut exploitation index |

### `SimToRealMetrics`
Consolidated telemetry monitoring sim-to-real divergence.

| Field | Type | Description | Alert Condition |
|---|---|---|---|
| `evaluation_window` | `integer` | Sample size of evaluated tasks | $N \ge 50$ |
| `synthetic_resolve_rate` | `float` | $\rho_{\text{synth}}$ resolution percentage | - |
| `real_pr_resolve_rate` | `float` | $\rho_{\text{real}}$ resolution percentage | - |
| `sim_to_real_gap` | `float` | $\Delta = \rho_{\text{synth}} - \rho_{\text{real}}$ | $> 0.25 \implies$ STOP |
| `wasserstein_action_divergence` | `float` | Action distribution Total Variation | $> 0.35 \implies$ STOP |
| `shortcut_learning_index` | `float` | Aggregate heuristic exploit rate | $> 0.45 \implies$ STOP |
| `stopping_signal_triggered` | `boolean` | Emergency training stop signal | Active when any bound breached |
