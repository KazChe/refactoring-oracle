"""Run arms over cases, N times each, sequentially, into one checkpointed artifact."""

from __future__ import annotations

import difflib
import json
import os
import shutil
import subprocess
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from refactoring_oracle import freeze, oracle, prompts
from refactoring_oracle.arms import Arm
from refactoring_oracle.case import CASES_ROOT, REPO_ROOT, Case, load_all
from refactoring_oracle.collateral import _files

WORK_ROOT = REPO_ROOT / "runs" / "work"

# USD per token, cited so the artifact and the post can be.
PRICING: dict[str, dict[str, Any]] = {
    "claude-sonnet-4-6": {
        "usd_per_input_token": 3 / 1e6,
        "usd_per_output_token": 15 / 1e6,
        "usd_per_cache_write_token": 3.75 / 1e6,
        "usd_per_cache_read_token": 0.30 / 1e6,
        "source": "https://platform.claude.com/docs/en/about-claude/pricing",
        "note": "$3 in, $15 out, $3.75 5m cache write, $0.30 cache read per MTok; read 2026-09-23",
    },
}


@dataclass
class RunConfig:
    arms: list[str] = field(default_factory=lambda: ["api-bare", "api-skill"])
    runs: int = 3
    out: Path = REPO_ROOT / "runs" / "api-results.json"
    resume: bool = False
    case_ids: list[str] | None = None
    dry_run: bool = False
    model: str = "claude-sonnet-4-6"
    allow_drift: bool = False
    keep_work: bool = True
    progress: Callable[[str], None] = lambda _s: None


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _git_commit() -> str | None:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except Exception:  # noqa: BLE001
        return None


def _versions() -> dict[str, str]:
    out = {"python": sys.version.split()[0]}
    for pkg in ("anthropic", "pydantic", "pytest"):
        try:
            out[pkg] = version(pkg)
        except PackageNotFoundError:
            out[pkg] = "not installed"
    return out


def write_artifact(path: Path, artifact: dict[str, Any]) -> None:
    artifact["meta"]["updated_at"] = _now()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(artifact, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def new_artifact(
    cfg: RunConfig, cases: list[Case], fixture_sha: str, frozen: bool
) -> dict[str, Any]:
    return {
        "meta": {
            "generated_at": _now(), "updated_at": None, "status": "running",
            "dry_run": cfg.dry_run, "git_commit": _git_commit(),
            "cases_sha256": fixture_sha, "cases_frozen": frozen,
            "prompt_sha256": prompts.prompt_sha256(), "skills_sha256": prompts.skills_sha256(),
            "arms": list(cfg.arms), "runs_requested": cfg.runs, "model": cfg.model,
            "temperature": "API default", "concurrency": 1,
            "case_ids": [c.id for c in cases], "versions": _versions(), "pricing": PRICING,
        },
        "cases": {c.id: {"refactoring": c.refactoring, "deterministic_tool": c.deterministic_tool,
                         "instruction": c.instruction} for c in cases},
        "trials": {},  # "<arm>/<case_id>/<run>" -> trial
        "summary": None,
    }


def make_arms(cfg: RunConfig) -> dict[str, Arm]:
    from refactoring_oracle.arms.api import ApiArm, ReferenceArm

    out: dict[str, Arm] = {}
    for name in cfg.arms:
        if cfg.dry_run:
            arm: Arm = ReferenceArm()
            arm.name = name  # type: ignore[misc]
            out[name] = arm
        elif name == "api-bare":
            out[name] = ApiArm(with_skill=False, model=cfg.model)
        elif name == "api-skill":
            out[name] = ApiArm(with_skill=True, model=cfg.model)
        elif name in ("agent-bare", "agent-skill"):
            from refactoring_oracle.arms.agent import AgentArm

            out[name] = AgentArm(with_skill=name == "agent-skill", model=cfg.model)
        else:
            raise ValueError(f"unknown arm {name!r}")
    return out


def _diff(case: Case, candidate: Path) -> str:
    before, after = _files(case.before_dir), _files(candidate)
    chunks = []
    for rel in sorted(set(before) | set(after)):
        b = before[rel].read_text(encoding="utf-8").splitlines(True) if rel in before else []
        a = after[rel].read_text(encoding="utf-8").splitlines(True) if rel in after else []
        if b != a:
            chunks.append("".join(difflib.unified_diff(b, a, f"before/{rel}", f"candidate/{rel}")))
    return "".join(chunks)


def run(cfg: RunConfig) -> dict[str, Any]:
    if cfg.allow_drift:
        fixture_sha, frozen = freeze.tree_sha256(), False
    else:
        fixture_sha, frozen = freeze.check_frozen(), True
    cases = load_all(CASES_ROOT)
    if cfg.case_ids:
        wanted = set(cfg.case_ids)
        cases = [c for c in cases if c.id in wanted]
        missing = wanted - {c.id for c in cases}
        if missing:
            raise ValueError(f"unknown case id(s): {sorted(missing)}")

    artifact: dict[str, Any] | None = None
    if cfg.resume and cfg.out.exists():
        artifact = json.loads(cfg.out.read_text(encoding="utf-8"))
        if artifact["meta"]["cases_sha256"] != fixture_sha:
            raise freeze.FixtureDrift("cannot resume: cases/ changed since the artifact started")
        artifact["meta"]["status"] = "running"
    if artifact is None:
        artifact = new_artifact(cfg, cases, fixture_sha, frozen)

    arms = make_arms(cfg)
    for arm_name in cfg.arms:
        arm = arms[arm_name]
        for case in cases:
            for run_idx in range(cfg.runs):
                key = f"{arm_name}/{case.id}/{run_idx}"
                existing = artifact["trials"].get(key)
                if existing and existing["arm"].get("error") is None:
                    continue
                workdir = WORK_ROOT / arm_name / case.id / str(run_idx)
                if workdir.exists():
                    shutil.rmtree(workdir)
                shutil.copytree(case.before_dir, workdir,
                                ignore=shutil.ignore_patterns("__pycache__"))
                arm_result = arm.run(case, workdir)
                trial: dict[str, Any] = {
                    "arm_name": arm_name, "case_id": case.id, "run": run_idx,
                    "arm": asdict(arm_result), "verdict": None, "diff": None,
                }
                if arm_result.ok:
                    verdict = oracle.grade(case, workdir)
                    trial["verdict"] = verdict.model_dump()
                    trial["diff"] = _diff(case, workdir)
                    mark = "." if verdict.overall else verdict.failure_class[0]
                else:
                    trial["verdict"] = {"overall": False, "failure_class": "arm_error"}
                    mark = "x"
                if not cfg.keep_work:
                    shutil.rmtree(workdir, ignore_errors=True)
                artifact["trials"][key] = trial
                cfg.progress(mark)
                write_artifact(cfg.out, artifact)
            cfg.progress(" ")
        cfg.progress("\n")

    artifact["meta"]["status"] = "complete"
    artifact["summary"] = summarize(artifact)
    write_artifact(cfg.out, artifact)
    return artifact


CLASSES = ("none", "compiles", "behavior", "shape", "collateral", "arm_error")


def summarize(artifact: dict[str, Any]) -> dict[str, Any]:
    trials = list(artifact["trials"].values())
    cases = artifact["cases"]
    arms = artifact["meta"]["arms"]
    pricing = PRICING.get(artifact["meta"]["model"])

    def counts(subset: list[dict[str, Any]]) -> dict[str, int]:
        out = dict.fromkeys(CLASSES, 0)
        for t in subset:
            out[t["verdict"]["failure_class"]] += 1
        return out

    summary: dict[str, Any] = {
        "per_arm": {}, "per_arm_refactoring": {}, "per_arm_case": {},
        "repeatability": {}, "usage": {}, "cost_per_trial": {}, "latency": {},
    }
    for arm in arms:
        mine = [t for t in trials if t["arm_name"] == arm]
        c = counts(mine)
        summary["per_arm"][arm] = {"trials": len(mine), **c,
                                   "pass_rate": (c["none"] / len(mine)) if mine else None}
        by_ref: dict[str, list[dict[str, Any]]] = {}
        for t in mine:
            by_ref.setdefault(cases[t["case_id"]]["refactoring"], []).append(t)
        summary["per_arm_refactoring"][arm] = {
            r: {"trials": len(ts), **counts(ts)} for r, ts in sorted(by_ref.items())
        }
        per_case: dict[str, list[str]] = {}
        for t in sorted(mine, key=lambda t: (t["case_id"], t["run"])):
            per_case.setdefault(t["case_id"], []).append(t["verdict"]["failure_class"])
        summary["per_arm_case"][arm] = per_case
        consistent = sum(1 for v in per_case.values() if len(set(v)) == 1)
        all_pass = sum(1 for v in per_case.values() if set(v) == {"none"})
        summary["repeatability"][arm] = {
            "cases": len(per_case), "same_outcome_every_run": consistent,
            "passed_every_run": all_pass,
            "passed_at_least_once": sum(1 for v in per_case.values() if "none" in v),
        }
        usage: dict[str, int] = {}
        n_calls = 0
        latencies = []
        for t in mine:
            a = t["arm"]
            if a.get("input_tokens") is None:
                continue
            n_calls += 1
            latencies.append(a["latency_ms"])
            for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens",
                      "cache_read_input_tokens"):
                usage[k] = usage.get(k, 0) + (a.get(k) or 0)
        summary["usage"][arm] = {**usage, "calls": n_calls}
        reported = [t["arm"].get("extra", {}).get("total_cost_usd") for t in mine
                    if t["arm"].get("input_tokens") is not None]
        turns = [t["arm"].get("extra", {}).get("num_turns") for t in mine
                 if t["arm"].get("extra", {}).get("num_turns") is not None]
        if turns:
            summary["usage"][arm]["mean_turns"] = sum(turns) / len(turns)
        if reported and all(r is not None for r in reported):
            total = float(sum(reported))
            summary["cost_per_trial"][arm] = total / len(reported)
            summary["usage"][arm]["total_usd"] = total
            summary["usage"][arm]["cost_source"] = "claude --output-format json total_cost_usd"
        elif pricing and n_calls:
            total = (
                usage.get("input_tokens", 0) * pricing["usd_per_input_token"]
                + usage.get("output_tokens", 0) * pricing["usd_per_output_token"]
                + usage.get("cache_creation_input_tokens", 0)
                * pricing["usd_per_cache_write_token"]
                + usage.get("cache_read_input_tokens", 0) * pricing["usd_per_cache_read_token"]
            )
            summary["cost_per_trial"][arm] = total / n_calls
            summary["usage"][arm]["total_usd"] = total
        else:
            summary["cost_per_trial"][arm] = None
        if latencies:
            s = sorted(latencies)
            summary["latency"][arm] = {"mean": sum(s) / len(s), "median": s[len(s) // 2],
                                       "max": s[-1], "n": len(s)}
    return summary
