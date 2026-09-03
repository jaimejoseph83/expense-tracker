import json
import sys
from pathlib import Path

import pytest

from expense_tracker.cli import main


def _run(args: list[str], store_path: Path) -> tuple[int, str, str]:
    """Run main() with a given store path; return (exit_code, stdout, stderr)."""
    import io
    from contextlib import redirect_stdout, redirect_stderr

    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


@pytest.fixture()
def store_env(tmp_path, monkeypatch):
    path = tmp_path / "expenses.json"
    monkeypatch.setenv("EXPENSE_TRACKER_FILE", str(path))
    return path


# AC3, AC4, AC5, AC6, AC7, AC14, AC15, AC17 — valid args: success path
def test_valid_log_creates_record(store_env):
    code, out, err = _run(
        ["log", "--amount", "42.50", "--category", "groceries",
         "--date", "2026-08-30", "--description", "weekly shop"],
        store_env,
    )
    assert code == 0
    assert err == ""
    record_id = out.strip()
    assert record_id  # non-empty

    data = json.loads(store_env.read_text())
    assert len(data) == 1
    rec = data[0]
    assert set(rec.keys()) == {"id", "amount", "category", "start_date", "end_date", "description"}
    assert rec["id"] == record_id
    assert rec["amount"] == "42.50"
    assert rec["category"] == "groceries"
    assert rec["start_date"] == "2026-08-30"
    assert rec["end_date"] == "2026-08-30"  # AC6: defaults to start
    assert rec["description"] == "weekly shop"


def test_end_date_given_is_stored(store_env):
    code, out, err = _run(
        ["log", "--amount", "200", "--category", "hotel",
         "--date", "2026-09-01", "--end-date", "2026-09-03"],
        store_env,
    )
    assert code == 0
    data = json.loads(store_env.read_text())
    assert data[0]["end_date"] == "2026-09-03"


def test_description_omitted_stored_as_null(store_env):
    code, out, err = _run(
        ["log", "--amount", "5", "--category", "tea", "--date", "2026-09-01"],
        store_env,
    )
    assert code == 0
    data = json.loads(store_env.read_text())
    assert data[0]["description"] is None


# AC15 — store file is created on first write
def test_store_file_created_on_first_write(store_env):
    assert not store_env.exists()
    code, _, _ = _run(
        ["log", "--amount", "1", "--category", "a", "--date", "2026-09-01"],
        store_env,
    )
    assert code == 0
    assert store_env.exists()


# AC16 — existing records preserved; new record appended last
def test_second_write_appends_and_preserves_existing(store_env):
    _run(["log", "--amount", "1.00", "--category", "a", "--date", "2026-09-01"], store_env)
    code, out2, _ = _run(
        ["log", "--amount", "2.00", "--category", "b", "--date", "2026-09-02"],
        store_env,
    )
    assert code == 0
    data = json.loads(store_env.read_text())
    assert len(data) == 2
    assert data[0]["category"] == "a"
    assert data[1]["category"] == "b"
    assert data[1]["id"] == out2.strip()


# AC1 + AC9 + AC12 + AC13 — rejected input classes
@pytest.mark.parametrize("args,desc", [
    (["log", "--category", "food", "--date", "2026-09-01"], "missing --amount"),
    (["log", "--amount", "0", "--category", "food", "--date", "2026-09-01"], "zero amount"),
    (["log", "--amount", "abc", "--category", "food", "--date", "2026-09-01"], "non-numeric amount"),
    (["log", "--amount", "12.555", "--category", "food", "--date", "2026-09-01"], "too many decimals"),
    (["log", "--amount", "10", "--date", "2026-09-01"], "missing --category"),
    (["log", "--amount", "10", "--category", "  ", "--date", "2026-09-01"], "blank category"),
    (["log", "--amount", "10", "--category", "food"], "missing --date"),
    (["log", "--amount", "10", "--category", "food", "--date", "not-a-date"], "bad date"),
    (["log", "--amount", "10", "--category", "food", "--date", "2026-09-03",
      "--end-date", "2026-09-01"], "end-date before start"),
])
def test_rejected_input_exits_1_error_line_no_stdout(args, desc, store_env):
    code, out, err = _run(args, store_env)
    assert code == 1, f"expected exit 1 for {desc}"
    assert out == "", f"expected empty stdout for {desc}"
    assert err.startswith("error: "), f"expected 'error: ' prefix for {desc}"
    assert err.count("\n") == 1, f"expected exactly one stderr line for {desc}"


def test_rejected_input_leaves_store_absent(store_env):
    _run(["log", "--amount", "bad", "--category", "food", "--date", "2026-09-01"], store_env)
    assert not store_env.exists()


def test_rejected_input_leaves_existing_store_unchanged(store_env):
    _run(["log", "--amount", "5", "--category", "tea", "--date", "2026-09-01"], store_env)
    before = store_env.read_bytes()
    _run(["log", "--amount", "bad", "--category", "food", "--date", "2026-09-01"], store_env)
    assert store_env.read_bytes() == before


# AC10 + AC12 + AC13 — corrupt store triggers rejection without touching file
def test_corrupt_store_rejected_unchanged(store_env):
    store_env.write_text("{not valid json}")
    before = store_env.read_bytes()
    code, out, err = _run(
        ["log", "--amount", "5", "--category", "food", "--date", "2026-09-01"],
        store_env,
    )
    assert code == 1
    assert out == ""
    assert err.startswith("error: ")
    assert store_env.read_bytes() == before


# AC8 — EXPENSE_TRACKER_FILE env var controls which file is used
def test_expense_tracker_file_env_var(tmp_path, monkeypatch):
    custom = tmp_path / "custom.json"
    monkeypatch.setenv("EXPENSE_TRACKER_FILE", str(custom))
    code, _, _ = _run(
        ["log", "--amount", "1", "--category", "a", "--date", "2026-09-01"],
        custom,
    )
    assert code == 0
    assert custom.exists()


# AC18 — POSIX: successful write leaves file with 0600 permissions
@pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
def test_posix_permissions_after_write(store_env):
    _run(["log", "--amount", "5", "--category", "food", "--date", "2026-09-01"], store_env)
    mode = store_env.stat().st_mode & 0o777
    assert mode == 0o600
