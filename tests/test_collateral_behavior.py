from pathlib import Path

from refactoring_oracle import behavior, collateral
from refactoring_oracle.case import Case
from tests.conftest import AFTER_PRICING, INIT, write_tree


def candidate(tmp_path: Path, files: dict[str, str]) -> Path:
    d = tmp_path / "cand"
    write_tree(d, files)
    return d


def test_reference_has_no_collateral_problems(pricing_case: Case) -> None:
    assert collateral.problems(pricing_case, pricing_case.after_dir) == []


def test_changed_file_outside_allowed(pricing_case: Case, tmp_path: Path) -> None:
    c = candidate(tmp_path, {"pricing.py": AFTER_PRICING, "__init__.py": INIT + "# touched\n"})
    probs = collateral.problems(pricing_case, c)
    assert any("changed file outside allowed_files: __init__.py" in p for p in probs)


def test_added_and_removed_files(pricing_case: Case, tmp_path: Path) -> None:
    c = candidate(tmp_path, {"pricing.py": AFTER_PRICING, "extra.py": "x = 1\n"})
    probs = collateral.problems(pricing_case, c)
    assert any("added file" in p for p in probs)
    assert any("removed file" in p for p in probs)


def test_protected_ast_change(pricing_case: Case, tmp_path: Path) -> None:
    edited = AFTER_PRICING.replace('f"${amount:.2f}"', 'f"{amount:.2f} USD"')
    assert edited != AFTER_PRICING
    c = candidate(tmp_path, {"pricing.py": edited, "__init__.py": INIT})
    probs = collateral.problems(pricing_case, c)
    assert probs == ["protected pricing.py::format_money: AST changed"]


def test_unlisted_import(pricing_case: Case, tmp_path: Path) -> None:
    c = candidate(tmp_path, {"pricing.py": "import os\n" + AFTER_PRICING, "__init__.py": INIT})
    probs = collateral.problems(pricing_case, c)
    assert any("new top-level import(s) ['os']" in p for p in probs)


def test_compile_all(tmp_path: Path) -> None:
    c = candidate(tmp_path, {"ok.py": "x = 1\n", "bad.py": "def (:\n"})
    res = behavior.compile_all(c)
    assert not res.ok and res.errors and res.errors[0].startswith("bad.py")
    assert behavior.compile_all(candidate(tmp_path / "b", {"ok.py": "x = 1\n"})).ok


def test_run_tests_pass_and_fail(pricing_case: Case) -> None:
    good = behavior.run_tests(pricing_case.after_dir, pricing_case.tests_after_dir)
    assert good.ok and "passed" in good.summary
    bad = behavior.run_tests(pricing_case.before_dir, pricing_case.tests_after_dir)
    assert not bad.ok
    assert bad.first_failure is not None
