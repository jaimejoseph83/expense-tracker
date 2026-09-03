from decimal import Decimal
from datetime import date

import pytest

from expense_tracker.models import Expense, ValidationError


# AC1 — accepted forms parse correctly and store string unchanged
def test_accepts_valid_amount_forms():
    for raw in ("12", "12.5", "12.50"):
        expense = Expense.from_input(
            amount=raw, category="coffee", date="2026-09-01",
            end_date=None, description=None,
        )
        assert expense.amount == Decimal(raw)
        assert expense.to_dict()["amount"] == raw


# AC1 — rejected forms raise ValidationError
REJECTED_AMOUNTS = [
    None, "0", "0.00", "-5", "abc", "NaN", "Infinity",
    "12.555", "+5", "1e5", " 12", "12 ", "12\n",
]


@pytest.mark.parametrize("raw", REJECTED_AMOUNTS)
def test_rejects_invalid_amount_forms(raw):
    with pytest.raises(ValidationError):
        Expense.from_input(
            amount=raw, category="coffee", date="2026-09-01",
            end_date=None, description=None,
        )


# AC2 — amount stored byte-for-byte as given
def test_amount_stored_exactly_as_given():
    for raw in ("12", "12.5", "12.50", "1", "99.99"):
        expense = Expense.from_input(
            amount=raw, category="food", date="2026-09-01",
            end_date=None, description=None,
        )
        assert expense.to_dict()["amount"] == raw


# AC3 — record created with correct category and start_date
def test_builds_record_from_valid_amount_category_date():
    expense = Expense.from_input(
        amount="42.50", category="groceries", date="2026-08-30",
        end_date=None, description=None,
    )
    d = expense.to_dict()
    assert d["category"] == "groceries"
    assert d["start_date"] == "2026-08-30"
    assert d["id"]


# AC4 — description given and non-blank is kept
def test_description_given_is_kept():
    expense = Expense.from_input(
        amount="10", category="food", date="2026-09-01",
        end_date=None, description="lunch at the cafe",
    )
    assert expense.description == "lunch at the cafe"
    assert expense.to_dict()["description"] == "lunch at the cafe"


# AC5 — description omitted or blank becomes null
@pytest.mark.parametrize("desc", [None, "", "   ", "\t"])
def test_description_omitted_or_blank_is_null(desc):
    expense = Expense.from_input(
        amount="10", category="food", date="2026-09-01",
        end_date=None, description=desc,
    )
    assert expense.description is None
    assert expense.to_dict()["description"] is None


# AC6 — end_date defaults to start_date when omitted
def test_end_date_defaults_to_start_date():
    expense = Expense.from_input(
        amount="10", category="food", date="2026-09-01",
        end_date=None, description=None,
    )
    assert expense.start_date == expense.end_date
    d = expense.to_dict()
    assert d["start_date"] == d["end_date"] == "2026-09-01"


# AC7 — end_date given on or after start is accepted
def test_end_date_given_on_or_after_start():
    e1 = Expense.from_input(
        amount="10", category="hotel", date="2026-09-01",
        end_date="2026-09-01", description=None,
    )
    assert e1.end_date == date(2026, 9, 1)

    e2 = Expense.from_input(
        amount="200", category="hotel", date="2026-09-01",
        end_date="2026-09-03", description=None,
    )
    assert e2.end_date == date(2026, 9, 3)


# AC7 + AC9 — end_date before start is rejected
def test_end_date_before_start_is_rejected():
    with pytest.raises(ValidationError):
        Expense.from_input(
            amount="10", category="hotel", date="2026-09-03",
            end_date="2026-09-01", description=None,
        )


# AC9 — missing or blank category is rejected
@pytest.mark.parametrize("cat", [None, "", "   "])
def test_missing_or_blank_category_is_rejected(cat):
    with pytest.raises(ValidationError):
        Expense.from_input(
            amount="10", category=cat, date="2026-09-01",
            end_date=None, description=None,
        )


# AC9 — missing or invalid date is rejected
@pytest.mark.parametrize("d", [None, "", "not-a-date", "2026-13-01", "01-09-2026"])
def test_missing_or_invalid_date_is_rejected(d):
    with pytest.raises(ValidationError):
        Expense.from_input(
            amount="10", category="food", date=d,
            end_date=None, description=None,
        )


# AC17 — record has exactly 6 keys with correct types; round-trips through from_dict
def test_to_dict_from_dict_round_trip_and_key_set():
    expense = Expense.from_input(
        amount="42.50", category="groceries", date="2026-08-30",
        end_date="2026-09-02", description="weekly shop",
    )
    d = expense.to_dict()

    assert set(d.keys()) == {"id", "amount", "category", "start_date", "end_date", "description"}
    assert isinstance(d["id"], str)
    assert isinstance(d["amount"], str)
    assert isinstance(d["category"], str)
    assert isinstance(d["start_date"], str)
    assert isinstance(d["end_date"], str)
    assert isinstance(d["description"], (str, type(None)))

    restored = Expense.from_dict(d)
    assert restored == expense
