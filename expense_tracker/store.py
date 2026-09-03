from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from expense_tracker.models import Expense


class StoreError(Exception):
    pass


def default_path() -> Path:
    env = os.environ.get("EXPENSE_TRACKER_FILE", "")
    if env:
        return Path(env)
    return Path.home() / ".expense-tracker" / "expenses.json"


def load(path: Path) -> list[Expense]:
    if not path.exists():
        return []
    try:
        with path.open() as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        raise StoreError(f"could not read store {path}: {exc}") from exc
    if not isinstance(data, list):
        raise StoreError(f"store {path} is not a JSON array")
    records: list[Expense] = []
    for i, item in enumerate(data):
        try:
            records.append(Expense.from_dict(item))
        except (ValueError, KeyError, TypeError) as exc:
            raise StoreError(f"store {path} record {i} is malformed: {exc}") from exc
    return records


def save(path: Path, records: list[Expense]) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=path.parent, delete=False, suffix=".tmp"
        ) as tmp:
            tmp_name = tmp.name
            json.dump([r.to_dict() for r in records], tmp)
        os.replace(tmp_name, path)
    except OSError as exc:
        raise StoreError(f"could not write store {path}: {exc}") from exc


def append(path: Path, record: Expense) -> None:
    existing = load(path)
    save(path, existing + [record])
