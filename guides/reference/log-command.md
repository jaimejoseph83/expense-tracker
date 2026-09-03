# `expense-tracker log`

Record a new expense to the local JSON store.

## Synopsis

```
expense-tracker log --amount AMOUNT --category CATEGORY --date DATE
                    [--end-date END_DATE] [--description DESCRIPTION]
```

## Options

| Flag | Required | Description |
| --- | --- | --- |
| `--amount` | yes | Amount to record. A positive number with at most 2 decimal digits — e.g. `12`, `12.5`, `12.50`. No sign, no scientific notation, no surrounding whitespace. |
| `--category` | yes | Free-text category label (non-blank). |
| `--date` | yes | Expense start date in `YYYY-MM-DD` format. |
| `--end-date` | no | Expense end date in `YYYY-MM-DD` format, on or after `--date`. Defaults to `--date` (single-day expense). |
| `--description` | no | Free-text note to help identify the entry later. Blank or whitespace-only is treated the same as omitted (stored as `null`). |

## Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Success — expense recorded. |
| `1` | Error — invalid input or store failure. One `error: …` line on stderr; store file is unchanged. |

## Output

On success, stdout is the new expense's UUID followed by a newline. Stderr is empty.

```
expense-tracker log --amount 42.50 --category groceries --date 2026-08-30
b3f12a34-56cd-78ef-9012-abcdef012345
```

On error, stdout is empty and stderr has one line:

```
expense-tracker log --amount abc --category food --date 2026-09-01
error: invalid --amount 'abc': must be a positive number with at most 2 decimal digits (e.g. 12, 12.5, 12.50)
```

## Store file

Expenses are written to `~/.expense-tracker/expenses.json` by default. Override with the `EXPENSE_TRACKER_FILE` environment variable (non-empty value):

```bash
EXPENSE_TRACKER_FILE=/tmp/test.json expense-tracker log --amount 5 --category coffee --date 2026-09-01
```

The file is a JSON array of records. Each record has exactly these keys:

| Key | Type | Notes |
| --- | --- | --- |
| `id` | string | UUID4, stable identifier for later edit/delete |
| `amount` | string | As given — never reformatted |
| `category` | string | As given |
| `start_date` | string | `YYYY-MM-DD` |
| `end_date` | string | `YYYY-MM-DD`, equals `start_date` when `--end-date` was omitted |
| `description` | string or `null` | `null` when omitted or blank |

On POSIX, the file is written with owner-only permissions (`0600`).
