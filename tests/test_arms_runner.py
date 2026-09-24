"""The API arm with a fake client, the reference arm, and the runner end to end (dry run)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from refactoring_oracle import prompts, runner
from refactoring_oracle.arms.api import ApiArm, ReferenceArm, apply_files
from refactoring_oracle.case import Case, load_all


def fake_response(files: list[dict[str, str]] | None, stop_reason: str = "tool_use") -> Any:
    content = []
    if files is not None:
        content.append(
            SimpleNamespace(type="tool_use", name=prompts.TOOL_NAME, input={"files": files})
        )
    return SimpleNamespace(
        model="claude-sonnet-4-6", stop_reason=stop_reason, stop_details=None, content=content,
        usage=SimpleNamespace(input_tokens=900, output_tokens=300,
                              cache_creation_input_tokens=0, cache_read_input_tokens=0),
        _request_id="req_fake",
    )


class FakeClient:
    def __init__(self, resp: Any) -> None:
        self.resp, self.calls = resp, []

    def create_message(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return self.resp


def test_prompt_and_skills_hashes_are_stable() -> None:
    assert prompts.prompt_sha256() == prompts.prompt_sha256()
    assert prompts.skills_sha256() == prompts.skills_sha256()
    for case in load_all():
        assert prompts.load_skill(case.refactoring).startswith("---\nname: " + case.refactoring)


def test_user_message_lists_every_before_file(pricing_case: Case) -> None:
    msg = prompts.user_message(pricing_case)
    assert msg.startswith("Instruction:\n")
    assert "### path: pricing.py" in msg and "### path: __init__.py" in msg


def test_api_arm_writes_returned_files_and_reports_usage(
    pricing_case: Case, tmp_path: Path
) -> None:
    new = (pricing_case.after_dir / "pricing.py").read_text()
    client = FakeClient(fake_response([{"path": "pricing.py", "content": new}]))
    arm = ApiArm(with_skill=True, client=client)
    work = tmp_path / "w"
    import shutil
    shutil.copytree(pricing_case.before_dir, work)
    res = arm.run(pricing_case, work)
    assert res.ok and res.files_written == ["pricing.py"]
    assert res.input_tokens == 900 and res.request_id == "req_fake"
    assert (work / "pricing.py").read_text() == new
    sent = client.calls[0]
    assert sent["tool_choice"] == {"type": "tool", "name": prompts.TOOL_NAME}
    assert "Introduce Parameter Object" in sent["system"]  # the skill is in the system prompt
    assert "thinking" not in sent
    bare = ApiArm(with_skill=False, client=client)
    bare.run(pricing_case, work)
    assert "Introduce Parameter Object" not in client.calls[1]["system"]


def test_api_arm_error_paths(pricing_case: Case, tmp_path: Path) -> None:
    work = tmp_path / "w"
    work.mkdir()
    assert ApiArm(False, client=FakeClient(fake_response(None))).run(pricing_case, work).error
    assert ApiArm(False, client=FakeClient(fake_response([]))).run(pricing_case, work).error
    r = ApiArm(False, client=FakeClient(fake_response(None, "max_tokens"))).run(pricing_case, work)
    assert "max_tokens" in (r.error or "")
    r = ApiArm(False, client=FakeClient(fake_response([{"path": "../x.py", "content": ""}]))).run(
        pricing_case, work)
    assert r.error and "escapes" in r.error


def test_apply_files_rejects_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        apply_files(tmp_path, [{"path": "../../etc/passwd", "content": "x"}])


def test_reference_arm_passes_every_case() -> None:
    import shutil

    from refactoring_oracle.oracle import grade

    for case in load_all():
        work = runner.WORK_ROOT / "test-reference" / case.id
        if work.exists():
            shutil.rmtree(work)
        shutil.copytree(case.before_dir, work)
        assert ReferenceArm().run(case, work).ok
        assert grade(case, work).overall, case.id
        shutil.rmtree(work)


def test_dry_run_artifact_summary_and_resume(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "WORK_ROOT", tmp_path / "work")
    out = tmp_path / "r.json"
    cfg = runner.RunConfig(arms=["api-bare"], runs=2, out=out, dry_run=True,
                           case_ids=["rename/csv-cleaner", "guard-clauses/ticket-refund"])
    art = runner.run(cfg)
    assert art["meta"]["status"] == "complete"
    assert len(art["trials"]) == 4
    s = art["summary"]
    assert s["per_arm"]["api-bare"]["none"] == 4
    assert s["repeatability"]["api-bare"]["passed_every_run"] == 2
    assert s["per_arm_refactoring"]["api-bare"]["rename"]["none"] == 2
    assert all(t["diff"] for t in art["trials"].values())
    # Resume: drop one trial, rerun, only it is recomputed.
    del art["trials"]["api-bare/rename/csv-cleaner/1"]
    out.write_text(json.dumps(art))
    art2 = runner.run(runner.RunConfig(arms=["api-bare"], runs=2, out=out, dry_run=True,
                                       case_ids=cfg.case_ids, resume=True))
    assert len(art2["trials"]) == 4
    from refactoring_oracle import report
    text = report.render(art2)
    assert "pass/pass" in text and "api-bare" in text
