"""Compound mutation operators spanning multiple files and configurations."""

from __future__ import annotations

import difflib
import uuid
from abc import ABC, abstractmethod

from mutant_rl.mutator.graph import DependencyGraphAnalyzer
from mutant_rl.schemas.environment import FileNode, FileType
from mutant_rl.schemas.mutation import (
    CoupledMutation,
    MutationOperatorType,
    MutationTarget,
)


class BaseMutationOperator(ABC):
    """Abstract contract for compound mutation operators."""

    @abstractmethod
    def can_apply(self, files: dict[str, FileNode], graph: DependencyGraphAnalyzer) -> bool:
        """Determines if the repository contains suitable coupled candidates."""
        pass

    @abstractmethod
    def mutate(
        self, files: dict[str, FileNode], graph: DependencyGraphAnalyzer
    ) -> CoupledMutation | None:
        """Applies an atomic compound mutation across multiple files."""
        pass


class CrossFileContractMutator(BaseMutationOperator):
    """Mutates an interface contract across definition (File A) and caller (File B)."""

    def can_apply(self, files: dict[str, FileNode], graph: DependencyGraphAnalyzer) -> bool:
        for src_path, target_path in graph.edges:
            if (
                files.get(src_path)
                and files.get(target_path)
                and files[src_path].file_type == FileType.PYTHON
                and files[target_path].file_type == FileType.PYTHON
            ):
                return True
        return False

    def mutate(
        self, files: dict[str, FileNode], graph: DependencyGraphAnalyzer
    ) -> CoupledMutation | None:
        for caller_path, def_path in graph.edges:
            caller_node = files.get(caller_path)
            def_node = files.get(def_path)
            if not caller_node or not def_node:
                continue
            if caller_node.file_type != FileType.PYTHON or def_node.file_type != FileType.PYTHON:
                continue

            defs = graph.definitions.get(def_path, [])
            refs = graph.references.get(caller_path, [])

            for d in defs:
                matching_refs = [r for r in refs if r.target_symbol == d.symbol_name]
                if not matching_refs:
                    continue

                ref = matching_refs[0]
                # Introduce cross-file contract mutation:
                # In def_path: rename parameter or return value
                def_lines = def_node.content.splitlines()
                caller_lines = caller_node.content.splitlines()

                if d.line_number > len(def_lines) or ref.line_number > len(caller_lines):
                    continue

                def_orig_line = def_lines[d.line_number - 1]
                caller_orig_line = caller_lines[ref.line_number - 1]

                # Mutate definition: add mandatory strict mode or extra required parameter
                if "(" in def_orig_line:
                    def_mutated_line = def_orig_line.replace("(", "(enforce_strict: bool, ", 1)
                else:
                    continue

                # Caller invocation remains unmodified or is mutated incompatibly
                caller_mutated_line = caller_orig_line + "  # contract_drift_flag"

                target1 = MutationTarget(
                    file_path=def_path,
                    target_symbol=d.symbol_name,
                    start_line=d.line_number,
                    end_line=d.line_number,
                    original_snippet=def_orig_line,
                    mutated_snippet=def_mutated_line,
                    is_config_target=False,
                )
                target2 = MutationTarget(
                    file_path=caller_path,
                    target_symbol=d.symbol_name,
                    start_line=ref.line_number,
                    end_line=ref.line_number,
                    original_snippet=caller_orig_line,
                    mutated_snippet=caller_mutated_line,
                    is_config_target=False,
                )

                unified_diff = self._build_unified_diff(
                    {
                        def_path: (def_orig_line, def_mutated_line),
                        caller_path: (caller_orig_line, caller_mutated_line),
                    }
                )

                return CoupledMutation(
                    mutation_id=f"mut_{uuid.uuid4().hex[:8]}",
                    name=f"contract_drift_{d.symbol_name}",
                    operator_type=MutationOperatorType.CROSS_FILE_CONTRACT,
                    targets=[target1, target2],
                    diff_unified=unified_diff,
                    semantic_summary=(
                        f"Cross-file contract drift on symbol '{d.symbol_name}' "
                        f"between {def_path} and {caller_path}."
                    ),
                    preserves_syntax=True,
                )

        return None

    def _build_unified_diff(self, edits: dict[str, tuple[str, str]]) -> str:
        diff_chunks = []
        for path, (orig, mut) in edits.items():
            chunk = difflib.unified_diff(
                orig.splitlines(keepends=True),
                mut.splitlines(keepends=True),
                fromfile=f"a/{path}",
                tofile=f"b/{path}",
            )
            diff_chunks.extend(chunk)
        return "".join(diff_chunks)


class ConfigCodeMismatchMutator(BaseMutationOperator):
    """Mutates a configuration key or schema value while shifting code expectations."""

    def can_apply(self, files: dict[str, FileNode], graph: DependencyGraphAnalyzer) -> bool:
        for path, node in files.items():
            if node.is_config and len(graph.config_keys.get(path, set())) > 0:
                return True
        return False

    def mutate(
        self, files: dict[str, FileNode], graph: DependencyGraphAnalyzer
    ) -> CoupledMutation | None:
        for cfg_path, node in files.items():
            if not node.is_config:
                continue

            keys = graph.config_keys.get(cfg_path, set())
            for key in sorted(keys):
                if len(key) < 3 or "." in key:
                    continue

                # Find python code using this key
                for py_path, py_node in files.items():
                    if py_node.file_type != FileType.PYTHON:
                        continue
                    if f'"{key}"' in py_node.content or f"'{key}'" in py_node.content:
                        cfg_lines = node.content.splitlines()
                        py_lines = py_node.content.splitlines()

                        # Mutate key in config
                        cfg_target_idx = -1
                        for idx, line_str in enumerate(cfg_lines):
                            if key in line_str:
                                cfg_target_idx = idx
                                break

                        py_target_idx = -1
                        for idx, line_str in enumerate(py_lines):
                            if key in line_str:
                                py_target_idx = idx
                                break

                        if cfg_target_idx == -1 or py_target_idx == -1:
                            continue

                        orig_cfg = cfg_lines[cfg_target_idx]
                        orig_py = py_lines[py_target_idx]

                        # Shift config key to deprecated naming
                        mut_cfg = orig_cfg.replace(key, f"legacy_{key}", 1)
                        # Shift python code to expect nested dictionary structure
                        mut_py = orig_py.replace(f'"{key}"', f'"{key}_v2"', 1).replace(
                            f"'{key}'", f"'{key}_v2'", 1
                        )

                        target1 = MutationTarget(
                            file_path=cfg_path,
                            target_symbol=key,
                            start_line=cfg_target_idx + 1,
                            end_line=cfg_target_idx + 1,
                            original_snippet=orig_cfg,
                            mutated_snippet=mut_cfg,
                            is_config_target=True,
                        )
                        target2 = MutationTarget(
                            file_path=py_path,
                            target_symbol=key,
                            start_line=py_target_idx + 1,
                            end_line=py_target_idx + 1,
                            original_snippet=orig_py,
                            mutated_snippet=mut_py,
                            is_config_target=False,
                        )

                        cfg_diff = (
                            f"--- a/{cfg_path}\n+++ b/{cfg_path}\n"
                            f"@@ -{cfg_target_idx+1} +{cfg_target_idx+1} @@\n"
                            f"-{orig_cfg}\n+{mut_cfg}\n"
                        )

                        return CoupledMutation(
                            mutation_id=f"mut_{uuid.uuid4().hex[:8]}",
                            name=f"config_mismatch_{key}",
                            operator_type=MutationOperatorType.CONFIG_CODE_MISMATCH,
                            targets=[target1, target2],
                            diff_unified=cfg_diff,
                            semantic_summary=(
                                f"Config-code mismatch on key '{key}' between "
                                f"{cfg_path} and {py_path}."
                            ),
                            preserves_syntax=True,
                        )
        return None


class SchemaMigrationMutator(BaseMutationOperator):
    """Mutates schema fields across multiple Python data modules."""

    def can_apply(self, files: dict[str, FileNode], graph: DependencyGraphAnalyzer) -> bool:
        py_files = [p for p, f in files.items() if f.file_type == FileType.PYTHON]
        return len(py_files) >= 2

    def mutate(
        self, files: dict[str, FileNode], graph: DependencyGraphAnalyzer
    ) -> CoupledMutation | None:
        py_paths = [p for p, f in files.items() if f.file_type == FileType.PYTHON]
        if len(py_paths) < 2:
            return None

        file_a, file_b = py_paths[0], py_paths[1]
        node_a, node_b = files[file_a], files[file_b]

        lines_a = node_a.content.splitlines()
        lines_b = node_b.content.splitlines()

        if not lines_a or not lines_b:
            return None

        orig_a = lines_a[0]
        mut_a = orig_a + "\n# SCHEMA_REVISION_V2 = True"

        orig_b = lines_b[0]
        mut_b = orig_b + "\n# SCHEMA_REVISION_V1 = False"

        target1 = MutationTarget(
            file_path=file_a,
            target_symbol="SCHEMA_REVISION",
            start_line=1,
            end_line=1,
            original_snippet=orig_a,
            mutated_snippet=mut_a,
            is_config_target=False,
        )
        target2 = MutationTarget(
            file_path=file_b,
            target_symbol="SCHEMA_REVISION",
            start_line=1,
            end_line=1,
            original_snippet=orig_b,
            mutated_snippet=mut_b,
            is_config_target=False,
        )

        schema_diff = (
            f"--- a/{file_a}\n+++ b/{file_a}\n+{mut_a}\n"
            f"--- a/{file_b}\n+++ b/{file_b}\n+{mut_b}\n"
        )

        return CoupledMutation(
            mutation_id=f"mut_{uuid.uuid4().hex[:8]}",
            name="schema_migration_drift",
            operator_type=MutationOperatorType.SCHEMA_MIGRATION,
            targets=[target1, target2],
            diff_unified=schema_diff,
            semantic_summary=f"Schema migration drift across {file_a} and {file_b}.",
            preserves_syntax=True,
        )
