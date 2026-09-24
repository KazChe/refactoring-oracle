"""ro-grade, ro-selfcheck, ro-freeze."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from refactoring_oracle import freeze, report
from refactoring_oracle.case import CASES_ROOT, find_case, load_all
from refactoring_oracle.oracle import expected_failure_class, grade
from refactoring_oracle.runner import RunConfig, run


def grade_main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ro-grade", description="Grade one candidate tree.")
    p.add_argument("case_id", help="<refactoring>/<sample>")
    p.add_argument("candidate", type=Path)
    p.add_argument("--json", action="store_true", help="print the full verdict as JSON")
    p.add_argument("--allow-drift", action="store_true",
                   help="grade even if cases/ no longer matches cases.sha256")
    args = p.parse_args(argv)
    if not args.allow_drift:
        try:
            freeze.check_frozen()
        except freeze.FixtureDrift as exc:
            print(f"refusing: {exc}", file=sys.stderr)
            return 2
    case = find_case(args.case_id)
    verdict = grade(case, args.candidate)
    if args.json:
        print(json.dumps(verdict.model_dump(), indent=2))
    else:
        print(verdict.summary_line())
        _print_failures(verdict)
    return 0 if verdict.overall else 1


def _print_failures(verdict) -> None:
    d = verdict.details
    if not verdict.compiles:
        for e in d["compiles"]["errors"]:
            print(f"  compile: {e}")
        return
    if verdict.behavior is False:
        print(f"  behavior: {d['behavior']['summary']}")
        if d["behavior"].get("first_failure"):
            print(f"            {d['behavior']['first_failure']}")
    for c in d.get("shape", []):
        if not c["ok"]:
            print(f"  shape: {c['message']}  [{c['assertion']}]")
    for problem in d.get("collateral", []):
        print(f"  collateral: {problem}")


def selfcheck_main(argv: list[str] | None = None) -> int:
    """Every after passes; every before fails; every mutant fails where its name says."""
    p = argparse.ArgumentParser(prog="ro-selfcheck")
    p.add_argument("--root", type=Path, default=CASES_ROOT)
    args = p.parse_args(argv)
    cases = load_all(args.root)
    if not cases:
        print("no cases found", file=sys.stderr)
        return 2
    bad = 0
    print(f"{'case':40} {'after':6} {'before':10} mutants")
    for case in cases:
        after = grade(case, case.after_dir)
        before = grade(case, case.before_dir)
        mutant_bits: list[str] = []
        for name, path in case.mutants():
            want = expected_failure_class(name)
            got = grade(case, path).failure_class
            ok = got == want
            bad += 0 if ok else 1
            mutant_bits.append(f"{name}:{got}{'' if ok else '!'}")
        after_ok = after.overall
        before_ok = not before.overall
        bad += (0 if after_ok else 1) + (0 if before_ok else 1)
        print(
            f"{case.id:40} {'PASS' if after_ok else 'FAIL':6} "
            f"{before.failure_class + ('' if before_ok else '!'):10} "
            + (" ".join(mutant_bits) or "-")
        )
        if not after_ok:
            _print_failures(after)
    print(f"\n{len(cases)} case(s), {bad} problem(s)")
    return 0 if bad == 0 else 1


def freeze_main(argv: list[str] | None = None) -> int:
    digest = freeze.freeze()
    print(f"froze cases/: sha256 {digest}")
    return 0


def load_dotenv(path: Path = CASES_ROOT.parent / ".env") -> None:
    """Minimal .env loader: KEY=VALUE lines, environment wins."""
    import os

    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def run_main(argv: list[str] | None = None) -> int:
    import os

    load_dotenv()
    p = argparse.ArgumentParser(prog="ro-run", description="Run arms over the frozen cases.")
    p.add_argument("--arms", default="api-bare,api-skill")
    p.add_argument("--runs", type=int, default=int(os.environ.get("RO_RUNS", "3")))
    p.add_argument("--out", type=Path, default=Path("runs/api-results.json"))
    p.add_argument("--cases", default=None, help="comma-separated case ids")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="reference arm, no network")
    p.add_argument("--model", default=os.environ.get("RO_MODEL", "claude-sonnet-4-6"))
    p.add_argument("--allow-drift", action="store_true")
    p.add_argument("--report-only", action="store_true")
    args = p.parse_args(argv)
    if args.report_only:
        sys.stdout.write(report.render(json.loads(args.out.read_text(encoding="utf-8"))))
        return 0
    arms = [a.strip() for a in args.arms.split(",") if a.strip()]
    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("ANTHROPIC_API_KEY is required", file=sys.stderr)
        return 2
    cfg = RunConfig(
        arms=arms, runs=args.runs, out=args.out, resume=args.resume,
        case_ids=[c.strip() for c in args.cases.split(",")] if args.cases else None,
        dry_run=args.dry_run, model=args.model, allow_drift=args.allow_drift,
        progress=lambda s: (sys.stderr.write(s), sys.stderr.flush()),
    )
    print(f"arms={','.join(arms)} runs={cfg.runs} model={cfg.model} out={cfg.out} "
          f"dry_run={cfg.dry_run} resume={cfg.resume}", file=sys.stderr)
    try:
        artifact = run(cfg)
    except freeze.FixtureDrift as exc:
        print(f"refusing to run: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(report.render(artifact))
    errors = sum(1 for t in artifact["trials"].values() if t["arm"].get("error"))
    return 1 if errors else 0
