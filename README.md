# refactoring-oracle

A small fixture of Python refactoring cases and a deterministic grader that
says whether a candidate refactoring is correct, with no model and no human in
the loop.

It exists because a thread claimed frontier coding agents do common
refactorings "quite reliably", a reply said "quite reliably is not enough",
and nobody had a number. Nobody had a number because nobody had a grader.
This is the grader. The things it grades (an LLM through the API, a coding
agent, a deterministic tool such as rope) come later and are not in this repo
yet.

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

## Commands

```bash
uv sync --group dev
uv run pytest -q                  # oracle unit tests plus the selfcheck over every case
uv run ro-selfcheck               # the same, as a table
uv run ro-grade extract-function/parking-fee cases/extract-function/parking-fee/after
uv run ro-grade extract-function/parking-fee cases/extract-function/parking-fee/before
uv run ro-grade <case-id> <candidate-dir> --json
uv run ro-freeze
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
src/refactoring_oracle/cli.py          ro-grade, ro-selfcheck, ro-freeze
tests/                                 unit tests, selfcheck, house rules
```
