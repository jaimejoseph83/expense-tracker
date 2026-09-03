import json
import os
import stat
import sys
from pathlib import Path

import pytest

from expense_tracker.models import Expense
from expense_tracker.store import StoreError, append, default_path, load, save


def _make_expense(**kwargs):
    defaults = dict(
        amount="12.50", category="coffee", date="2026-09-01",
        end_date=None, description=None,
    )
    defaults.update(kwargs)
    return Expense.from_input(**defaults)


# AC8 — default path and EXPENSE_TRACKER_FILE override
def test_default_path_env_override(monkeypatch, tmp_path):
    monkeypatch.delenv("EXPENSE_TRACKER_FILE", raising=False)
    assert default_path() == Path.home() / ".expense-tracker" / "expenses.json"

    target = tmp_path / "custom.json"
    monkeypatch.setenv("EXPENSE_TRACKER_FILE", str(target))
    assert default_path() == target


# AC15 — save() creates missing file and parent directory
def test_save_creates_missing_parent_dir(tmp_path):
    target = tmp_path / "nested" / "expenses.json"
    save(target, [])
    assert target.exists()
    assert json.loads(target.read_text()) == []


# AC16 — existing records preserved in order; new record appended last
def test_save_preserves_existing_and_appends_last(tmp_path):
    target = tmp_path / "expenses.json"
    e1 = _make_expense(amount="1.00", category="a")
    e2 = _make_expense(amount="2.00", category="b")
    save(target, [e1])
    save(target, [e1, e2])
    loaded = load(target)
    assert len(loaded) == 2
    assert loaded[0] == e1
    assert loaded[1] == e2


# AC18 — POSIX: save sets owner-only permissions
@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
def test_save_sets_owner_only_permissions(tmp_path):
    target = tmp_path / "expenses.json"
    save(target, [])
    mode = target.stat().st_mode & 0o777
    assert mode == 0o600


# AC15 — load() on a missing path returns empty list (precondition for first write)
def test_load_missing_path_returns_empty_list(tmp_path):
    result = load(tmp_path / "nonexistent.json")
    assert result == []


# AC10 — unparseable JSON or non-list top level raises StoreError
@pytest.mark.parametrize("content", ["{bad json", '{"not": "a list"}', "null", "42"])
def test_load_raises_store_error_on_unparseable_json(tmp_path, content):
    target = tmp_path / "expenses.json"
    target.write_text(content)
    with pytest.raises(StoreError):
        load(target)


# AC10 + AC17 — malformed record raises StoreError (missing key, extra key, bad date)
@pytest.mark.parametrize("record", [
    {"id": "x", "amount": "1.00", "category": "a", "start_date": "2026-09-01"},  # missing keys
    {"id": "x", "amount": "1.00", "category": "a", "start_date": "2026-09-01",
     "end_date": "2026-09-01", "description": None, "extra": "nope"},             # extra key
    {"id": "x", "amount": "1.00", "category": "a", "start_date": "not-a-date",
     "end_date": "2026-09-01", "description": None},                               # bad date
])
def test_load_raises_store_error_on_malformed_record(tmp_path, record):
    target = tmp_path / "expenses.json"
    target.write_text(json.dumps([record]))
    with pytest.raises(StoreError):
        load(target)


# AC11 — unwritable path raises StoreError
def test_save_raises_store_error_on_unwritable_path(tmp_path):
    locked = tmp_path / "locked"
    locked.mkdir()
    locked.chmod(0o000)
    try:
        with pytest.raises(StoreError):
            save(locked / "expenses.json", [])
    finally:
        locked.chmod(0o755)  # restore so pytest can clean up


# AC3 + AC16 — append loads existing, adds new record last
def test_append_loads_adds_saves_without_losing_existing(tmp_path):
    target = tmp_path / "expenses.json"
    e1 = _make_expense(amount="5.00", category="tea")
    e2 = _make_expense(amount="10.00", category="coffee")
    append(target, e1)
    append(target, e2)
    result = load(target)
    assert len(result) == 2
    assert result[0] == e1
    assert result[1] == e2
