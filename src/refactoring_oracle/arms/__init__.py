"""An arm takes a case and a fresh copy of before/, edits it, and reports what it spent."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from refactoring_oracle.case import Case


@dataclass
class ArmResult:
    ok: bool
    latency_ms: float
    model: str | None = None
    request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None
    stop_reason: str | None = None
    files_written: list[str] = field(default_factory=list)
    error: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)


class Arm(Protocol):
    name: str

    def run(self, case: Case, workdir: Path) -> ArmResult: ...
