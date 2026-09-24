# refactoring-oracle

A small fixture of Python refactoring cases and a deterministic grader that
says whether a candidate refactoring is correct, with no model and no human in
the loop.

It exists because a thread claimed frontier coding agents do common
refactorings "quite reliably", a reply said "quite reliably is not enough",
and nobody had a number. Nobody had a number because nobody had a grader.
This is the grader, plus five things it grades: Claude through the API, bare
and with a refactoring skill; Claude Code run headless, bare and with the same
skill; and rope, the deterministic refactoring library for Python.

## The oracle

`grade(case, candidate_dir)` runs four checks, in order, and names the first
one that fails:

| check | question | how |
| --- | --- | --- |
| compiles | Does every file parse? | in-memory `compile()` of each `.py` |
| behavior | Is behavior preserved? | a held-out pytest suite, written against the target interface the instruction named, run in a subprocess the candidate never saw |
| shape | Was the refactoring actually done? | AST assertions from `case.json`: the dataclass exists with these fields, the function now takes one parameter, the old name is gone, the body starts with a guard, no literal 85 remains inside `status` |
| collateral | Was anything else touched? | files outside `allowed_files` byte-identical to `before/`, `protected` definitions with an identical AST, no new imports beyond `allowed_imports` |

The verdict's `failure_class` splits the usual argument into measurable
parts: changed behavior (the fear), did not refactor (the shortcut), touched
things it should not have (the reason people review every line).

What it does not judge: style, naming beyond the named interface, or whether
the refactoring was a good idea.

## The fixture keeps itself honest

`ro-selfcheck` and `tests/test_selfcheck.py` enforce, for every case:

- the reference `after/` passes all four checks;
- the untouched `before/` fails the shape check (so the assertions bite);
- a hand-written `mutants/behavior_*` candidate, a subtly wrong version of the
  changed function, fails on behavior and nothing earlier;
- a synthetic collateral mutant (one byte appended to the never-allowed
  `__init__.py`) fails on collateral, and a synthetic compile mutant fails on
  compiles.

If any of those stops holding, the fixture is wrong, not the thing being
graded.

## The cases

Six refactorings, two fresh samples each, no examples from Fowler or from
anyone's skill library. Each case's instruction names the target interface
exactly, the way a person would ask, so grading needs no interpretation.

| refactoring | samples | rope can do it |
| --- | --- | --- |
| extract-function | parking-fee, shipping-quote | yes, `rope.refactor.extract.ExtractMethod` |
| inline-function | log-parser, loyalty-ledger | yes, `rope.refactor.inline.InlineMethod` |
| rename | meeting-slots, csv-cleaner | yes, `rope.refactor.rename.Rename` |
| introduce-parameter-object | invoice-line, room-booking | no |
| replace-magic-literal | temperature-alerts, late-fees | only within a scope; no module-level hoist |
| guard-clauses | discount-eligibility, ticket-refund | no |

Case layout:

```
cases/<refactoring>/<sample>/
  case.json      id, instruction, allowed_files, protected, allowed_imports,
                 deterministic_tool, shape assertions
  before/        what an arm is given: the module, __init__.py (never allowed), tests/
  after/         the reference solution; never shown to an arm
  tests_after/   the held-out suite
  mutants/       behavior_<name>/ candidate trees that must fail on behavior
```

The whole `cases/` tree is frozen by `ro-freeze` into `cases.sha256`, and
`ro-grade` refuses to run if it has drifted.

## The arms

An arm gets a fresh copy of a case's `before/` tree and the instruction,
produces a candidate tree, and the oracle grades it. The arm is the only
variable.

| arm | what edits the code |
| --- | --- |
| `api-bare` | One Messages API call to `claude-sonnet-4-6`: a frozen system prompt, the instruction, every file in `before/`, and one forced `write_files` tool that returns the changed files whole |
| `api-skill` | The same call with the case's skill prepended to the system prompt |
| `agent-bare` | Claude Code, `claude -p`, run inside a copy of `before/` with `--bare` (no global CLAUDE.md, memory, hooks, or plugins), `acceptEdits`, a $1 budget per trial, and JSON output. It can read the tree, run the before tests, and edit in place |
| `agent-skill` | The same, with the case's skill appended to the system prompt through `--append-system-prompt-file` |
| `rope` | `rope.refactor` driven by per-case offset specs in `arms/rope_arm.py`, for the three refactorings rope implements. The other three are reported as `unsupported` |

### Skills

Jason Gorman's format from the thread: a name, a one-line description, a
one-paragraph summary, and one before/after example. One file per refactoring
in `skills/`, with examples in domains that are not in the fixture. The rename
one, complete:

```markdown
---
name: rename
description: Rename refactoring for Python. Use when asked to rename a function, parameter, or variable everywhere it is used.
---
# Rename

Change a name at its definition and at every use, including call sites, keyword arguments, docstrings, and tests that reference it. Only the name changes.

Example:

def calc(amt, pct):
    """Apply pct to amt."""
    return amt * pct / 100

def tax(amt):
    return calc(amt, 8)

Rename `calc` to `apply_percent` and `amt` to `amount`.

def apply_percent(amount, pct):
    """Apply pct to amount."""
    return amount * pct / 100

def tax(amount):
    return apply_percent(amount, 8)
```

The prompt and the skills are hashed into every artifact's meta. `ro-run`
runs each arm over each case N times, sequentially, copies `before/` per
trial, applies the returned files, grades, keeps the unified diff, and rewrites
the artifact after every trial so a killed run resumes. `--dry-run` swaps in a
reference arm that copies `after/` and needs no key.

## Results: five arms, twelve cases, three runs each

Artifacts in `runs/`: `api-results.json`, `agent-results.json`,
`rope-results.json`, all from 2026-09-24. Model `claude-sonnet-4-6` for the
four model arms. Every trial starts from a fresh copy of `before/`.

| arm | pass | behavior | shape | collateral | compiles | unsupported | per trial | total |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| api-bare | 33/36 | 0 | 3 | 0 | 0 | 0 | $0.009, 4.1 s | $0.32 |
| api-skill | 33/36 | 0 | 3 | 0 | 0 | 0 | $0.010, 4.2 s | $0.35 |
| agent-bare | 36/36 | 0 | 0 | 0 | 0 | 0 | $0.028, 19 s, 5.4 turns | $1.00 |
| agent-skill | 35/36 | 0 | 1 | 0 | 0 | 0 | $0.028, 21 s, 5.2 turns | $1.00 |
| rope | 4/12 | 2 | 0 | 0 | 0 | 6 | free, instant | $0 |

Across 144 model trials: zero behavior changes, zero files or functions
touched outside the instruction, zero compile errors. Every miss by a model
is the same one case.

**The one case.** `guard-clauses/discount-eligibility` asks for guard clauses
"so that no if statement is nested inside another if". Both API arms produced,
on every run, a byte-identical version with one nested `if` under
`if order_total >= 100:`. The tests pass and it is a reasonable guard-clause
rewrite; it violates the letter of the instruction, and the reference met the
constraint with a conditional expression. The bare agent passed all three
runs by writing `if order_total >= 100 and coupon == "SAVE20": return 0.2`
followed by `if order_total >= 100: return 0.1`. The agent with the skill
passed twice and produced the API arms' nested version once.

**The skill.** No effect on the API arm (same outputs, same miss, about 200
more input tokens) and one extra miss on the agent arm. On this fixture the
model already knew all six refactorings; the before/after example added
nothing it needed.

**The harness.** Same model, same instruction, different result: the one-shot
rewrite missed the constraint every time and the agent met it every time.
The agent can read the whole tree, run the before tests, and revise; it used
about five turns per case and cost three times as much.

**The deterministic tool.** rope passed both renames and both inlines. On
both extract cases it produced a working function with the parameters in the
order it chose, `evening_discount(entered_hour, base)` and
`validate(zone, weight_kg)`, not the order the instruction named, so the
held-out tests that call the new function positionally fail. rope cannot be
told the target interface. The other six cases (parameter object, magic
literal, guard clauses) have no rope refactoring at all.

What this is not: twelve cases, one model, small files, and instructions
written to be gradable. It is a shape, not a benchmark.

## Commands

```bash
uv sync --group dev
cp .env.example .env              # ANTHROPIC_API_KEY, only needed for live arms
uv run pytest -q                  # oracle unit tests plus the selfcheck over every case
uv run ro-selfcheck               # the same, as a table
uv run ro-grade extract-function/parking-fee cases/extract-function/parking-fee/after
uv run ro-grade extract-function/parking-fee cases/extract-function/parking-fee/before
uv run ro-grade <case-id> <candidate-dir> --json
uv run ro-freeze
uv run ro-run --dry-run                          # reference arm, no network
uv run ro-run --cases rename/csv-cleaner --runs 1 --out runs/smoke.json
uv run ro-run --runs 3 --out runs/api-results.json
uv run ro-run --arms agent-bare,agent-skill --runs 3 --out runs/agent-results.json   # needs the claude CLI
uv run ro-run --arms rope --runs 1 --out runs/rope-results.json                      # local, free
uv run ro-run --report-only --out runs/api-results.json
```

## Shape assertion kinds

`defines_function` (name, optional exact params), `not_defines`,
`defines_class` (optional dataclass flag and exact field order), `calls`
(callee inside a function), `no_call` (file-wide or inside one function),
`defines_constant` (module-level, exact value and type), `no_literal` (inside
a function; 1 and True are different literals), `starts_with_guard`,
`max_if_depth`, `name_absent`, `name_present`. Methods are addressed as
`Class.method`.

## Layout

```
src/refactoring_oracle/case.py         Case and ShapeAssertion models, loading
src/refactoring_oracle/shape.py        the assertion kinds
src/refactoring_oracle/collateral.py   byte, AST, and import comparisons
src/refactoring_oracle/behavior.py     compile check and the pytest subprocess
src/refactoring_oracle/oracle.py       grade() and the Verdict
src/refactoring_oracle/freeze.py       hash of the cases tree
src/refactoring_oracle/cli.py          ro-grade, ro-selfcheck, ro-freeze, ro-run
src/refactoring_oracle/prompts.py      the frozen system prompt, tool, and skill loading
src/refactoring_oracle/arms/api.py     the two API arms and the dry-run reference arm
src/refactoring_oracle/arms/agent.py   the two Claude Code headless arms
src/refactoring_oracle/arms/rope_arm.py  rope, with per-case offset specs
src/refactoring_oracle/runner.py       trials, checkpointed artifact, summary
src/refactoring_oracle/report.py       stdout tables
skills/                                one Gorman-style skill per refactoring
runs/                                  committed artifacts and captured output
tests/                                 unit tests, selfcheck, house rules
```
