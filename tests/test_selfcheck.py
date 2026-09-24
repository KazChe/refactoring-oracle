"""The fixture keeps itself honest: after passes, before fails, mutants fail where named."""

import subprocess
import sys

import pytest

from refactoring_oracle.case import load_all
from refactoring_oracle.oracle import expected_failure_class, grade

CASES = load_all()


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_reference_passes(case) -> None:
    v = grade(case, case.after_dir)
    assert v.overall, v.details


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_before_fails_the_shape_check(case) -> None:
    v = grade(case, case.before_dir)
    assert not v.overall
    assert v.shape is False, "before/ satisfies the shape assertions; the case cannot discriminate"


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_before_tests_pass_on_before(case) -> None:
    """The arm starts from a green suite."""
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=", "tests"],
        cwd=case.before_dir, capture_output=True, text=True,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PATH": "", "PYTHONPATH": str(case.before_dir)},
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_mutants_fail_where_named(case) -> None:
    for name, path in case.mutants():
        v = grade(case, path)
        assert v.failure_class == expected_failure_class(name), (name, v.details)


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_synthetic_mutants(case, tmp_path) -> None:
    import shutil

    # Collateral: touch the never-allowed __init__.py.
    m = tmp_path / "collateral"
    shutil.copytree(case.after_dir, m)
    (m / "__init__.py").write_text((m / "__init__.py").read_text() + "# touched\n")
    assert grade(case, m).failure_class == "collateral"
    # Compile: break the first allowed .py file.
    m = tmp_path / "compiles"
    shutil.copytree(case.after_dir, m)
    target = next(f for f in case.allowed_files if f.endswith(".py"))
    (m / target).write_text((m / target).read_text() + "\ndef (:\n")
    assert grade(case, m).failure_class == "compiles"
