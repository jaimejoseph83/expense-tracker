# 0001. Use Python 3 with the standard library and a local JSON file store

- **Status:** Accepted
- **Date:** 2026-09-01
- **Re-evaluate when:** expenses need concurrent multi-writer access, complex
  queries/aggregation across a large history, or the JSON file's size causes
  noticeable read/write latency.

## Context

`expense-tracker` is a brand-new repo with no prior stack decision. The first
feature is a CLI command to log an expense (amount, category, date(s),
optional description). The product is a single-user personal tool: one person
running commands from a terminal, no server, no concurrent writers, no
authentication or multi-tenant concerns.

## Decision

Build the CLI in **Python 3**, using only the **standard library**:
`argparse` for command parsing, `json` + `pathlib` for storage, `decimal` for
money values, and `datetime`/`date` for date handling. Store expenses as a
JSON array of records in a single local file (default
`~/.expense-tracker/expenses.json`, overridable via a flag/env var for
testing).

## Alternatives considered

- **Node.js/TypeScript.** Native JSON handling, but no built-in CLI
  arg-parsing library — would require a new dependency (e.g. `commander`) for
  a capability Python's stdlib already covers, plus a runtime install step
  this project doesn't otherwise need.
- **SQLite instead of a JSON file.** Better suited to concurrent access and
  complex queries, but overkill for a single-user, append-mostly log at this
  size. A JSON file is human-readable, greppable, and diffable, which matters
  for a personal finance log someone may want to inspect or back up directly.
  Revisit via a follow-up ADR if query complexity or file size grows.
- **A third-party CLI framework (Click/Typer) instead of `argparse`.** Nicer
  ergonomics, but a new dependency for a small number of subcommands that
  `argparse` handles fine.

## Consequences

- Zero new dependencies — `pip install` is not required to run the tool.
- The JSON file is the durable schema every future command (list, edit,
  delete, report) reads and writes; its shape is recorded in
  [`docs/architecture/reference.md`](../architecture/reference.md) and changed
  deliberately.
- Concurrent writes are not safe. Acceptable for a single-user CLI; would need
  revisiting (e.g. file locking or a real database) if that assumption changes.
- Money is stored and parsed via `decimal.Decimal`, never `float`, to avoid
  floating-point rounding errors in amounts.
