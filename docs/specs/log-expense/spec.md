# Spec: log-expense

- **Status:** Shipped <!-- Draft | Approved | Implementing | Shipped | Archived -->
- **Owner:** jaimejoseph83
- **Plan:** [`plan.md`](plan.md)
- **Constrained by:** ADR-0001 ([`docs/adr/0001-python-stdlib-json-file-store.md`](../../adr/0001-python-stdlib-json-file-store.md))
- **Brief:** none
- **Discovery:** none
- **Contract:** none
- **Shape:** service

> **Spec contract:** this document defines what "done" means. The implementing
> PR must match this spec, or update it. Verification must be derivable from it.

<!-- **Durable-spec fill.** This template governs work that needs a durable
behavior contract for one delivery slice. Fill Objective, Boundaries, Testing
Strategy, Acceptance Criteria, and Assumptions to the depth the durable work
requires. The sibling plan carries the implementation and verification strategy.
Eligible direct-light work does not create this artifact. -->

<!-- **Present tense, as-built.** Write every body section below as if the
feature already exists and always worked this way — no "will be", no
"previously X, now Y", no deprecation timelines, no version-stamped history.
The body describes the current contract; decision history lives in ADRs and the
changelog. This applies to the spec body only — `plan.md` keeps its own
changelog of how the approach evolved. -->

## Objective

`expense-tracker` gives a single user a `log` command that records one
expense to a local file from the command line. The user runs
`expense-tracker log --amount 42.50 --category groceries --date 2026-08-30`
and gets back a confirmation with the new expense's id; the expense is now
durably recorded and available to later commands (list, edit, delete, report)
that read the same store. An expense may span more than one day (a hotel
stay, a multi-day trip) by giving an end date in addition to the start date;
a description is optional and exists only to help the user recognize the
entry later (e.g. when scanning a list). Success means: valid input always
produces exactly one new, correctly-shaped record and a clear confirmation;
invalid input never touches the store and always explains what was wrong.

## Durable Outputs

| Semantic role | Applicability | Destination | Owner | Expected evidence | Closeout condition |
| --- | --- | --- | --- | --- | --- |
| Current architecture | Applicable — this is the first implemented feature; the golden path now names the exact record schema and module signatures. `docs/architecture/overview.md` is still its unedited seed template and sits in the same living-class role; per its own seed instructions ("delete this file if it would only repeat an existing architecture source") it is deleted rather than filled in, since `reference.md` already covers this single-package repo's structure | [`docs/architecture/reference.md`](../../architecture/reference.md) (already updated: record-shape table, module signatures, permission and error-handling standards); `docs/architecture/overview.md` deleted | implementer | reference.md's "Expense record shape" table and module signatures match the shipped code; `overview.md` no longer exists | `close-work` confirms no drift between reference.md and the implementation; amend in the same PR if the design deviates |
| Decision rationale | Not applicable — the stack decision is already recorded | [`docs/adr/0001-python-stdlib-json-file-store.md`](../../adr/0001-python-stdlib-json-file-store.md) | n/a | n/a | no new ADR needed unless this feature reverses ADR-0001 |
| User-facing documentation | Applicable — a user needs to know the command exists and how to call it. Destination confirmed against `docs/CONVENTIONS.md` § 5c and its `84d79223` migration note: `guides/` lives at the repo root, not under `docs/` | `guides/reference/log-command.md` (new; repo root) | implementer | guide page committed describing flags, defaults, and exit codes | guide's documented flags/behavior match the shipped CLI `--help` output |
| Maintainer / getting-started procedure | Applicable — `README.md` is a one-line placeholder, and `AGENTS.md`'s *Project overview* and *Build and test commands* are still literal `<...>` placeholders this feature is the first to have real facts for | `README.md`, `AGENTS.md` | implementer | README documents install (none — stdlib only, `pytest` for tests) and run, with a worked `log` example; `AGENTS.md`'s placeholders are replaced with the verified `pip install -e .` / `pytest` commands (lint: none configured yet — stated as fact, not invented) | a new contributor can run the worked example as written; `AGENTS.md` has no remaining `<...>` placeholder in the sections this feature touches |
| Current product truth | Applicable — `docs/product/roadmap.md` is still the unedited seed template, and this is the first shipped feature it should reflect | `docs/product/roadmap.md` | implementer | the "Now" section's `<theme>` placeholder is replaced with a real entry linking this spec, and `Last updated` is set | roadmap.md has no remaining `<theme>`/`YYYY-MM-DD` placeholder in the section this feature touches |
| Release history | Not applicable | `docs/product/changelog.md` | n/a | n/a | this repo has no versioned releases yet; revisit when the first release is cut |
| Interface compatibility | Not applicable | n/a | n/a | n/a | the CLI surface is defined by this spec's Acceptance Criteria, not a separate published contract |
| Operations | Not applicable | n/a | n/a | n/a | local CLI, nothing deployed or operated |
| Reusable learning | Not applicable at spec-approval time | n/a | n/a | n/a | handled by `work-loop`'s own learning-capture step, not a separate durable output here |

## Boundaries

The three-tier guard that keeps an implementing agent inside the lines.
*Always do* applies without asking; *Ask first* requires human sign-off
before proceeding; *Never do* is a hard rule, even under time pressure.

### Always do

- Use only the Python standard library at runtime (ADR-0001) — no new
  runtime dependency. `pytest` as a test-only dependency is allowed (see
  `docs/architecture/reference.md`).
- Represent and store money amounts as `decimal.Decimal` internally; persist
  `amount` as the exact validated input string, never a JSON number and
  never renormalized.
- Validate all input before touching the store file; on any invalid input,
  leave the store file byte-for-byte as it was before the command ran.
- Write the store file atomically (write to a temp file in the same
  directory, then `os.replace` into place) so a crash mid-write cannot
  corrupt existing records.
- On POSIX, create the store file with owner-only read/write permissions
  (see `docs/architecture/reference.md`'s Security & data handling
  standard).

### Ask first

- Changing the default store path or its `EXPENSE_TRACKER_FILE` override
  (both fixed by `docs/architecture/reference.md`).
- Adding any third-party **runtime** dependency (test-only dependencies are
  pre-approved; see Always do).
- Changing the on-disk JSON record shape in a way future commands (list,
  edit, delete, report) would need to migrate around.

### Never do

- Introduce a database or alternate storage engine (e.g. SQLite) — ADR-0001
  explicitly defers that until its re-evaluation trigger fires.
- Add a command module, storage module, or package boundary beyond the
  `cli.py` / `store.py` / `models.py` split named in `reference.md`. (The
  packaging console-script `expense-tracker = expense_tracker.cli:main`
  and the `expense_tracker` package's `__init__.py` are the only
  additional files this spec authorizes — they're packaging, not a new
  component.)
- Partially apply an invalid `log` invocation (e.g. write a record with a
  default in place of a bad field) instead of failing closed.

## Testing Strategy

- **Input validation and record construction** (AC1-AC7, AC9, AC17's shape
  as produced by `models.py`): **TDD** — each rule is a compressible
  pure-function invariant in `models.py`.
- **Store read/write** (AC8, AC10, AC11, AC13, AC15, AC16, AC17's on-load
  enforcement, AC18): **TDD** against a temp-directory fixture — a
  compressible invariant on `store.py`.
- **The `log` command end-to-end** (AC12, AC14): this is the *altitude* of
  a whole-journey check (per `work-loop`'s TDD/goal-based/manual-QA modes,
  which classify by altitude, not by "was a human involved") — labeled
  **Visual / manual QA** and exercised by an **integration** test that
  invokes the built CLI entry point against a temp store file (via
  `EXPENSE_TRACKER_FILE`) and asserts on stdout, stderr, exit code, and file
  contents together, since unit coverage of the pieces alone doesn't prove
  the wiring between them.
- **Packaging and documentation** (install, console-script, guide/README
  accuracy — not an AC, but part of this delivery's Durable Outputs):
  **Goal-based check** — `pip install -e .` succeeds and the worked example
  in the docs runs as written.

Stub coverage (see `plan.md`'s per-task `Tests:` subsections, validated by
compiling and running each stub from disposable scratch): **stubbed with a
validated red** — AC1 (both the accept and reject cases) and AC15.
**TDD-mode but not stubbed at PLAN** (prose `Tests:` entries; the edge-case
matrix is built out in EXECUTE) — AC2-AC10, AC13, AC16-AC18. **`no stub
(visual/manual QA)`** — T3 (AC12, AC14). **`no stub (goal-based)`** — T4.

## Acceptance Criteria

- [ ] **AC1 — amount grammar.** `--amount` is accepted only when it is
      exactly a positive number written as one or more digits, optionally
      followed by a decimal point and one or two more digits — e.g. `12`,
      `12.5`, `12.50` — with no sign, no scientific notation, and no
      surrounding whitespace or other characters. Any other `--amount`
      (missing, `0`, `0.00`, negative, non-numeric, `NaN`, `Infinity`, more
      than two fractional digits, a leading `+`/`-`, scientific notation, or
      leading/trailing whitespace) is rejected as invalid input.
- [ ] **AC2 — amount stored exactly.** Given `--amount` is accepted per
      AC1, the new record's `amount` equals the given `--amount` string
      byte-for-byte, with no reformatting or renormalization.
- [ ] **AC3 — record created from valid amount/category/date.** Given
      `--amount` is accepted per AC1, `--category` is non-blank text, and
      `--date` is a valid ISO-8601 (`YYYY-MM-DD`) date, when
      `expense-tracker log` runs, the store file (see AC8 for which file)
      gains exactly one new record with a freshly generated id whose
      `category` and `start_date` equal the given `--category` and
      `--date`.
- [ ] **AC4 — description given.** Given `--description` is provided and
      non-blank after stripping leading/trailing whitespace, the new
      record's `description` equals the given value.
- [ ] **AC5 — description omitted or blank.** Given `--description` is
      omitted, or given but blank (empty or whitespace-only), the new
      record's `description` is `null`.
- [ ] **AC6 — end date defaults to start date.** Given `--end-date` is
      omitted, the new record's `end_date` equals its `start_date`
      (`--date`).
- [ ] **AC7 — end date given.** Given `--end-date` is provided and is a
      valid ISO-8601 date on or after `--date`, the new record's `end_date`
      equals the given `--end-date`.
- [ ] **AC8 — which file.** The command reads and writes the file named by
      the `EXPENSE_TRACKER_FILE` environment variable when it is set to a
      non-empty value, and `~/.expense-tracker/expenses.json` otherwise.
- [ ] **AC9 — invalid input triggers rejection.** Given any of: `--amount`
      is rejected per AC1; `--category` is missing or blank; `--date` is
      missing or not a valid ISO-8601 date; or `--end-date` is provided but
      not a valid ISO-8601 date, or precedes `--date` — `expense-tracker
      log` rejects the invocation, reported per AC12.
- [ ] **AC10 — an unreadable store triggers rejection.** Given the store
      file (AC8) exists but its contents cannot be parsed into the expected
      list of expense records (invalid JSON, a non-list top level, or an
      individual record missing/mismatching the required fields), when
      `expense-tracker log` runs with otherwise-accepted input,
      `expense-tracker log` rejects the invocation, reported per AC12.
- [ ] **AC11 — an unwritable store triggers rejection.** Given the store
      file's parent directory cannot be created, or the store file's path
      cannot be opened for writing, when `expense-tracker log` runs with
      otherwise-accepted input, `expense-tracker log` rejects the
      invocation, reported per AC12.
- [ ] **AC12 — rejection reporting shape.** For every rejection described
      in AC9, AC10, or AC11: the command exits with status `1`, stderr is
      exactly one line beginning `error: `, and stdout is empty.
- [ ] **AC13 — rejection leaves the store untouched.** For every rejection
      described in AC9, AC10, or AC11: the store file's contents (or
      absence, if it did not already exist) are unchanged from immediately
      before the command ran.
- [ ] **AC14 — success reporting.** On success, stdout is exactly the new
      record's generated id followed by a newline, stderr is empty, and the
      command exits with status `0`.
- [ ] **AC15 — store file created on first write.** Given the store file
      does not exist yet, when `expense-tracker log` runs successfully, the
      file and any missing parent directory are created, and the file
      contains exactly the new record.
- [ ] **AC16 — existing records preserved and new record appended last.**
      Given a store file that already contains records, when
      `expense-tracker log` runs successfully, every record present before
      the run is still present afterward — same `id`, `amount`, `category`,
      `start_date`, `end_date`, and `description`, same relative order —
      and the new record is the last element of the array, with no other
      record added or removed.
- [ ] **AC17 — record shape after a successful write.** After any
      successful `expense-tracker log` invocation, every record in the
      store file has exactly the keys `id`, `amount`, `category`,
      `start_date`, `end_date`, `description` — no more, no fewer — with
      `id` a `uuid4` string, `amount`/`category` as given strings,
      `start_date`/`end_date` as `YYYY-MM-DD` strings, and `description` a
      string or `null`, matching `docs/architecture/reference.md`'s
      "Expense record shape" table (the enforced contract; this criterion
      pins conformance to it, not a second copy of it).
- [ ] **AC18 — file permissions.** On a POSIX system, after any successful
      `expense-tracker log` invocation, the store file's permissions grant
      read and write access to its owner only.

## Follow-ons

<!--
Separately scoped work that does not belong to the final accepted AC set. Each
entry needs an owner and a stable work-intake artifact or external evidence
reference. Do not use this section to hide unfinished accepted intent.

- <owner>: <stable artifact or external ref> — <one-sentence scope>
-->

## Assumptions

<!--
Audit trail for the assumption-surfacing checkpoint that ran when this
spec was drafted (see `new-spec` SKILL.md step 3). Each item names how
it was settled. This section is *not* the contract — it's the frame the
contract was written under. The contract lives above (Objective,
Boundaries, Testing Strategy, Acceptance Criteria).

Format: `- <category>: <fact> (source: <path | URL | probe | user
confirmation YYYY-MM-DD>)`

If an assumption later turns out wrong, fix the spec body in the same
PR and add a one-line note here recording what changed and why.
-->

- Technical: runtime is Python 3.11+, standard library only, no new
  dependencies (source: `docs/adr/0001-python-stdlib-json-file-store.md`,
  `docs/architecture/reference.md`)
- Technical: storage is a single local JSON file, default path
  `~/.expense-tracker/expenses.json`, overridable via the
  `EXPENSE_TRACKER_FILE` env var (source: `docs/architecture/reference.md`)
- Technical: amounts use `decimal.Decimal` (stored as JSON strings), dates
  use ISO-8601 `YYYY-MM-DD`, each record gets a `uuid4` id (source:
  `docs/architecture/reference.md`)
- Product: an expense carries a date range (`start_date`, `end_date`); a
  single-day expense sets `end_date` equal to `start_date` (source: user
  confirmation 2026-09-01)
- Product: category is free text — any non-blank string is accepted, with
  no fixed/enum set (source: user confirmation 2026-09-01)
- Process: this is a solo-maintainer project with no prior spec in the
  repo; the user is the sole approver of the spec/plan gates below (source:
  repository has one contributor; no `docs/specs/` precedent exists yet)
