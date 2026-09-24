"""Run a held-out pytest suite against a candidate tree, in a subprocess."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from refactoring_oracle.collateral import _files

DEFAULT_TIMEOUT = 60.0


@dataclass(frozen=True)
class CompileResult:
    ok: bool
    errors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class BehaviorResult:
    ok: bool
    summary: str
    first_failure: str | None = None
    returncode: int | None = None
    timed_out: bool = False


def compile_all(candidate_dir: Path) -> CompileResult:
    errors: list[str] = []
    for rel, path in sorted(_files(candidate_dir).items()):
        if not rel.endswith(".py"):
            continue
        try:
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        except SyntaxError as exc:
            errors.append(f"{rel}: line {exc.lineno}: {exc.msg}")
    return CompileResult(not errors, errors)


def run_tests(
    candidate_dir: Path, tests_dir: Path, timeout: float = DEFAULT_TIMEOUT
) -> BehaviorResult:
    """Copy the candidate and the held-out tests into a temp dir and run pytest there."""
    with tempfile.TemporaryDirectory(prefix="ro-") as tmp:
        root = Path(tmp)
        shutil.copytree(candidate_dir, root / "cand", ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(tests_dir, root / "cand" / "tests_after",
                        ignore=shutil.ignore_patterns("__pycache__"))
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONPATH": str(root / "cand"),
            "PYTHONHASHSEED": "0",
        }
        cmd = [
            sys.executable, "-m", "pytest", "-x", "-q", "-p", "no:cacheprovider",
            "--rootdir", str(root / "cand"), "-o", "addopts=", "tests_after",
        ]
        try:
            proc = subprocess.run(
                cmd, cwd=root / "cand", env=env, capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return BehaviorResult(False, f"timed out after {timeout:.0f}s", timed_out=True)
    out = proc.stdout + proc.stderr
    lines = [ln for ln in out.splitlines() if ln.strip()]
    summary = lines[-1] if lines else "(no output)"
    first_failure = next((ln for ln in lines if ln.startswith(("FAILED", "ERROR"))), None)
    if proc.returncode != 0 and first_failure is None:
        first_failure = next((ln for ln in lines if "Error" in ln or "error" in ln), None)
    return BehaviorResult(proc.returncode == 0, summary, first_failure, proc.returncode)
