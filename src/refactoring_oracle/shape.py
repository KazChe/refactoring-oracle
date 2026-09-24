"""AST assertions: did the candidate actually do the refactoring that was asked?

Each assertion kind is a small function over a parsed module. They are
deliberately literal: a refactoring instruction names the target interface,
and these check that exactly that interface exists.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

from refactoring_oracle.case import ShapeAssertion


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    message: str
    assertion: str = ""


def parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _defs(tree: ast.AST) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef]:
    """Top-level defs by name, plus methods as 'Class.method'."""
    out: dict[str, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef] = {}
    for node in getattr(tree, "body", []):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            out[node.name] = node
            if isinstance(node, ast.ClassDef):
                for sub in node.body:
                    if isinstance(sub, ast.FunctionDef | ast.AsyncFunctionDef):
                        out[f"{node.name}.{sub.name}"] = sub
    return out


def find_function(tree: ast.Module, name: str) -> ast.FunctionDef | ast.AsyncFunctionDef | None:
    node = _defs(tree).get(name)
    return node if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef) else None


def find_class(tree: ast.Module, name: str) -> ast.ClassDef | None:
    node = _defs(tree).get(name)
    return node if isinstance(node, ast.ClassDef) else None


def param_names(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    a = fn.args
    names = [p.arg for p in a.posonlyargs] + [p.arg for p in a.args]
    if a.vararg:
        names.append("*" + a.vararg.arg)
    names += [p.arg for p in a.kwonlyargs]
    if a.kwarg:
        names.append("**" + a.kwarg.arg)
    return names


def _call_name(call: ast.Call) -> str | None:
    f = call.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def _same_constant(node: ast.Constant, value: object) -> bool:
    # 1 == True in Python; a magic literal check must not confuse them.
    return type(node.value) is type(value) and node.value == value


def _decorator_name(d: ast.expr) -> str | None:
    if isinstance(d, ast.Call):
        d = d.func
    if isinstance(d, ast.Name):
        return d.id
    if isinstance(d, ast.Attribute):
        return d.attr
    return None


def _identifiers(tree: ast.AST) -> set[str]:
    ids: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            ids.add(node.id)
        elif isinstance(node, ast.Attribute):
            ids.add(node.attr)
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            ids.add(node.name)
        elif isinstance(node, ast.arg):
            ids.add(node.arg)
        elif isinstance(node, ast.keyword) and node.arg:
            ids.add(node.arg)
        elif isinstance(node, ast.alias):
            ids.add(node.asname or node.name)
    return ids


def _if_depth(node: ast.AST) -> int:
    best = 0
    for child in ast.iter_child_nodes(node):
        d = _if_depth(child)
        if isinstance(child, ast.If):
            d += 1
        best = max(best, d)
    return best


def check(assertion: ShapeAssertion, candidate_dir: Path) -> CheckResult:
    label = assertion.describe()
    path = candidate_dir / assertion.in_file
    if not path.exists():
        return CheckResult(False, f"{assertion.in_file} is missing", label)
    try:
        tree = parse(path)
    except SyntaxError as exc:
        return CheckResult(False, f"{assertion.in_file} does not parse: {exc}", label)

    k = assertion.kind
    if k == "defines_function":
        fn = find_function(tree, assertion.name or "")
        if fn is None:
            return CheckResult(False, f"function {assertion.name} not defined", label)
        if assertion.params is not None and param_names(fn) != assertion.params:
            return CheckResult(
                False,
                f"{assertion.name} params are {param_names(fn)}, want {assertion.params}",
                label,
            )
        return CheckResult(True, f"{assertion.name} defined", label)

    if k == "not_defines":
        if assertion.name in _defs(tree):
            return CheckResult(False, f"{assertion.name} is still defined", label)
        return CheckResult(True, f"{assertion.name} not defined", label)

    if k == "defines_class":
        cls = find_class(tree, assertion.name or "")
        if cls is None:
            return CheckResult(False, f"class {assertion.name} not defined", label)
        if assertion.dataclass:
            if not any(_decorator_name(d) == "dataclass" for d in cls.decorator_list):
                return CheckResult(False, f"{assertion.name} is not a dataclass", label)
        if assertion.fields is not None:
            have = [
                s.target.id
                for s in cls.body
                if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)
            ]
            if have != assertion.fields:
                return CheckResult(
                    False, f"{assertion.name} fields are {have}, want {assertion.fields}", label
                )
        return CheckResult(True, f"class {assertion.name} defined", label)

    if k == "calls":
        fn = find_function(tree, assertion.inside or "")
        if fn is None:
            return CheckResult(False, f"function {assertion.inside} not defined", label)
        found = any(
            isinstance(n, ast.Call) and _call_name(n) == assertion.callee for n in ast.walk(fn)
        )
        return CheckResult(found, f"{assertion.inside} {'calls' if found else 'does not call'} "
                                  f"{assertion.callee}", label)

    if k == "no_call":
        scope: ast.AST = tree
        if assertion.inside:
            fn = find_function(tree, assertion.inside)
            if fn is None:
                return CheckResult(False, f"function {assertion.inside} not defined", label)
            scope = fn
        found = any(
            isinstance(n, ast.Call) and _call_name(n) == assertion.callee for n in ast.walk(scope)
        )
        where = assertion.inside or assertion.in_file
        return CheckResult(not found, f"{where} {'still calls' if found else 'does not call'} "
                                      f"{assertion.callee}", label)

    if k == "defines_constant":
        for node in tree.body:
            if isinstance(node, ast.Assign | ast.AnnAssign):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                names = [t.id for t in targets if isinstance(t, ast.Name)]
                if assertion.name in names:
                    value = node.value
                    if isinstance(value, ast.Constant) and _same_constant(value, assertion.value):
                        return CheckResult(True, f"{assertion.name} = {assertion.value!r}", label)
                    return CheckResult(
                        False, f"{assertion.name} is defined but not equal to {assertion.value!r}",
                        label,
                    )
        return CheckResult(False, f"module constant {assertion.name} not defined", label)

    if k == "no_literal":
        fn = find_function(tree, assertion.inside or "")
        if fn is None:
            return CheckResult(False, f"function {assertion.inside} not defined", label)
        found = any(
            isinstance(n, ast.Constant) and _same_constant(n, assertion.value) for n in ast.walk(fn)
        )
        return CheckResult(not found, f"literal {assertion.value!r} "
                                      f"{'still present' if found else 'absent'} in "
                                      f"{assertion.inside}", label)

    if k == "starts_with_guard":
        fn = find_function(tree, assertion.inside or "")
        if fn is None:
            return CheckResult(False, f"function {assertion.inside} not defined", label)
        body = [s for s in fn.body if not _is_docstring(s)]
        first = body[0] if body else None
        ok = (
            isinstance(first, ast.If)
            and not first.orelse
            and len(first.body) == 1
            and isinstance(first.body[0], ast.Return | ast.Raise)
        )
        return CheckResult(ok, f"{assertion.inside} {'starts' if ok else 'does not start'} "
                               f"with a guard clause", label)

    if k == "max_if_depth":
        fn = find_function(tree, assertion.inside or "")
        if fn is None:
            return CheckResult(False, f"function {assertion.inside} not defined", label)
        depth = _if_depth(fn)
        ok = depth <= (assertion.n or 0)
        return CheckResult(ok, f"{assertion.inside} if-nesting depth is {depth}, "
                               f"limit {assertion.n}", label)

    if k == "name_absent":
        present = assertion.name in _identifiers(tree)
        return CheckResult(not present, f"identifier {assertion.name} "
                                        f"{'still present' if present else 'absent'}", label)

    if k == "name_present":
        present = assertion.name in _identifiers(tree)
        return CheckResult(present, f"identifier {assertion.name} "
                                    f"{'present' if present else 'absent'}", label)

    raise ValueError(f"unknown assertion kind {k}")  # unreachable: the model validates kind


def _is_docstring(stmt: ast.stmt) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def check_all(assertions: list[ShapeAssertion], candidate_dir: Path) -> list[CheckResult]:
    return [check(a, candidate_dir) for a in assertions]
