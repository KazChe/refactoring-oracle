"""The deterministic arm: rope, for the refactorings it implements.

rope is driven by character offsets and refactoring classes, not by an
instruction, so each supported case has a spec here that says which class to
call and where. The specs live outside cases/ so the frozen fixture is not
touched. Cases with no rope refactoring are reported as unsupported, which is
itself a result: the deterministic tool's coverage.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from refactoring_oracle.arms import ArmResult
from refactoring_oracle.case import Case

Step = tuple[str, dict[str, Any]]


def _offset(text: str, anchor: str, name: str) -> int:
    """Offset of `name` inside the first occurrence of `anchor`."""
    i = text.index(anchor)
    return i + anchor.index(name)


# One list of steps per supported case. Each step names the rope refactoring and how
# to find its target in the *current* file text (steps run in order).
SPECS: dict[str, list[Step]] = {
    "rename/csv-cleaner": [
        ("rename", {"file": "cleaner.py", "anchor": "def clean_hdr(", "name": "clean_hdr",
                    "new": "normalize_header"}),
    ],
    "rename/meeting-slots": [
        ("rename", {"file": "slots.py", "anchor": "def find_gaps(", "name": "find_gaps",
                    "new": "free_slots"}),
        ("rename", {"file": "slots.py", "anchor": "def free_slots(busy, min_len)",
                    "name": "min_len", "new": "min_minutes"}),
        ("rename", {"file": "slots.py", "anchor": "def first_gap(busy, min_len)",
                    "name": "min_len", "new": "min_minutes"}),
    ],
    "inline-function/log-parser": [
        ("inline", {"file": "logparse.py", "anchor": "def _is_level(", "name": "_is_level"}),
    ],
    "inline-function/loyalty-ledger": [
        ("inline", {"file": "loyalty.py", "anchor": "def _points_for(", "name": "_points_for"}),
    ],
    # Extract, then reorder the parameters to the order the instruction named. rope picks
    # its own order on extraction and offers no way to set it there; ChangeSignature is the
    # second step a person driving rope would take. The first artifact (runs/rope-results.json)
    # was produced without this step and is kept.
    "extract-function/parking-fee": [
        ("extract", {"file": "parking.py",
                     "start": "    if entered_hour >= 18 or entered_hour < 6:\n",
                     "end": "        base = round(base * 0.8, 2)\n",
                     "new": "evening_discount"}),
        ("reorder", {"file": "parking.py", "anchor": "def evening_discount(",
                     "name": "evening_discount", "order": ["base", "entered_hour"]}),
    ],
    "extract-function/shipping-quote": [
        ("extract", {"file": "shipping.py",
                     "start": "    if zone not in ZONE_RATES:\n",
                     "end": '        raise ValueError("weight must be positive")\n',
                     "new": "validate"}),
        ("reorder", {"file": "shipping.py", "anchor": "def validate(",
                     "name": "validate", "order": ["weight_kg", "zone"]}),
    ],
}

SPEC_VERSION = 2  # v1 had no reorder step on the extract cases


def _current_params(text: str, name: str) -> list[str]:
    import ast

    for node in ast.parse(text).body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return [a.arg for a in node.args.args]
    raise ValueError(f"function {name} not found")


def _apply(workdir: Path, steps: list[Step]) -> list[str]:
    from rope.base.project import Project
    from rope.refactor.change_signature import ArgumentReorderer, ChangeSignature
    from rope.refactor.extract import ExtractMethod
    from rope.refactor.inline import create_inline
    from rope.refactor.rename import Rename

    project = Project(str(workdir), ropefolder=None)
    touched: set[str] = set()
    try:
        for kind, spec in steps:
            resource = project.get_resource(spec["file"])
            text = resource.read()
            if kind == "rename":
                off = _offset(text, spec["anchor"], spec["name"])
                changes = Rename(project, resource, off).get_changes(spec["new"], docs=True)
            elif kind == "inline":
                off = _offset(text, spec["anchor"], spec["name"])
                changes = create_inline(project, resource, off).get_changes(
                    remove=True, only_current=False
                )
            elif kind == "extract":
                start = text.index(spec["start"])
                end = text.index(spec["end"], start) + len(spec["end"])
                changes = ExtractMethod(project, resource, start, end).get_changes(
                    spec["new"], global_=True
                )
            elif kind == "reorder":
                current = _current_params(text, spec["name"])
                new_order = [current.index(n) for n in spec["order"]]
                off = _offset(text, spec["anchor"], spec["name"])
                changes = ChangeSignature(project, resource, off).get_changes(
                    [ArgumentReorderer(new_order)]
                )
            else:
                raise ValueError(kind)
            for change in changes.changes:
                res = getattr(change, "resource", None)
                if res is not None:
                    touched.add(res.path)
            project.do(changes)
    finally:
        project.close()
    return sorted(touched)


class RopeArm:
    name = "rope"

    def __init__(self, apply: Callable[[Path, list[Step]], list[str]] = _apply) -> None:
        self._apply = apply

    def run(self, case: Case, workdir: Path) -> ArmResult:
        steps = SPECS.get(case.id)
        started = time.perf_counter()
        if steps is None:
            return ArmResult(False, 0.0, model="rope",
                             error=f"no rope refactoring for {case.refactoring}",
                             extra={"unsupported": True})
        try:
            written = self._apply(workdir, steps)
        except Exception as exc:  # noqa: BLE001
            return ArmResult(False, (time.perf_counter() - started) * 1000.0, model="rope",
                             error=f"{type(exc).__name__}: {exc}")
        return ArmResult(True, (time.perf_counter() - started) * 1000.0, model="rope",
                         input_tokens=0, output_tokens=0, files_written=written,
                         extra={"total_cost_usd": 0.0, "steps": len(steps),
                                "spec_version": SPEC_VERSION})
