"""Dependency graph analysis across Python source code and configuration files."""

from __future__ import annotations

import ast
import json
import re
from dataclasses import dataclass, field

import yaml

from mutant_rl.schemas.environment import FileNode, FileType


@dataclass
class SymbolDefinition:
    """Represents a defined function, class, or variable symbol."""

    file_path: str
    symbol_name: str
    symbol_type: str  # "function", "class", "variable"
    line_number: int
    arguments: list[str] = field(default_factory=list)


@dataclass
class SymbolReference:
    """Represents a reference/call to a symbol."""

    file_path: str
    target_symbol: str
    line_number: int


class DependencyGraphAnalyzer:
    """Extracts call graphs, import graphs, and configuration key dependencies."""

    def __init__(self) -> None:
        self.definitions: dict[str, list[SymbolDefinition]] = {}
        self.references: dict[str, list[SymbolReference]] = {}
        self.config_keys: dict[str, set[str]] = {}
        self.edges: set[tuple[str, str]] = set()

    def analyze_repository(self, files: dict[str, FileNode]) -> None:
        """Parses all files to extract multi-file and config relationships."""
        self.definitions.clear()
        self.references.clear()
        self.config_keys.clear()
        self.edges.clear()

        for path, file_node in files.items():
            if file_node.file_type == FileType.PYTHON:
                self._parse_python_file(path, file_node.content)
            elif file_node.file_type in (FileType.YAML, FileType.JSON, FileType.TOML):
                self._parse_config_file(path, file_node.content, file_node.file_type)

        self._build_cross_file_edges(files)

    def _parse_python_file(self, file_path: str, source_code: str) -> None:
        defs: list[SymbolDefinition] = []
        refs: list[SymbolReference] = []

        try:
            tree = ast.parse(source_code, filename=file_path)
        except SyntaxError:
            return

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                args = [a.arg for a in node.args.args]
                defs.append(
                    SymbolDefinition(
                        file_path=file_path,
                        symbol_name=node.name,
                        symbol_type="function",
                        line_number=node.lineno,
                        arguments=args,
                    )
                )
            elif isinstance(node, ast.ClassDef):
                defs.append(
                    SymbolDefinition(
                        file_path=file_path,
                        symbol_name=node.name,
                        symbol_type="class",
                        line_number=node.lineno,
                    )
                )
            elif isinstance(node, ast.Call):
                name = ""
                if isinstance(node.func, ast.Name):
                    name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    name = node.func.attr
                if name:
                    refs.append(
                        SymbolReference(
                            file_path=file_path,
                            target_symbol=name,
                            line_number=node.lineno,
                        )
                    )

        self.definitions[file_path] = defs
        self.references[file_path] = refs

    def _parse_config_file(self, file_path: str, content: str, file_type: FileType) -> None:
        keys: set[str] = set()
        try:
            if file_type == FileType.JSON:
                data = json.loads(content)
                self._collect_keys(data, keys)
            elif file_type == FileType.YAML:
                data = yaml.safe_load(content)
                if isinstance(data, dict):
                    self._collect_keys(data, keys)
            elif file_type == FileType.TOML:
                # Basic line-based key extraction for TOML
                for line in content.splitlines():
                    match = re.match(r"^([a-zA-Z0-9_\-]+)\s*=", line.strip())
                    if match:
                        keys.add(match.group(1))
        except Exception:
            pass

        self.config_keys[file_path] = keys

    def _collect_keys(self, obj: object, keys: set[str], prefix: str = "") -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                full_key = f"{prefix}.{k}" if prefix else str(k)
                keys.add(str(k))
                keys.add(full_key)
                self._collect_keys(v, keys, full_key)

    def _build_cross_file_edges(self, files: dict[str, FileNode]) -> None:
        # Cross-file Python calls
        global_defs: dict[str, str] = {}
        for path, defs in self.definitions.items():
            for d in defs:
                global_defs[d.symbol_name] = path

        for src_path, refs in self.references.items():
            for r in refs:
                target_path = global_defs.get(r.target_symbol)
                if target_path and target_path != src_path:
                    self.edges.add((src_path, target_path))

        # Config-to-code edges: when python code references a config key
        for py_path, node in files.items():
            if node.file_type == FileType.PYTHON:
                for cfg_path, keys in self.config_keys.items():
                    for k in keys:
                        if len(k) > 2 and k in node.content:
                            self.edges.add((cfg_path, py_path))
                            break

    def get_coupled_pairs(self) -> list[tuple[str, str]]:
        """Returns sorted list of dependent file pairs suitable for compound mutation."""
        return sorted(self.edges)
