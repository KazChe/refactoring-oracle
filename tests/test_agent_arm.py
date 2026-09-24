"""The agent arm with a fake claude subprocess."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from types import SimpleNamespace

from refactoring_oracle.arms.agent import AgentArm, build_command
from refactoring_oracle.case import Case


def fake_runner(payload: dict, rc: int = 0, edit: Path | None = None, new: str = ""):
    def run(cmd, cwd, env, capture_output, text, timeout):
        if edit is not None:
            (cwd / edit).write_text(new, encoding="utf-8")
        return SimpleNamespace(returncode=rc, stdout=json.dumps(payload), stderr="")
    return run


def test_build_command_flags() -> None:
    cmd = build_command("do it", "claude-sonnet-4-6", 1.0, None)
    assert cmd[:3] == ["claude", "-p", "do it"]
    assert "--bare" in cmd and "--output-format" in cmd and "json" in cmd
    assert "--no-session-persistence" in cmd
    assert cmd[cmd.index("--permission-mode") + 1] == "acceptEdits"
    assert "--append-system-prompt-file" not in cmd
    cmd = build_command("do it", "m", 0.5, Path("skills/rename.md"))
    assert cmd[cmd.index("--append-system-prompt-file") + 1] == "skills/rename.md"


def test_agent_arm_parses_json_and_edits_land(pricing_case: Case, tmp_path: Path) -> None:
    work = tmp_path / "w"
    shutil.copytree(pricing_case.before_dir, work)
    new = (pricing_case.after_dir / "pricing.py").read_text()
    payload = {
        "type": "result", "subtype": "success", "is_error": False, "num_turns": 6,
        "duration_ms": 41000, "duration_api_ms": 30000, "total_cost_usd": 0.042,
        "session_id": "sess_1", "result": "Done.",
        "usage": {"input_tokens": 12000, "output_tokens": 900,
                  "cache_creation_input_tokens": 3000, "cache_read_input_tokens": 20000},
    }
    arm = AgentArm(with_skill=False, runner=fake_runner(payload, edit=Path("pricing.py"), new=new))
    res = arm.run(pricing_case, work)
    assert res.ok and res.error is None
    assert res.input_tokens == 12000 and res.cache_read_input_tokens == 20000
    assert res.extra["total_cost_usd"] == 0.042 and res.extra["num_turns"] == 6
    assert (work / "pricing.py").read_text() == new


def test_agent_arm_error_paths(pricing_case: Case, tmp_path: Path) -> None:
    work = tmp_path / "w"
    work.mkdir()
    bad = AgentArm(
        False, runner=lambda *a, **k: SimpleNamespace(returncode=1, stdout="nope", stderr="boom")
    )
    assert "did not return JSON" in (bad.run(pricing_case, work).error or "")
    err = AgentArm(False, runner=fake_runner({"is_error": True, "result": "budget exceeded",
                                              "usage": {}}, rc=1))
    assert "error" in (err.run(pricing_case, work).error or "")
