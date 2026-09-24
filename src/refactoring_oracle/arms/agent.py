"""The agent arms: Claude Code run headless inside a copy of the case.

Unlike the API arm, the agent sees the file tree, can run the before tests,
edits in place with its own tools, and can touch things it was not asked to
touch. `--bare` keeps the user's global CLAUDE.md, memory, hooks, and plugins
out of the session so the agent sees only the case. The skill arm delivers the
skill through --append-system-prompt-file so its presence does not depend on
discovery.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from refactoring_oracle.arms import ArmResult
from refactoring_oracle.case import Case
from refactoring_oracle.prompts import skill_path

DEFAULT_MODEL = "claude-sonnet-4-6"
DEFAULT_TIMEOUT = 600.0
DEFAULT_BUDGET_USD = 1.00

FRAMING = (
    "You are in a small Python project. Apply exactly the refactoring described below and "
    "nothing else: keep behavior identical, do not touch files or functions the instruction "
    "does not mention, do not add imports beyond what the refactoring needs, do not reformat or "
    "reorder unrelated code, and do not add comments or docstrings that were not there. Edit "
    "the files in place. You may run the existing tests with `python -m pytest -q tests`. Do not "
    "create files the instruction does not require, and do not use git. When the refactoring is "
    "done, stop.\n\nInstruction:\n"
)


def build_command(prompt: str, model: str, budget_usd: float, skill: Path | None) -> list[str]:
    cmd = [
        "claude", "-p", prompt,
        "--bare",
        "--output-format", "json",
        "--no-session-persistence",
        "--model", model,
        "--permission-mode", "acceptEdits",
        "--setting-sources", "project",
        "--tools", "Read,Edit,Write,Glob,Grep,Bash",
        "--allowedTools", "Bash(python -m pytest*)", "Bash(pytest*)", "Bash(python3 -m pytest*)",
        "--max-budget-usd", f"{budget_usd:.2f}",
    ]
    if skill is not None:
        cmd += ["--append-system-prompt-file", str(skill)]
    return cmd


class AgentArm:
    def __init__(
        self,
        with_skill: bool,
        model: str = DEFAULT_MODEL,
        budget_usd: float = DEFAULT_BUDGET_USD,
        timeout: float = DEFAULT_TIMEOUT,
        runner: Any = subprocess.run,
    ) -> None:
        self.with_skill = with_skill
        self.name = "agent-skill" if with_skill else "agent-bare"
        self.model = model
        self.budget_usd = budget_usd
        self.timeout = timeout
        self._run = runner
        if shutil.which("claude") is None and runner is subprocess.run:
            raise RuntimeError("the claude CLI is not on PATH")

    def run(self, case: Case, workdir: Path) -> ArmResult:
        skill = skill_path(case.refactoring) if self.with_skill else None
        cmd = build_command(FRAMING + case.instruction, self.model, self.budget_usd, skill)
        env = {**os.environ, "CLAUDE_CODE_SIMPLE": "1"}
        started = time.perf_counter()
        try:
            proc = self._run(cmd, cwd=workdir, env=env, capture_output=True, text=True,
                             timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return ArmResult(False, (time.perf_counter() - started) * 1000.0,
                             error=f"timed out after {self.timeout:.0f}s")
        latency_ms = (time.perf_counter() - started) * 1000.0
        result = ArmResult(ok=False, latency_ms=latency_ms, model=self.model)
        result.extra["returncode"] = proc.returncode
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError:
            result.error = f"claude did not return JSON (rc={proc.returncode}): " \
                           f"{(proc.stderr or proc.stdout)[-400:]}"
            return result
        usage = payload.get("usage") or {}
        result.input_tokens = usage.get("input_tokens")
        result.output_tokens = usage.get("output_tokens")
        result.cache_creation_input_tokens = usage.get("cache_creation_input_tokens")
        result.cache_read_input_tokens = usage.get("cache_read_input_tokens")
        result.request_id = payload.get("session_id")
        result.stop_reason = payload.get("subtype")
        result.extra.update({
            "total_cost_usd": payload.get("total_cost_usd"),
            "num_turns": payload.get("num_turns"),
            "duration_ms": payload.get("duration_ms"),
            "duration_api_ms": payload.get("duration_api_ms"),
            "is_error": payload.get("is_error"),
            "result_text": (payload.get("result") or "")[:2000],
            "model_usage": payload.get("modelUsage"),
        })
        if payload.get("is_error") or proc.returncode != 0:
            result.error = f"claude reported an error: {(payload.get('result') or '')[:300]}"
            return result
        result.ok = True
        return result
