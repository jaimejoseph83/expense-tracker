from __future__ import annotations

import argparse
import sys

from expense_tracker import store
from expense_tracker.models import Expense, ValidationError
from expense_tracker.store import StoreError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="expense-tracker",
        description="Track personal expenses from the command line.",
    )
    sub = parser.add_subparsers(dest="command")

    log_p = sub.add_parser("log", help="Record a new expense.")
    log_p.add_argument("--amount")
    log_p.add_argument("--category")
    log_p.add_argument("--date")
    log_p.add_argument("--end-date")
    log_p.add_argument("--description")

    return parser


def run_log(args: argparse.Namespace) -> int:
    path = store.default_path()
    try:
        expense = Expense.from_input(
            amount=args.amount,
            category=args.category,
            date=args.date,
            end_date=args.end_date,
            description=args.description,
        )
        store.append(path, expense)
    except (ValidationError, StoreError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(expense.id)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "log":
        return run_log(args)
    parser.print_help(sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
