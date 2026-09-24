"""Every case.json validates and its instruction names what the shape asserts."""

import pytest

from refactoring_oracle.case import load_all

CASES = load_all()


def test_ids_unique_and_present() -> None:
    assert len({c.id for c in CASES}) == len(CASES) >= 1


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_instruction_names_asserted_symbols(case) -> None:
    for a in case.shape:
        for symbol in (a.name, a.callee):
            if symbol and a.kind not in ("name_absent", "no_call", "not_defines"):
                bare = symbol.split(".")[-1]
                assert bare in case.instruction, f"{case.id}: instruction never names {bare}"


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_layout(case) -> None:
    assert (case.before_dir / "__init__.py").exists()
    assert (case.after_dir / "__init__.py").exists()
    assert any(case.tests_after_dir.glob("test_*.py"))
    for f in case.allowed_files:
        assert (case.before_dir / f).exists(), f
    assert "__init__.py" not in case.allowed_files
