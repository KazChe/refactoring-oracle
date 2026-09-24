"""The two API arms: Claude through the Messages API, bare or with a skill."""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Protocol

from refactoring_oracle.arms import ArmResult
from refactoring_oracle.case import Case
from refactoring_oracle.prompts import TOOL, TOOL_NAME, load_skill, system_prompt, user_message

DEFAULT_MODEL = "claude-sonnet-4-6"
API_KEY_ENV = "ANTHROPIC_API_KEY"


class MessagesClient(Protocol):
    def create_message(self, **kwargs: Any) -> Any: ...


class _AnthropicMessages:
    def __init__(self, timeout: float) -> None:
        import anthropic

        self._client = anthropic.Anthropic(timeout=timeout, max_retries=2)

    def create_message(self, **kwargs: Any) -> Any:
        return self._client.messages.create(**kwargs)


def apply_files(workdir: Path, files: list[dict[str, Any]]) -> list[str]:
    """Write the returned files into the candidate tree. Paths must stay inside it."""
    written: list[str] = []
    root = workdir.resolve()
    for entry in files:
        rel = str(entry["path"]).lstrip("/")
        target = (root / rel).resolve()
        if root not in target.parents and target != root:
            raise ValueError(f"path escapes the project: {rel}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(entry["content"]), encoding="utf-8")
        written.append(rel)
    return written


class ApiArm:
    def __init__(
        self,
        with_skill: bool,
        model: str = DEFAULT_MODEL,
        client: MessagesClient | None = None,
        max_tokens: int = 4096,
        timeout: float = 120.0,
    ) -> None:
        self.with_skill = with_skill
        self.name = "api-skill" if with_skill else "api-bare"
        self.model = model
        self.max_tokens = max_tokens
        if client is None and not os.environ.get(API_KEY_ENV):
            raise RuntimeError(f"{API_KEY_ENV} is not set")
        self._client = client or _AnthropicMessages(timeout)

    def run(self, case: Case, workdir: Path) -> ArmResult:
        import anthropic

        skill = load_skill(case.refactoring) if self.with_skill else None
        started = time.perf_counter()
        try:
            resp = self._client.create_message(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt(skill),
                tools=[TOOL],
                tool_choice={"type": "tool", "name": TOOL_NAME},
                messages=[{"role": "user", "content": user_message(case)}],
            )
        except (anthropic.APIError, anthropic.APIConnectionError) as exc:
            return ArmResult(False, (time.perf_counter() - started) * 1000.0,
                             error=f"{type(exc).__name__}: {exc}")
        latency_ms = (time.perf_counter() - started) * 1000.0
        usage = getattr(resp, "usage", None)
        result = ArmResult(
            ok=False, latency_ms=latency_ms, model=getattr(resp, "model", None),
            request_id=getattr(resp, "_request_id", None),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            cache_creation_input_tokens=getattr(usage, "cache_creation_input_tokens", None),
            cache_read_input_tokens=getattr(usage, "cache_read_input_tokens", None),
            stop_reason=getattr(resp, "stop_reason", None),
        )
        if result.stop_reason == "refusal":
            details = getattr(resp, "stop_details", None)
            result.error = "model refused"
            result.extra["refusal"] = {"category": getattr(details, "category", None),
                                       "explanation": getattr(details, "explanation", None)}
            return result
        if result.stop_reason == "max_tokens":
            result.error = "hit max_tokens before the tool call completed"
            return result
        block = next(
            (b for b in resp.content if getattr(b, "type", None) == "tool_use"
             and getattr(b, "name", None) == TOOL_NAME),
            None,
        )
        if block is None:
            result.error = f"no {TOOL_NAME} tool call"
            return result
        files = block.input.get("files") if isinstance(block.input, dict) else None
        if not isinstance(files, list) or not files:
            result.error = "tool input had no files"
            return result
        try:
            result.files_written = apply_files(workdir, files)
        except (ValueError, KeyError, TypeError) as exc:
            result.error = f"bad tool input: {exc}"
            return result
        result.ok = True
        return result


class ReferenceArm:
    """Dry-run stand-in: copies the reference solution. Always passes the oracle."""

    name = "reference"

    def run(self, case: Case, workdir: Path) -> ArmResult:
        import shutil

        written = []
        for rel in case.allowed_files:
            src = case.after_dir / rel
            if src.exists():
                (workdir / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, workdir / rel)
                written.append(rel)
        return ArmResult(True, 1.0, model="reference", input_tokens=0, output_tokens=0,
                         files_written=written)
