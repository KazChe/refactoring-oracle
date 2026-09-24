"""Case model and loading.

A case lives in `cases/<refactoring>/<sample>/` and holds `case.json`, the
`before/` tree an arm edits, the reference `after/` tree, the held-out
`tests_after/` suite, and optional `mutants/<name>/` candidate trees.
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

REPO_ROOT = Path(__file__).resolve().parents[2]
CASES_ROOT = REPO_ROOT / "cases"

ShapeKind = Literal[
    "defines_function",
    "not_defines",
    "defines_class",
    "calls",
    "no_call",
    "defines_constant",
    "no_literal",
    "starts_with_guard",
    "max_if_depth",
    "name_absent",
    "name_present",
]


class ShapeAssertion(BaseModel):
    """One AST assertion. Which fields apply depends on `kind`; see shape.py."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: ShapeKind
    in_file: str
    name: str | None = None
    params: list[str] | None = None
    dataclass: bool | None = None
    fields: list[str] | None = None
    callee: str | None = None
    inside: str | None = None
    value: Any = None
    n: int | None = None

    @model_validator(mode="after")
    def _required_fields(self) -> ShapeAssertion:
        need: dict[str, tuple[str, ...]] = {
            "defines_function": ("name",),
            "not_defines": ("name",),
            "defines_class": ("name",),
            "calls": ("callee", "inside"),
            "no_call": ("callee",),
            "defines_constant": ("name", "value"),
            "no_literal": ("value", "inside"),
            "starts_with_guard": ("inside",),
            "max_if_depth": ("inside", "n"),
            "name_absent": ("name",),
            "name_present": ("name",),
        }
        for field in need[self.kind]:
            if getattr(self, field) is None:
                raise ValueError(f"{self.kind} needs {field}")
        return self

    def describe(self) -> str:
        parts = [self.kind, self.in_file]
        for field in ("name", "params", "dataclass", "fields", "callee", "inside", "value", "n"):
            v = getattr(self, field)
            if v is not None:
                parts.append(f"{field}={v!r}")
        return " ".join(parts)


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(description="<refactoring>/<sample>, equal to the directory path")
    refactoring: str
    sample: str
    instruction: str = Field(description="The exact text every arm receives")
    allowed_files: list[str] = Field(description="Paths under before/ the arm may change")
    protected: list[str] = Field(
        default_factory=list,
        description="'file.py::name' or 'file.py::Class.method' whose AST must not change",
    )
    allowed_imports: list[str] = Field(
        default_factory=list, description="Module roots the arm may newly import"
    )
    deterministic_tool: str | None = Field(
        None, description="rope class that performs this refactoring, or null"
    )
    shape: list[ShapeAssertion] = Field(min_length=1)
    notes: str = ""

    case_dir: Path = Field(exclude=True)

    @model_validator(mode="after")
    def _id_matches_dir(self) -> Case:
        expected = f"{self.refactoring}/{self.sample}"
        if self.id != expected:
            raise ValueError(f"id {self.id!r} must equal {expected!r}")
        if self.case_dir.name != self.sample or self.case_dir.parent.name != self.refactoring:
            raise ValueError(f"{self.id}: directory {self.case_dir} does not match id")
        return self

    @property
    def before_dir(self) -> Path:
        return self.case_dir / "before"

    @property
    def after_dir(self) -> Path:
        return self.case_dir / "after"

    @property
    def tests_after_dir(self) -> Path:
        return self.case_dir / "tests_after"

    @property
    def mutants_dir(self) -> Path:
        return self.case_dir / "mutants"

    def mutants(self) -> list[tuple[str, Path]]:
        """(name, candidate_dir) for each mutant; the name prefix is the expected failure class."""
        if not self.mutants_dir.exists():
            return []
        return sorted((p.name, p) for p in self.mutants_dir.iterdir() if p.is_dir())


def load_case(case_dir: Path) -> Case:
    data = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
    return Case.model_validate({**data, "case_dir": case_dir.resolve()})


def iter_case_dirs(root: Path = CASES_ROOT) -> Iterator[Path]:
    if not root.exists():
        return
    for refactoring in sorted(p for p in root.iterdir() if p.is_dir()):
        for sample in sorted(p for p in refactoring.iterdir() if p.is_dir()):
            if (sample / "case.json").exists():
                yield sample


def load_all(root: Path = CASES_ROOT) -> list[Case]:
    cases = [load_case(d) for d in iter_case_dirs(root)]
    ids = [c.id for c in cases]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate case ids")
    return cases


def find_case(case_id: str, root: Path = CASES_ROOT) -> Case:
    return load_case(root / case_id)
