import json
from pathlib import Path

import pytest

from refactoring_oracle import cli, freeze
from refactoring_oracle.case import Case, load_all
from refactoring_oracle.oracle import expected_failure_class, grade
from tests.conftest import AFTER_PRICING, BEFORE_PRICING, INIT, write_tree


def test_reference_passes_and_before_fails(pricing_case: Case) -> None:
    after = grade(pricing_case, pricing_case.after_dir)
    assert after.overall and after.failure_class == "none"
    before = grade(pricing_case, pricing_case.before_dir)
    assert not before.overall
    assert before.failure_class == "behavior"  # the interface changed, so tests fail first
    assert before.shape is False


def test_failure_class_order(pricing_case: Case, tmp_path: Path) -> None:
    # Compile error stops everything.
    c = tmp_path / "c1"
    write_tree(c, {"pricing.py": "def (:\n", "__init__.py": INIT})
    v = grade(pricing_case, c)
    assert v.failure_class == "compiles" and v.behavior is None and v.shape is None

    # Tests pass, shape ok, but a non-allowed file changed: collateral.
    c = tmp_path / "c2"
    write_tree(c, {"pricing.py": AFTER_PRICING, "__init__.py": INIT + "# touched\n"})
    v = grade(pricing_case, c)
    assert v.behavior and v.shape and not v.collateral
    assert v.failure_class == "collateral"

    # Tests pass but the dataclass was not introduced as asked: shape.
    shaped = AFTER_PRICING.replace("@dataclass\nclass Item:", "class Item:").replace(
        "    price: float\n    quantity: int\n",
        "    def __init__(self, price, quantity):\n"
        "        self.price, self.quantity = price, quantity\n",
    )
    c = tmp_path / "c3"
    write_tree(c, {"pricing.py": shaped, "__init__.py": INIT})
    v = grade(pricing_case, c)
    assert v.behavior is True and v.shape is False
    assert v.failure_class == "shape"


def test_summary_line_and_mutant_names(pricing_case: Case) -> None:
    line = grade(pricing_case, pricing_case.after_dir).summary_line()
    assert line.endswith("PASS") and "introduce-parameter-object/pricing" in line
    assert expected_failure_class("behavior_off_by_one") == "behavior"
    with pytest.raises(ValueError):
        expected_failure_class("weird_name")


def test_freeze_and_drift(tmp_path: Path) -> None:
    root = tmp_path / "cases"
    write_tree(root, {"a/b/case.json": "{}", "a/b/before/x.py": "x = 1\n"})
    h = tmp_path / "cases.sha256"
    with pytest.raises(freeze.FixtureDrift):
        freeze.check_frozen(root, h)
    digest = freeze.freeze(root, h)
    assert freeze.check_frozen(root, h) == digest
    (root / "a/b/before/x.py").write_text("x = 2\n", encoding="utf-8")
    with pytest.raises(freeze.FixtureDrift):
        freeze.check_frozen(root, h)


def test_selfcheck_cli_on_a_temp_root(pricing_case: Case, capsys, tmp_path: Path) -> None:
    root = pricing_case.case_dir.parents[1]
    # Two mutants: one that fails where its name says, one that does not.
    m = pricing_case.mutants_dir
    write_tree(m / "collateral_touch", {"pricing.py": AFTER_PRICING, "__init__.py": INIT + "#\n"})
    write_tree(m / "behavior_none", {"pricing.py": AFTER_PRICING, "__init__.py": INIT})
    rc = cli.selfcheck_main(["--root", str(root)])
    out = capsys.readouterr().out
    assert rc == 1
    assert "collateral_touch:collateral " in out or "collateral_touch:collateral\n" in out
    assert "behavior_none:none!" in out
    assert len(load_all(root)) == 1


def test_case_model_rejects_bad_ids(tmp_path: Path) -> None:
    case_dir = tmp_path / "cases" / "x" / "y"
    write_tree(case_dir / "before", {"m.py": ""})
    data = {
        "id": "x/z", "refactoring": "x", "sample": "y", "instruction": "i",
        "allowed_files": ["m.py"],
        "shape": [{"kind": "not_defines", "in_file": "m.py", "name": "f"}],
    }
    (case_dir / "case.json").write_text(json.dumps(data), encoding="utf-8")
    from refactoring_oracle.case import load_case
    with pytest.raises(ValueError):
        load_case(case_dir)
    data["id"] = "x/y"
    data["shape"] = [{"kind": "calls", "in_file": "m.py", "callee": "f"}]  # missing inside
    (case_dir / "case.json").write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_case(case_dir)


def test_before_pricing_is_valid_python() -> None:
    compile(BEFORE_PRICING, "pricing.py", "exec")
