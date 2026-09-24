"""Did the candidate touch anything it was not asked to touch?

Three rules: files outside `allowed_files` are byte-identical to before;
`protected` definitions have the same AST as before; allowed files gain no
top-level imports beyond what before had plus `allowed_imports`.
"""

from __future__ import annotations

import ast
from pathlib import Path

from refactoring_oracle.case import Case
from refactoring_oracle.shape import _defs, parse

SKIP_DIRS = {"__pycache__", ".pytest_cache", ".ruff_cache", ".git"}


def _files(root: Path) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for p in root.rglob("*"):
        if p.is_dir() or any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if p.suffix == ".pyc":
            continue
        out[p.relative_to(root).as_posix()] = p
    return out


def _import_roots(tree: ast.Module) -> set[str]:
    roots: set[str] = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative import: within the package, always fine
                continue
            roots.add((node.module or "").split(".")[0])
    return roots


def _dump(node: ast.AST) -> str:
    return ast.dump(node, include_attributes=False)


def problems(case: Case, candidate_dir: Path) -> list[str]:
    before = _files(case.before_dir)
    after = _files(candidate_dir)
    allowed = set(case.allowed_files)
    out: list[str] = []

    for rel in sorted(set(before) | set(after)):
        if rel in allowed:
            continue
        if rel not in after:
            out.append(f"removed file outside allowed_files: {rel}")
        elif rel not in before:
            out.append(f"added file outside allowed_files: {rel}")
        elif before[rel].read_bytes() != after[rel].read_bytes():
            out.append(f"changed file outside allowed_files: {rel}")

    for spec in case.protected:
        file, _, name = spec.partition("::")
        if file not in after:
            out.append(f"protected {spec}: file missing")
            continue
        try:
            b_defs = _defs(parse(before[file]))
            a_defs = _defs(parse(after[file]))
        except SyntaxError as exc:
            out.append(f"protected {spec}: {exc}")
            continue
        if name not in a_defs:
            out.append(f"protected {spec}: definition missing")
        elif name not in b_defs:
            out.append(f"protected {spec}: not present in before (fixture error)")
        elif _dump(a_defs[name]) != _dump(b_defs[name]):
            out.append(f"protected {spec}: AST changed")

    for rel in sorted(allowed):
        if rel not in after or not rel.endswith(".py"):
            continue
        try:
            new_roots = _import_roots(parse(after[rel]))
        except SyntaxError:
            continue  # the compiles check reports this
        old_roots = _import_roots(parse(before[rel])) if rel in before else set()
        extra = new_roots - old_roots - set(case.allowed_imports)
        if extra:
            out.append(f"{rel}: new top-level import(s) {sorted(extra)} not in allowed_imports")

    return out
