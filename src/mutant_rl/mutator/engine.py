"""Compound mutation execution engine and topology planner."""

from __future__ import annotations

import ast
import difflib

from mutant_rl.mutator.graph import DependencyGraphAnalyzer
from mutant_rl.mutator.operators import (
    BaseMutationOperator,
    ConfigCodeMismatchMutator,
    CrossFileContractMutator,
    SchemaMigrationMutator,
)
from mutant_rl.schemas.environment import FileNode, FileType
from mutant_rl.schemas.mutation import (
    CoupledMutation,
    MutationTopology,
)


class CompoundMutationEngine:
    """Orchestrates multi-file, coupled mutation generation with topology constraints."""

    def __init__(self, operators: list[BaseMutationOperator] | None = None) -> None:
        self.operators: list[BaseMutationOperator] = operators or [
            CrossFileContractMutator(),
            ConfigCodeMismatchMutator(),
            SchemaMigrationMutator(),
        ]
        self.graph_analyzer = DependencyGraphAnalyzer()

    def generate_compound_mutation(
        self, files: dict[str, FileNode], min_files: int = 2
    ) -> tuple[CoupledMutation | None, MutationTopology]:
        """Analyzes repo state and generates a verified compound mutation."""
        self.graph_analyzer.analyze_repository(files)

        selected_mutation: CoupledMutation | None = None
        for op in self.operators:
            if op.can_apply(files, self.graph_analyzer):
                mutation = op.mutate(files, self.graph_analyzer)
                if mutation and self._validate_mutation(mutation, files, min_files):
                    selected_mutation = mutation
                    break

        topology = self._build_topology(files, selected_mutation)
        return selected_mutation, topology

    def apply_mutation(
        self, files: dict[str, FileNode], mutation: CoupledMutation
    ) -> dict[str, str]:
        """Applies mutation targets to file contents and returns updated string mapping."""
        mutated_files = {p: node.content for p, node in files.items()}

        for target in mutation.targets:
            current_content = mutated_files.get(target.file_path, "")
            if not current_content:
                continue

            lines = current_content.splitlines()
            if 1 <= target.start_line <= len(lines):
                # Replace target line(s)
                before = lines[: target.start_line - 1]
                after = lines[target.end_line :]
                mutated_chunk = target.mutated_snippet.splitlines()
                new_lines = before + mutated_chunk + after
                mutated_files[target.file_path] = "\n".join(new_lines) + "\n"

        return mutated_files

    def generate_ground_truth_patch(
        self, original_files: dict[str, FileNode], mutated_contents: dict[str, str]
    ) -> str:
        """Computes the reverse unified diff patch that repairs the mutation back to clean code."""
        patch_chunks = []
        for path, orig_node in original_files.items():
            mut_content = mutated_contents.get(path, orig_node.content)
            if mut_content != orig_node.content:
                diff = difflib.unified_diff(
                    mut_content.splitlines(keepends=True),
                    orig_node.content.splitlines(keepends=True),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                )
                patch_chunks.extend(diff)
        return "".join(patch_chunks)

    def _validate_mutation(
        self, mutation: CoupledMutation, files: dict[str, FileNode], min_files: int
    ) -> bool:
        unique_paths = {t.file_path for t in mutation.targets}
        if len(unique_paths) < min_files:
            return False

        # Validate that mutated python files preserve AST parseability
        mutated_map = self.apply_mutation(files, mutation)
        for path in unique_paths:
            node = files.get(path)
            if node and node.file_type == FileType.PYTHON:
                content = mutated_map.get(path, "")
                try:
                    ast.parse(content, filename=path)
                except SyntaxError:
                    return False

        return True

    def _build_topology(
        self, files: dict[str, FileNode], mutation: CoupledMutation | None
    ) -> MutationTopology:
        code_nodes = [p for p, f in files.items() if f.file_type == FileType.PYTHON]
        config_nodes = [p for p, f in files.items() if f.is_config]

        edges = list(self.graph_analyzer.edges)
        total_possible_edges = max(1, len(files) * (len(files) - 1))
        density = min(1.0, len(edges) / total_possible_edges)

        spans_multi = False
        ratio = len(config_nodes) / max(1, len(code_nodes))

        if mutation:
            unique_paths = {t.file_path for t in mutation.targets}
            spans_multi = len(unique_paths) > 1

        return MutationTopology(
            environment_id=mutation.mutation_id if mutation else "none",
            primary_code_nodes=code_nodes,
            config_nodes=config_nodes,
            cross_file_edges=edges,
            graph_density=round(density, 3),
            spans_multi_file=spans_multi,
            config_code_ratio=round(ratio, 3),
        )
