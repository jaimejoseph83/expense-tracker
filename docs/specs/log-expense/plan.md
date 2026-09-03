# Plan: log-expense

- **Spec:** [`spec.md`](spec.md)
- **Status:** Done <!-- Drafting | Approved | Executing | Done -->
- **Repository anchors:** `docs/architecture/reference.md` (golden path:
  module split, storage/validation standards) and
  `docs/adr/0001-python-stdlib-json-file-store.md` (stack decision). No
  analogous prior implementation exists — this is the repo's first feature.

> **Plan contract:** this is the implementation strategy. Unlike the spec, this
> document is allowed to change as you learn — while its Status is `Drafting`
> or `Executing`. When it changes substantially (a different approach, not just
> a re-ordering), note why in the changelog at the bottom. Once it is `Done`
> and the spec is `Shipped`, the directory freezes as a unit
> (or the adopter repository's equivalent document-lifecycle guidance).

<!-- Existing plans without this field remain valid. Treat its absence as a
named assurance gap during structural review, not a universal lint failure. -->

<!-- **Durable-plan fill.** This template is the implementation and verification
strategy for a durable delivery slice. Fill Approach, Constraints, Risks,
Design, Tasks, and Changelog to the depth the durable work requires. Its sibling
spec is the durable behavior contract. Eligible direct-light work does not
create this artifact. -->

## Approach

Three small stdlib modules, built bottom-up: `models.py` (the `Expense`
shape and its validation rules) → `store.py` (atomic JSON read/write on top
of validated models) → `cli.py` (an `argparse` entry point that wires user
input through validation into the store and reports the result). Each layer
only depends on the one below it, matching `reference.md`'s composition
rule, so each is unit-testable in isolation before the CLI wires them
together. The riskiest part is the CLI-level integration (argument parsing,
exit codes, and the store's file effects all agreeing) — that gets its own
end-to-end task and test rather than being inferred from the unit layers.
Packaging (`pyproject.toml`) and docs (README, a user guide) land last, once
the command's real behavior exists to document accurately.

## Constraints

- ADR-0001 (`docs/adr/0001-python-stdlib-json-file-store.md`): Python
  stdlib only at runtime, no new runtime dependency (`pytest` is a
  pre-approved test-only dependency); JSON file store, not a database.
- `docs/architecture/reference.md`: module signatures (`cli.py` /
  `store.py` / `models.py`), the "Expense record shape" table,
  `decimal.Decimal` for money, ISO-8601 dates, atomic writes with
  owner-only permissions on POSIX, exit code `1` (never `argparse`'s `2`)
  for every rejection, default path `~/.expense-tracker/expenses.json`
  overridable via `EXPENSE_TRACKER_FILE`, and store-level failures
  (corrupt JSON, a malformed record, an unwritable path) reported the same
  uniform way as a validation error — never a raw traceback.

## Construction tests

**Integration tests:** one end-to-end test module (`tests/test_cli_log.py`)
invoking the built `log` command against a temp store file, asserting
stdout, stderr, exit code, and resulting file contents together — including
a valid-input case, one case per rejected-input class, a corrupt-store
case, and (POSIX) a permissions check (T3).
**Manual verification:** after T4, run `expense-tracker log --amount 12.50
--category coffee --date 2026-09-01` for real against a scratch
`EXPENSE_TRACKER_FILE`, inspect the resulting JSON by eye, and (on POSIX)
confirm its permissions with `stat -f %A` / `stat -c %a`.

## Durable-output map

<!--
This section maps each task to the spec's Durable Outputs table so closeout can
verify planned output, implementation evidence, and closeout evidence without
copying requirements into a second record.

For each output, name:

- planned output
- implementing task(s)
- implementation evidence
- closeout evidence
- unresolved destination or freshness blocker, if any

If the plan's Design (LLD) contains a non-inferable design fact, map it to its
semantic owner here. Mechanically evident details may stay with code, types,
docstrings, and tests; one-off construction order may remain delivery residue.
-->

| Durable output | Tasks | Implementation evidence | Closeout evidence |
| --- | --- | --- | --- |
| Current architecture — `docs/architecture/reference.md` | T1-T3 | shipped module signatures and record shape match the doc (already updated during spec review) | `close-work` diffs the doc against the shipped code; amend either if they diverge |
| User-facing documentation — `guides/reference/log-command.md` | T4 | guide page committed | guide's flags/examples match `expense-tracker log --help` and observed behavior |
| Maintainer procedure — `README.md`, `AGENTS.md` | T4 | README usage section committed; `AGENTS.md`'s *Project overview* and *Build and test commands* placeholders replaced with verified facts | a fresh contributor can follow the README's worked example as written; `AGENTS.md` has no remaining `<...>` placeholder in those sections |
| Current product truth — `docs/product/roadmap.md` | T4 | "Now" section's placeholder replaced with a real entry linking `docs/specs/log-expense/spec.md`; `Last updated` set | roadmap.md has no remaining `<theme>`/`YYYY-MM-DD` placeholder in the touched section |

## Design (LLD)

Shape: `service`, so this scaffolds Interfaces & contracts, Data & schema,
Failure/resilience, and Quality attributes (plus Design decisions).

### Design decisions

- Validation lives in `models.py`, not `cli.py`: `Expense.from_input(...)`
  raises a single `ValidationError` with a human-readable message on any
  invalid field, so `cli.py` has exactly one place to catch and report an
  error uniformly — including a "missing" field, since `cli.py` never marks
  a flag `required=True` in `argparse` (that would produce `argparse`'s own
  usage error and exit `2`, not this spec's `error: `/exit-`1` shape).
  Traces to: AC9, AC12 · none.
- A blank `--description` (empty or whitespace-only after `strip()`) is
  normalized to `None`/`null` in `models.py`, the same place blank
  `--category` is rejected — one function owns "what counts as blank".
  Traces to: AC5 · none.
- `store.py` owns *both* store-level failure classes uniformly: a
  `json.JSONDecodeError`/non-list top level on `load()`, a malformed
  individual record (missing/extra key, unparseable date) on
  `Expense.from_dict()` during `load()`, and an `OSError` from `mkdir`/open
  on `save()` are all wrapped in `StoreError` and reported through the same
  `cli.py` path as a validation error. Traces to: AC10, AC11, AC12 · none.
- `store.append()` does read-validate-write of the *whole* file rather than
  a line-append, because the store is a single JSON array (not JSONL) — a
  format chosen for readability. Acceptable at the scale this project
  targets (see `reference.md`'s quality-goal strategy). AC13's bar is
  field-level equality, order, and append-last position, not byte identity,
  precisely because this mechanism reserializes the whole file. Traces to:
  AC3, AC13, AC16 · none.
- No `created_at` or other bookkeeping field: record order in the JSON array
  is insertion order, which is enough until a feature genuinely needs
  something else (`reference.md`'s "Expense record shape" table is the
  living record of this). Traces to: AC17 · none.

### Data & schema

Each record, as stored in the JSON array — the exact shape is
`docs/architecture/reference.md`'s "Expense record shape" table; this is a
worked instance of it, not a second copy of the rule:

```json
{
  "id": "b3f1...-uuid4",
  "amount": "42.50",
  "category": "groceries",
  "start_date": "2026-08-30",
  "end_date": "2026-08-30",
  "description": null
}
```

Traces to: AC2, AC3, AC4, AC5, AC6, AC7, AC14, AC17 · none.

### Interfaces & contracts

CLI surface (no `contracts/` entry — a local CLI, not a published API):

```
expense-tracker log --amount AMOUNT --category CATEGORY --date DATE
                     [--end-date END_DATE] [--description DESCRIPTION]
```

All five flags are parsed as `argparse` optionals (none `required=True` —
see Design decisions) so missingness is validated uniformly by
`models.py`. The target file is resolved once, at `run_log` entry, via
`store.default_path()`: `EXPENSE_TRACKER_FILE` if set and non-empty, else
`~/.expense-tracker/expenses.json` (AC8).

- `--amount`: a positive number, 0-2 fractional digits, no sign, no
  scientific notation, no surrounding whitespace (AC1).
- `--category`: non-blank free text.
- `--date`: `YYYY-MM-DD`, the expense's start date.
- `--end-date` (optional): `YYYY-MM-DD`, on or after `--date`; defaults to
  `--date`.
- `--description` (optional): free text; blank normalizes to `null`.

On success: stdout is exactly the new record's `id` plus a newline, exit
`0`. On any rejected input or store-level failure: `error: <message>` on
stderr, nothing on stdout, exit `1`, no file mutation. Traces to: AC1, AC8,
AC9, AC10, AC11, AC12, AC14 · none.

### Failure, edge cases & resilience

- Invalid input (bad amount/category/date/date-order, or a missing flag) is
  caught in `models.py` before the store is touched — fail closed, no
  partial write. Traces to: AC9, AC13.
- A crash between "compute new contents" and "commit" cannot corrupt the
  store: `store.save()` writes via `tempfile.NamedTemporaryFile(dir=<store
  dir>, delete=False)` (mode `0600` by construction on POSIX), then
  `os.replace(tmp, path)`, which is atomic on the platforms this project
  targets and preserves the temp file's mode. Traces to: AC13, AC15, AC18.
- A missing store file or missing parent directory is created on first
  successful write, not treated as an error. Traces to: AC15.
- A store file that fails to load — unparseable JSON, a non-list top
  level, a malformed individual record, or an `OSError` reading/creating
  the path — is a `StoreError`, reported the same way as a validation error
  (`error: ...` on stderr, exit `1`), never silently overwritten and never
  a raw traceback. Traces to: AC10, AC11, AC12.

### Quality attributes (NFRs)

No NFR in this spec carries a numeric pass/fail bar (per `reference.md`,
this is a small local CLI with no throughput/latency target) — none to
design against here.

> **Rollout & deployment** — the tenth design dimension — is **not** a
> sub-heading here. It is realized by [`## Rollout`](#rollout) below (infra,
> external-system integration, deployment sequencing). Cross-link it from the
> relevant sub-sections; never duplicate it.

## Tasks

Four tasks, strictly sequential (each depends on the last): `models.py` →
`store.py` → `cli.py` → packaging/docs.

### T1: `models.py` — `Expense` shape and validation

**Mode:** TDD

**Depends on:** none

**Tests:**
- `test_accepts_valid_amount_forms` (AC1) — stub: true
- `test_rejects_invalid_amount_forms` (AC1, AC9) — stub: true
- `test_amount_stored_exactly_as_given` (AC2)
- `test_builds_record_from_valid_amount_category_date` (AC3)
- `test_description_given_is_kept` (AC4)
- `test_description_omitted_or_blank_is_null` (AC5)
- `test_end_date_defaults_to_start_date` (AC6)
- `test_end_date_given_on_or_after_start` (AC7)
- `test_end_date_before_start_is_rejected` (AC7, AC9)
- `test_missing_or_blank_category_is_rejected` (AC9)
- `test_missing_or_invalid_date_is_rejected` (AC9)
- `test_to_dict_from_dict_round_trip_and_key_set` (AC17)

```python
# STUB: AC1 — accepted --amount forms parse to Decimal, stored string unchanged
# Stored and validated in PLAN's T1 Tests: subsection.
from decimal import Decimal

from expense_tracker.models import Expense


def test_accepts_valid_amount_forms():
    for raw in ("12", "12.5", "12.50"):
        expense = Expense.from_input(
            amount=raw, category="coffee", date="2026-09-01",
            end_date=None, description=None,
        )
        assert expense.amount == Decimal(raw)          # full: parses correctly
        assert expense.to_dict()["amount"] == raw       # full: exact stored string
```

```python
# STUB: AC1 — rejected --amount forms raise ValidationError
# Stored and validated in PLAN's T1 Tests: subsection. Paired with the
# accepting stub above so this exclusion test is falsifiable, not vacuous.
from expense_tracker.models import Expense, ValidationError

REJECTED_AMOUNTS = [
    None, "0", "0.00", "-5", "abc", "NaN", "Infinity",
    "12.555", "+5", "1e5", " 12", "12 ", "12\n",
]


def test_rejects_invalid_amount_forms():
    for raw in REJECTED_AMOUNTS:
        try:
            Expense.from_input(
                amount=raw, category="coffee", date="2026-09-01",
                end_date=None, description=None,
            )
        except ValidationError:
            continue
        raise AssertionError(f"amount={raw!r} should have been rejected")
```

Compiled and validated from disposable scratch (2026-09-01): both blocks
pass `python3 -m py_compile`. `pytest` is not installed in this environment
(it is T4's job to declare it as a test-only dependency), so the intended
red was proved by direct execution rather than pytest collection: both
blocks fail at `from expense_tracker.models import ...` with
`ModuleNotFoundError: No module named 'expense_tracker.models'` against the
current empty tree — a genuine red, not a vacuous pass. Isolation downgrade
recorded: scratch execution ran without `pytest`'s own sandboxing; both
files were removed after validation. Recorded here per
`work-loop/references/tdd-stubs.md`; no repository test file created.

**Approach:**
- Define `Expense` as a frozen `dataclass`: `id`, `amount: Decimal`,
  `category: str`, `start_date: date`, `end_date: date`,
  `description: str | None`.
- `Expense.from_input(amount, category, date, end_date, description)`:
  - `amount`: reject `None`/non-`str`; match against
    `re.fullmatch(r"\A[0-9]+(\.[0-9]{1,2})?\Z", amount)` (`\A`/`\Z`, not
    `^`/`$` — `$` matches before a trailing newline in Python's `re`, which
    would let `"12\n"` slip through); reject if it doesn't match or parses
    to `<= 0`; on success, keep the original string for storage alongside
    the parsed `Decimal`.
  - `category`: reject `None` or blank-after-`strip()`.
  - `description`: `None`, or blank-after-`strip()`, normalizes to `None`;
    otherwise kept as given.
  - `date`/`end_date`: parse via `date.fromisoformat`, catching
    `ValueError`; default `end_date` to `date` when not given; reject when
    `end_date < date`.
  - Raise `ValidationError(message)` on the first failure, otherwise return
    a new `Expense` with a fresh `uuid4()` id.
- `to_dict()` / `from_dict()` for the JSON shape in the plan's Data &
  schema section — exactly the six keys, no more; `from_dict()` raises
  `ValueError` on a missing/extra key or an unparseable date, for
  `store.py` (T2) to wrap.

**Done when:** `pytest tests/test_models.py` is green.

### T2: `store.py` — atomic JSON read/write

**Mode:** TDD

**Depends on:** T1

**Tests:**
- `test_default_path_env_override` — `default_path()` returns
  `~/.expense-tracker/expenses.json` by default and the
  `EXPENSE_TRACKER_FILE` value when that env var is set to a non-empty
  string. (AC8)
- `test_save_creates_missing_parent_dir` (AC15) — stub: true
- `test_save_preserves_existing_and_appends_last` — given N existing
  records plus one new one, `save()` results in a file whose first N
  records equal the originals (same `id`/fields/order) and whose last
  record is the new one. (AC16)
- `test_save_sets_owner_only_permissions` — on POSIX, after `save()`, the
  file's mode is `0600`. (AC18)
- `test_load_missing_path_returns_empty_list` — `load()` on a
  non-existent path returns `[]`. (AC15)
- `test_load_raises_store_error_on_unparseable_json` — invalid JSON or a
  non-list top level. (AC10)
- `test_load_raises_store_error_on_malformed_record` — a well-formed JSON
  array containing one record with a missing/extra key or bad date; wraps
  `Expense.from_dict`'s `ValueError`. (AC10, AC17)
- `test_save_raises_store_error_on_unwritable_path` — `mkdir`/open raising
  `OSError` is wrapped in `StoreError`, not left to propagate. (AC11)
- `test_append_loads_adds_saves_without_losing_existing` — `append()` =
  `load()` + one record + `save()`. (AC3, AC16)

```python
# STUB: AC15 — save() creates a missing store file and parent directory
# Stored and validated in PLAN's T2 Tests: subsection.
import json

from expense_tracker.store import save


def test_save_creates_missing_parent_dir(tmp_path):
    target = tmp_path / "nested" / "expenses.json"
    save(target, [])
    assert target.exists()                              # full: file created
    assert json.loads(target.read_text()) == []          # full: valid empty array
```

Compiled and validated from disposable scratch (2026-09-01): the block
passes `python3 -m py_compile`; direct execution fails at `from
expense_tracker.store import save` with `ModuleNotFoundError: No module
named 'expense_tracker.store'` against the current empty tree — a genuine
red. Same isolation-downgrade note as T1 (no `pytest` installed in this
environment); scratch file removed after validation.

**Approach:**
- `default_path()` reads `EXPENSE_TRACKER_FILE` if set and non-empty, else
  `Path.home() / ".expense-tracker" / "expenses.json"`.
- `load(path) -> list[Expense]`: missing file → `[]`; present file →
  `json.load`, requiring a top-level list (else `StoreError`), then
  `Expense.from_dict` per record — catching `json.JSONDecodeError` and any
  `ValueError`/`KeyError` from `from_dict` and re-raising as `StoreError`.
- `save(path, records)`: `path.parent.mkdir(parents=True, exist_ok=True)`;
  `tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False)` →
  write `json.dumps([r.to_dict() for r in records])`, flush, close; then
  `os.replace(tmp.name, path)`. Any `OSError` from `mkdir` or the temp-file
  open/write is caught and re-raised as `StoreError`.
- `append(path, record)`: `save(path, load(path) + [record])` — the new
  record is last because it's appended to the end of the loaded list.

**Done when:** `pytest tests/test_store.py` is green.

### T3: `cli.py` — the `log` command end-to-end

**Mode:** Visual / manual QA — `no stub (visual/manual QA)`, per
`work-loop/references/tdd-stubs.md`; this task's obligation is the
integration test below, not a PLAN-time stub.

**Depends on:** T1, T2

**Tests:**
- Integration test (`tests/test_cli_log.py`) invoking the CLI's `main()`
  with a temp `EXPENSE_TRACKER_FILE`:
  - valid args → stdout is exactly the new id followed by a newline, exit
    code `0`, file contains exactly one record matching the args. (AC3,
    AC4, AC5, AC6, AC7, AC14, AC15, AC17)
  - each rejected-input class from T1 (bad amount, blank category, bad
    date, bad/backwards end-date, missing flag) → stderr is exactly one
    line starting `error: `, nothing on stdout, exit code `1`, file
    unchanged or still absent. (AC1, AC9, AC12, AC13)
  - a pre-existing store file containing invalid JSON → stderr starts
    `error: `, nothing on stdout, exit code `1`, file byte-unchanged.
    (AC10, AC12, AC13)
  - a second valid invocation against an already-populated file → both
    records present afterward, original first, new one last. (AC16)
  - (POSIX only) after a successful run, the store file's mode is `0600`.
    (AC18)
  - `EXPENSE_TRACKER_FILE` unset vs. set to a scratch path resolves to the
    two different files respectively. (AC8)

**Approach:**
- `build_parser()`: `argparse.ArgumentParser` with a `log` subcommand and
  the five flags from the plan's Interfaces & contracts section — none
  marked `required=True`; missingness is a `None` passed through to
  `Expense.from_input`.
- `run_log(args)`: calls `Expense.from_input(...)`, catches
  `ValidationError`/`StoreError`, prints `error: {message}` to stderr and
  returns exit code `1`; on success calls `store.append(default_path(),
  expense)`, prints `expense.id` to stdout, returns `0`.
- `main(argv=None)`: parses args, dispatches to `run_log`, returns its exit
  code; `if __name__ == "__main__": sys.exit(main())`.

**Done when:** `pytest tests/test_cli_log.py` is green — this is the
Testing Strategy's Visual/manual QA mode, satisfied by the integration test
exercising the real built entry point end-to-end.

### T4: Packaging and docs

**Depends on:** T3

**Tests:** none — goal-based check (build config + documentation, not
logic).

**Approach:**
- Add `pyproject.toml`: package `expense_tracker`, console-script
  `expense-tracker = expense_tracker.cli:main`, and
  `[project.optional-dependencies] test = ["pytest"]` (a test-only
  dependency, not a runtime one — see `reference.md`).
- Update `README.md`: install (`pip install -e ".[test]"` for
  contributors, `pip install -e .` for just running it), and a worked
  `log` example with its output.
- Replace `AGENTS.md`'s *Project overview* and *Build and test commands*
  placeholders with the verified facts: what this project is, `pip install
  -e ".[test]"`, `pytest` as the test command, and lint recorded as "none
  configured yet" (not invented).
- Write `guides/reference/log-command.md` (repo-root `guides/`, per
  `docs/CONVENTIONS.md` § 5c): the `log` command's flags, defaults, exit
  codes, and one worked example (Diátaxis *reference*).
- Update `docs/product/roadmap.md`: replace the "Now" section's `<theme>`
  placeholder with a real entry for expense logging linking this spec, and
  set `Last updated` to today's date.

**Done when:** `pip install -e .` succeeds and `expense-tracker log
--amount 12.50 --category coffee --date 2026-09-01` run for real against a
scratch `EXPENSE_TRACKER_FILE` produces the documented output.


## Rollout

Local CLI, nothing deployed: no flag, no gradual rollout, no infrastructure,
no external-system dependency, no deployment sequencing. Shipping means
merging the PR; installing means `pip install -e .` on the user's own
machine.

## Risks

- **JSON-array read-validate-write doesn't scale forever.** Fine at
  personal-expense-log volumes; if it ever becomes a real problem, ADR-0001
  already names the re-evaluation trigger (revisit storage engine), so this
  isn't a silent risk.
- **`os.replace` atomicity assumption.** Relied on for crash-safety (T2);
  true on POSIX and Windows for same-filesystem replaces, which holds here
  since the temp file is written beside the target — worth a one-line
  comment in `store.py` so a future change doesn't move the temp file
  off-filesystem without noticing.

## Changelog

- 2026-09-01: initial plan.
- 2026-09-01: revised per shaping review — dropped `created_at` (unrequested
  scope); made all CLI flags `argparse`-optional so missingness validates
  uniformly through `models.py` instead of triggering `argparse`'s own
  usage error; replaced the unsatisfiable "byte-for-byte" append bar with a
  field-level one; gave `--amount` a closed accepted-format grammar instead
  of an exclusion list; added store-corruption and file-permission handling
  and their tests; added `pytest` as a declared test-only dependency; added
  `AGENTS.md` to the durable-output map; confirmed the `guides/` root
  against CONVENTIONS.
- 2026-09-02: third revision — rewrote T1 reject-stub to remove `import
  pytest` (stub now uses try/except/raise so it compiles and runs red
  without pytest installed; validation note now accurate: both stubs fail at
  `from expense_tracker.models import ...`); corrected all AC references
  throughout Tasks, Design decisions, Data & schema, Interfaces & contracts,
  and Failure/resilience sections to match the final AC1–AC18 numbering from
  the third shaping-review revision (AC9–AC15 → AC9–AC18 after the
  rejection-reporting split).
- 2026-09-01: second revision per shaping review round 2 — added a
  criterion for which store file is read/written (AC8); normalized blank
  `--description` to `null` (AC5); extended store-failure handling and its
  criteria to cover an unwritable path and a malformed individual record,
  not just corrupt JSON (AC9/AC10); pinned the new record as strictly
  appended last (AC13); made the stdout contract exact and silent on
  rejection (AC11, AC9); re-anchored the schema criterion to "after a
  successful write" instead of an unverifiable "ever contains" (AC14);
  split the amount and rejection criteria along their independent failure
  modes (AC1/AC2, AC9/AC10); added `docs/product/roadmap.md` to the
  durable-output map; declared TDD mode on T1/T2 explicitly and
  `no stub (visual/manual QA)` on T3; fixed the amount regex's `$`
  trailing-newline gap (`\A…\Z`); added and validated (`py_compile` +
  direct-execution red, `pytest` not installed in this environment) real
  stub blocks for T1 and T2.
