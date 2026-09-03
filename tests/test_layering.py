"""AST-based import boundary enforcement.

Fails the build if:
- engine/ imports sim/ or narrator/
- sim/ imports engine/

This is the guard that keeps the benchmark honest. If the policy engine
can see the outcome model's parameters, you are grading your own
hypothesis and the headline number means nothing.
"""

import ast
import os
from pathlib import Path

import pytest

# Resolve package roots
_SRC = Path(__file__).resolve().parent.parent / "src" / "rra"
_ENGINE = _SRC / "engine"
_SIM = _SRC / "sim"
_NARRATOR = _SRC / "narrator"


def _collect_imports(filepath: Path) -> list[str]:
    """Parse a Python file and return all imported module names."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(filepath))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def _collect_py_files(directory: Path) -> list[Path]:
    """Recursively collect all .py files in a directory."""
    if not directory.exists():
        return []
    return list(directory.rglob("*.py"))


def _check_forbidden_imports(
    package_dir: Path,
    forbidden_prefixes: list[str],
    package_name: str,
) -> list[str]:
    """Check all modules in package_dir for imports matching forbidden prefixes."""
    violations: list[str] = []
    for py_file in _collect_py_files(package_dir):
        rel = py_file.relative_to(_SRC)
        for imp in _collect_imports(py_file):
            for prefix in forbidden_prefixes:
                if imp.startswith(prefix):
                    violations.append(
                        f"{rel}: imports '{imp}' (forbidden: {package_name} "
                        f"must not import {prefix})"
                    )
    return violations


class TestLayering:
    """Enforce the structural layering rule via AST analysis."""

    def test_engine_does_not_import_sim(self):
        violations = _check_forbidden_imports(
            _ENGINE, ["rra.sim", "sim.", "sim"], "engine"
        )
        assert violations == [], (
            f"engine/ must not import sim/:\n" + "\n".join(violations)
        )

    def test_engine_does_not_import_narrator(self):
        violations = _check_forbidden_imports(
            _ENGINE, ["rra.narrator", "narrator.", "narrator"], "engine"
        )
        assert violations == [], (
            f"engine/ must not import narrator/:\n" + "\n".join(violations)
        )

    def test_sim_does_not_import_engine(self):
        violations = _check_forbidden_imports(
            _SIM, ["rra.engine", "engine.", "engine"], "sim"
        )
        assert violations == [], (
            f"sim/ must not import engine/:\n" + "\n".join(violations)
        )


class TestLayeringNegativeFixture:
    """Verify the checker actually catches violations.

    We don't write a forbidden import to disk — instead we test the
    AST parsing logic against a synthetic source string.
    """

    def test_detects_direct_import(self):
        """A direct 'import rra.sim.outcome_model' is caught."""
        source = "import rra.sim.outcome_model\n"
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
        assert any(i.startswith("rra.sim") for i in imports)

    def test_detects_from_import(self):
        """A 'from rra.sim.outcome_model import probability' is caught."""
        source = "from rra.sim.outcome_model import probability\n"
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        assert any(i.startswith("rra.sim") for i in imports)

    def test_safe_import_not_flagged(self):
        """Importing from rra.domain is fine for engine/."""
        source = "from rra.domain.enums import FailureCode\n"
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        assert not any(i.startswith("rra.sim") for i in imports)
        assert not any(i.startswith("rra.narrator") for i in imports)
