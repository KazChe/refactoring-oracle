"""The rope arm: specs address real anchors, unsupported cases say so, and the real
rope run on the two rename cases passes the oracle (rope is local, so this is offline)."""

from __future__ import annotations

import shutil
from pathlib import Path

from refactoring_oracle.arms.rope_arm import SPECS, RopeArm, _offset
from refactoring_oracle.case import load_all
from refactoring_oracle.oracle import grade


def test_every_spec_anchor_exists_in_before() -> None:
    by_id = {c.id: c for c in load_all()}
    for case_id, steps in SPECS.items():
        case = by_id[case_id]
        text = (case.before_dir / steps[0][1]["file"]).read_text(encoding="utf-8")
        first = steps[0][1]
        if "anchor" in first:
            assert _offset(text, first["anchor"], first["name"]) >= 0
        else:
            assert first["start"] in text and first["end"] in text


def test_unsupported_case_is_reported_not_raised(tmp_path: Path) -> None:
    case = next(c for c in load_all() if c.refactoring == "guard-clauses")
    res = RopeArm().run(case, tmp_path)
    assert not res.ok and res.extra.get("unsupported") is True


def test_rope_rename_passes_the_oracle(tmp_path: Path) -> None:
    case = next(c for c in load_all() if c.id == "rename/csv-cleaner")
    work = tmp_path / "w"
    shutil.copytree(case.before_dir, work)
    res = RopeArm().run(case, work)
    assert res.ok, res.error
    assert grade(case, work).overall
    assert not (work / ".ropeproject").exists()


def test_rope_extract_chooses_its_own_parameter_order(tmp_path: Path) -> None:
    case = next(c for c in load_all() if c.id == "extract-function/parking-fee")
    work = tmp_path / "w"
    shutil.copytree(case.before_dir, work)
    assert RopeArm().run(case, work).ok
    v = grade(case, work)
    assert v.shape is False
    assert any("params are" in c["message"] for c in v.details["shape"] if not c["ok"])
