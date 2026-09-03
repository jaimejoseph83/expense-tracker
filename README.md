# expense-tracker

A personal command-line expense logger. Records expenses — amount, category, date range, optional description — to a local JSON file.

## Install

Python 3.11+ required. No runtime dependencies.

```bash
# Clone and install (editable):
pip install -e .

# To run tests, include the test dependency:
pip install -e ".[test]"
```

## Usage

```bash
expense-tracker log --amount 42.50 --category groceries --date 2026-08-30
# → b3f12a34-56cd-78ef-9012-abcdef012345
```

| Flag | Required | Description |
| --- | --- | --- |
| `--amount` | yes | Positive number, at most 2 decimal digits (e.g. `12`, `12.5`, `12.50`) |
| `--category` | yes | Free-text label |
| `--date` | yes | Start date, `YYYY-MM-DD` |
| `--end-date` | no | End date, `YYYY-MM-DD` (defaults to `--date`) |
| `--description` | no | Free-text note (blank → stored as null) |

Exit `0` on success (new record's id on stdout). Exit `1` on any error (`error: …` on stderr, store file unchanged).

See [guides/reference/log-command.md](guides/reference/log-command.md) for full flag reference.

## Store file

Expenses are stored at `~/.expense-tracker/expenses.json` (override with `EXPENSE_TRACKER_FILE`).

## Run tests

```bash
pytest
```

No linter is configured yet.
