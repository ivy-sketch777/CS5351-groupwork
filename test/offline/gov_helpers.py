"""Read-only AST/source helpers used by the offline governance gate.

These helpers intentionally inspect source text instead of importing modules:
a broken module must produce a clear gate failure, not a collection error.
"""

import ast
import re
from pathlib import Path

_SQL_PREFIX = re.compile(
    r"^\s*(SELECT|INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|WITH|REPLACE)\b",
    re.IGNORECASE,
)
_EXECUTE_ATTRS = {"execute", "executemany", "executescript"}
_DB_CALLS = {
    "create_engine",
    "sessionmaker",
    "declarative_base",
    "Column",
    "relationship",
    "mapped_column",
    "query",
}


def python_files(root: Path, subdir: str = "src") -> list[Path]:
    base = root / subdir
    if not base.exists():
        return []
    return sorted(p for p in base.rglob("*.py") if ".git" not in p.parts)


def parse_module(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_roots(tree: ast.Module) -> set[str]:
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            roots.add(node.module.split(".")[0])
    return roots


def _is_sql_literal(value: object) -> bool:
    return isinstance(value, str) and bool(_SQL_PREFIX.match(value.strip()))


def raw_sql_violations(path: Path) -> list[str]:
    """Return human-readable violations of the 'no raw SQL / ORM only' rule."""
    tree = parse_module(path)
    violations: list[str] = []

    if "sqlite3" in imported_roots(tree):
        violations.append("imports sqlite3 directly")

    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and _is_sql_literal(node.value):
            violations.append(f"raw SQL string at line {node.lineno}")

        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr in _EXECUTE_ATTRS:
                sql_args = [
                    arg.value
                    for arg in node.args
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str)
                ]
                if any(_is_sql_literal(sql) for sql in sql_args):
                    violations.append(f"execute() with raw SQL at line {node.lineno}")
            if isinstance(func, ast.Name) and func.id == "text":
                violations.append(f"sqlalchemy.text() at line {node.lineno}")
            if isinstance(func, ast.Attribute) and func.attr == "cursor":
                violations.append(f"raw cursor() at line {node.lineno}")

    return violations


def uses_database(tree: ast.Module) -> bool:
    """True when the module performs database access that must go through ORM."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = ""
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name in _DB_CALLS:
                return True
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id in {"Base", "DeclarativeBase"}:
                    return True
    return False


def cross_module_imports(path: Path, forbidden_package: str) -> list[str]:
    """Find imports of src.<forbidden_package> or sibling relative imports."""
    tree = parse_module(path)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith(f"src.{forbidden_package}"):
                    found.append(f"line {node.lineno}: import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            absolute = module.startswith(f"src.{forbidden_package}")
            sibling = bool(node.level) and module.split(".")[0] == forbidden_package
            if absolute or sibling:
                found.append(f"line {node.lineno}: from {'.' * node.level}{module}")
    return found


def writes_approved(path: Path) -> list[str]:
    """Detect AI modules that attempt to emit the authoritative approved state."""
    tree = parse_module(path)
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "APPROVED":
            found.append(f"line {node.lineno}: CaseStatus.APPROVED")
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value.strip().lower() in {"approved", "approve"}:
                found.append(f"line {node.lineno}: literal {node.value!r}")
    return found
