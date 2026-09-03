from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date as _Date
from decimal import Decimal, InvalidOperation


class ValidationError(Exception):
    pass


_RECORD_KEYS = frozenset({"id", "amount", "category", "start_date", "end_date", "description"})


@dataclass(frozen=True)
class Expense:
    id: str
    amount: Decimal
    category: str
    start_date: _Date
    end_date: _Date
    description: str | None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "amount": str(self.amount),
            "category": self.category,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Expense:
        if set(data.keys()) != _RECORD_KEYS:
            raise ValueError(f"record has unexpected keys: {set(data.keys()) ^ _RECORD_KEYS}")
        try:
            amount = Decimal(data["amount"])
            start_date = _Date.fromisoformat(data["start_date"])
            end_date = _Date.fromisoformat(data["end_date"])
        except (InvalidOperation, ValueError, TypeError) as exc:
            raise ValueError(str(exc)) from exc
        return cls(
            id=data["id"],
            amount=amount,
            category=data["category"],
            start_date=start_date,
            end_date=end_date,
            description=data["description"],
        )

    @classmethod
    def from_input(
        cls,
        amount: str | None,
        category: str | None,
        date: str | None,
        end_date: str | None,
        description: str | None,
    ) -> Expense:
        if not isinstance(amount, str) or not re.fullmatch(r"\A[0-9]+(\.[0-9]{1,2})?\Z", amount):
            raise ValidationError(
                f"invalid --amount {amount!r}: must be a positive number "
                f"with at most 2 decimal digits (e.g. 12, 12.5, 12.50)"
            )
        parsed_amount = Decimal(amount)
        if parsed_amount <= 0:
            raise ValidationError(f"invalid --amount {amount!r}: must be greater than zero")

        if not category or not category.strip():
            raise ValidationError("--category is required and must not be blank")

        if not date:
            raise ValidationError("--date is required")
        try:
            start = _Date.fromisoformat(date)
        except ValueError:
            raise ValidationError(f"invalid --date {date!r}: must be YYYY-MM-DD")

        if end_date is None:
            end = start
        else:
            try:
                end = _Date.fromisoformat(end_date)
            except ValueError:
                raise ValidationError(f"invalid --end-date {end_date!r}: must be YYYY-MM-DD")
            if end < start:
                raise ValidationError(
                    f"--end-date {end_date!r} is before --date {date!r}"
                )

        desc = description if (description and description.strip()) else None

        return cls(
            id=str(uuid.uuid4()),
            amount=parsed_amount,
            category=category,
            start_date=start,
            end_date=end,
            description=desc,
        )
