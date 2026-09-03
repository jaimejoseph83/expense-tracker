# Reference architecture

> Golden path for `expense-tracker`. New commands and modules conform to this;
> a deviation needs a recorded reason. See
> [`docs/adr/0001-python-stdlib-json-file-store.md`](../adr/0001-python-stdlib-json-file-store.md)
> for the decision this codifies.

## Constraints

- **Technical constraints.** Python 3.11+, standard library only at
  **runtime** — no third-party runtime dependency (`argparse`, `json`,
  `pathlib`, `decimal`, `datetime`, `uuid`). `pytest` is a **test-only**
  dependency, declared in `pyproject.toml`'s `[project.optional-dependencies]
  test` group, never imported by shipped code. No server, no deployment
  target: this is a local CLI the user runs from a terminal on their own
  machine.
- **Organizational / process constraints.** Single maintainer. Conventional
  Commits. Follow the `work-loop` skill for non-trivial changes.
- **Constraints you cannot change here.** Single-writer only — the JSON store
  is not safe for concurrent processes writing at once. A feature needing
  concurrent access must revisit ADR-0001, not work around it locally.

## Solution strategy

- **Architectural style.** A single-package CLI: an `argparse` entry point
  dispatches to one function per subcommand; each subcommand function reads
  the store, mutates or queries it, writes it back if changed, and prints a
  result. No client/server split, no background process.
- **Key technology decisions.**
  - `argparse` for command/subcommand parsing and `--flag` options — stdlib,
    no new dependency.
  - `json` + `pathlib` for storage: one file, one JSON array of expense
    records, rewritten atomically on each write (write to a temp file in the
    same directory, then `os.replace` into place) so a crash mid-write can't
    corrupt the store.
  - `decimal.Decimal` for all money values — never `float` — to avoid
    floating-point rounding in amounts. Stored in JSON as a string, parsed
    back through `Decimal`.
  - `datetime.date` for expense dates, stored as ISO-8601 (`YYYY-MM-DD`)
    strings.
  - `uuid.uuid4` for each expense record's `id`, so records are stable
    identifiers a later `edit`/`delete` command can target regardless of list
    order.
- **Quality-goal strategy.** Data durability over performance: every mutating
  command does a full read-validate-write rather than optimizing for a large
  file, since a personal expense log stays small (thousands, not millions, of
  rows) for the foreseeable lifetime of this project.

## Building-block view / component catalogue

- **Component stereotypes.**
  - **A command module** owns one CLI subcommand: argument definition,
    input validation, and the user-facing success/error message. It does not
    touch the JSON file directly.
  - **The store** owns all reading and writing of `expenses.json`: loading,
    validating shape, appending/updating/removing records, and the atomic
    write. Nothing else touches the file.
  - **A model** (a `dataclass`) is the in-memory shape of one expense record
    and how it (de)serializes to/from a JSON-compatible dict.
- **Reusable building blocks.**
  - `expense_tracker/store.py` — the store: `default_path()` (resolves
    `~/.expense-tracker/expenses.json`, overridable by a non-empty
    `EXPENSE_TRACKER_FILE` env var), `load(path) -> list[Expense]`,
    `save(path, records)` (atomic write), `append(path, record)`. Raises
    `StoreError` on a store file that doesn't parse, contains a malformed
    record, or can't be read or written (an `OSError`).
  - `expense_tracker/models.py` — the `Expense` dataclass, its
    `to_dict`/`from_dict`, and `Expense.from_input(...)` (validates raw CLI
    strings and raises `ValidationError` on the first invalid field).
  - `expense_tracker/cli.py` — the `argparse` entry point and per-command
    handlers.
- **Composition rules.** `cli.py` depends on `store.py` and `models.py`;
  `store.py` depends on `models.py`; `models.py` depends on neither. A command
  handler never opens the JSON file itself — it always goes through `store.py`.

### Expense record shape

The durable, on-disk shape every command reads and writes — the contract
future commands (list, edit, delete, report) are built against. A record has
**exactly** these keys, no more, no fewer:

| Key | Encoding | Notes |
| --- | --- | --- |
| `id` | string | a freshly generated `uuid4()`, stable across edits |
| `amount` | string | the validated input string, unmodified — a positive number with 0-2 fractional digits (e.g. `"12.5"`), never a JSON number, never renormalized |
| `category` | string | non-blank, free text, as given |
| `start_date` | string | `YYYY-MM-DD` |
| `end_date` | string | `YYYY-MM-DD`, `>= start_date`; equals `start_date` when only one date was given |
| `description` | string or `null` | `null` when not given, or when given but blank (empty/whitespace-only) — never an empty string |

No `created_at` or other bookkeeping field — record order in the JSON array
*is* insertion order, which is sufficient until a feature genuinely needs
something else (at which point that feature's spec adds the field and this
table changes with it).

## Crosscutting concepts / standards

- **Error handling.** Invalid user input (bad amount, bad date, missing
  required field) is caught in the command module and reported as a one-line
  `error: <message>` on stderr with exit code `1` — never a raw traceback,
  and never `argparse`'s own usage-error exit (`2`): required-looking flags
  are parsed as optional and validated by `models.py` so every rejection,
  including a missing flag, goes through the same uniform path. Store-level
  failures (corrupt JSON, a malformed individual record, an unwritable path)
  raise a typed `StoreError` from `store.py` that `cli.py` catches and
  reports the same way — nothing on stdout in either failure class.
- **Observability.** None beyond stdout/stderr — this is a local CLI with no
  running service to instrument.
- **Security & data handling.** The expense file may contain sensitive
  personal financial data. On POSIX, every write creates the temp file via
  `tempfile.NamedTemporaryFile` (mode `0600` by construction) in the store's
  directory, then `os.replace`s it into place — the store file at the
  destination path becomes *that* temp file (rename doesn't alter a file's
  mode), so the store ends up owner-read/write-only after every successful
  write, even one that replaces a pre-existing store file created with
  looser permissions. Never transmitted anywhere; no secrets, no network
  calls. (Windows has no equivalent POSIX-mode concept; this standard
  applies to POSIX only.)
- **Configuration & environments.** The store path defaults to
  `~/.expense-tracker/expenses.json` and is overridable via the
  `EXPENSE_TRACKER_FILE` environment variable when it is set to a
  non-empty value (used by tests to avoid touching the real user file).
- **Testing standards.** Unit tests for `store.py` and `models.py` (pure
  logic, in-memory or temp-dir fixtures). Manual/CLI-level tests for `cli.py`
  invoke the built entry point end-to-end against a temp store file and
  assert on stdout/exit code — see the `work-loop` skill's Visual/manual QA
  mode. No separate verification harness; `pytest` is the one test command.
