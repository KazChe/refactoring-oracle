"""grade(case, candidate) -> Verdict. Four checks, one failure class."""

from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from refactoring_oracle import behavior, collateral, shape
from refactoring_oracle.case import Case

FailureClass = Literal["none", "compiles", "behavior", "shape", "collateral"]
ORDER: tuple[FailureClass, ...] = ("compiles", "behavior", "shape", "collateral")


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    case_id: str
    candidate: str
    compiles: bool
    behavior: bool | None
    shape: bool | None
    collateral: bool | None
    overall: bool
    failure_class: FailureClass
    details: dict[str, Any]

    def summary_line(self) -> str:
        def mark(v: bool | None) -> str:
            return "-" if v is None else ("ok" if v else "FAIL")

        return (
            f"{self.case_id:40} compiles={mark(self.compiles):4} behavior={mark(self.behavior):4} "
            f"shape={mark(self.shape):4} collateral={mark(self.collateral):4} -> "
            f"{'PASS' if self.overall else 'fail: ' + self.failure_class}"
        )


def grade(case: Case, candidate_dir: Path, timeout: float = behavior.DEFAULT_TIMEOUT) -> Verdict:
    candidate_dir = candidate_dir.resolve()
    details: dict[str, Any] = {}

    comp = behavior.compile_all(candidate_dir)
    details["compiles"] = asdict(comp)
    if not comp.ok:
        return Verdict(
            case_id=case.id, candidate=str(candidate_dir), compiles=False, behavior=None,
            shape=None, collateral=None, overall=False, failure_class="compiles", details=details,
        )

    beh = behavior.run_tests(candidate_dir, case.tests_after_dir, timeout=timeout)
    details["behavior"] = asdict(beh)

    checks = shape.check_all(case.shape, candidate_dir)
    details["shape"] = [asdict(c) for c in checks]
    shape_ok = all(c.ok for c in checks)

    probs = collateral.problems(case, candidate_dir)
    details["collateral"] = probs
    coll_ok = not probs

    results: dict[FailureClass, bool] = {
        "compiles": True, "behavior": beh.ok, "shape": shape_ok, "collateral": coll_ok,
    }
    failure_class: FailureClass = next((k for k in ORDER if not results[k]), "none")
    return Verdict(
        case_id=case.id, candidate=str(candidate_dir), compiles=True, behavior=beh.ok,
        shape=shape_ok, collateral=coll_ok, overall=failure_class == "none",
        failure_class=failure_class, details=details,
    )


def expected_failure_class(mutant_name: str) -> FailureClass:
    """Mutant directories are named '<class>_<anything>'."""
    prefix = mutant_name.split("_", 1)[0]
    if prefix not in ORDER:
        raise ValueError(f"mutant {mutant_name!r} must start with one of {ORDER}")
    return prefix  # type: ignore[return-value]
