"""Stdout report over a run artifact."""

from __future__ import annotations

from typing import Any

from refactoring_oracle.runner import CLASSES

SHORT = {"none": "pass", "compiles": "comp", "behavior": "beh", "shape": "shape",
         "collateral": "coll", "arm_error": "err", "unsupported": "n/a"}


def render(artifact: dict[str, Any]) -> str:
    meta, summary, cases = artifact["meta"], artifact["summary"], artifact["cases"]
    out: list[str] = []
    w = out.append
    w(f"refactoring-oracle run  status={meta['status']}  dry_run={meta['dry_run']}  "
      f"model={meta['model']}  runs={meta['runs_requested']}")
    w(f"  cases sha {meta['cases_sha256'][:12]}  prompt sha {meta['prompt_sha256'][:12]}  "
      f"skills sha {meta['skills_sha256'][:12]}  commit {(meta['git_commit'] or 'n/a')[:12]}")

    arms = meta["arms"]
    w("")
    w("Per case, outcome of each run (pass, or the first failing check)")
    hdr = f"{'case':42} {'tool':5} " + "  ".join(f"{a:>20}" for a in arms)
    w(hdr)
    w("-" * len(hdr))
    for case_id in sorted(cases):
        tool = "rope" if cases[case_id]["deterministic_tool"] else "-"
        cells = []
        for a in arms:
            runs = summary["per_arm_case"].get(a, {}).get(case_id, [])
            cells.append(f"{'/'.join(SHORT[r] for r in runs):>20}")
        w(f"{case_id:42} {tool:5} " + "  ".join(cells))

    w("")
    w("Per arm")
    w(f"  {'arm':10} {'trials':>6} " + " ".join(f"{SHORT[c]:>6}" for c in CLASSES) + "   pass rate")
    for a in arms:
        p = summary["per_arm"][a]
        rate = "n/a" if p["pass_rate"] is None else f"{p['pass_rate'] * 100:5.1f}%"
        w(f"  {a:10} {p['trials']:6} " + " ".join(f"{p[c]:6}" for c in CLASSES) + f"   {rate}")

    w("")
    w("Per arm and refactoring: pass / trials")
    refs = sorted({c["refactoring"] for c in cases.values()})
    w(f"  {'refactoring':28} " + "  ".join(f"{a:>10}" for a in arms))
    for r in refs:
        cells = []
        for a in arms:
            x = summary["per_arm_refactoring"][a].get(r)
            cells.append(f"{x['none']:>4}/{x['trials']:<5}" if x else f"{'-':>10}")
        w(f"  {r:28} " + "  ".join(cells))

    w("")
    w("Repeatability (per case across runs)")
    for a in arms:
        r = summary["repeatability"][a]
        w(f"  {a:10} same outcome every run {r['same_outcome_every_run']}/{r['cases']}, "
          f"passed every run {r['passed_every_run']}/{r['cases']}, "
          f"passed at least once {r['passed_at_least_once']}/{r['cases']}")

    w("")
    w("Cost and latency per trial")
    for a in arms:
        u = summary["usage"].get(a, {})
        c = summary["cost_per_trial"].get(a)
        lat = summary["latency"].get(a)
        cost = "n/a" if c is None else f"${c:.4f}"
        total = f"${u['total_usd']:.2f}" if "total_usd" in u else "n/a"
        lt = "n/a" if not lat else f"mean {lat['mean']:,.0f} ms, max {lat['max']:,.0f} ms"
        turns = f"; mean turns {u['mean_turns']:.1f}" if "mean_turns" in u else ""
        w(f"  {a:11} {cost} per trial, {total} total over {u.get('calls', 0)} calls; "
          f"{u.get('input_tokens', 0)} in / {u.get('output_tokens', 0)} out tokens; {lt}{turns}")
    return "\n".join(out) + "\n"
