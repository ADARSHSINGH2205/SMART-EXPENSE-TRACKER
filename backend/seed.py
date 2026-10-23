"""Friendly demo data used on a brand-new local PayArc database."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import Budget, Category, Expense, Goal, RecurringBill
from .services import safe_next_due_date


CATEGORY_DATA = [
    ("Food & Dining", "food-dining", "expense", "#F97316", "utensils"),
    ("Transport", "transport", "expense", "#3B82F6", "car"),
    ("Housing", "housing", "expense", "#8B5CF6", "home"),
    ("Shopping", "shopping", "expense", "#EC4899", "shopping-bag"),
    ("Health & Wellness", "health-wellness", "expense", "#10B981", "heart-pulse"),
    ("Entertainment", "entertainment", "expense", "#F59E0B", "clapperboard"),
    ("Education", "education", "expense", "#06B6D4", "graduation-cap"),
    ("Utilities", "utilities", "expense", "#64748B", "zap"),
    ("Travel", "travel", "expense", "#14B8A6", "plane"),
    ("Savings", "savings", "expense", "#22C55E", "piggy-bank"),
    ("Salary", "salary", "income", "#16A34A", "banknote"),
    ("Freelance", "freelance", "income", "#0EA5E9", "briefcase-business"),
]


def seed_database(db: Session) -> None:
    """Insert data exactly once, keeping existing user data untouched."""
    existing_categories = {item.slug: item for item in db.scalars(select(Category))}
    for name, slug, kind, color, icon in CATEGORY_DATA:
        if slug not in existing_categories:
            db.add(Category(name=name, slug=slug, kind=kind, color=color, icon=icon, is_system=True))
    db.flush()
    categories = {item.slug: item for item in db.scalars(select(Category))}

    if not db.scalar(select(func.count()).select_from(Expense)):
        today = date.today()
        first_of_month = today.replace(day=1)
        seed_expenses = [
            ("Monthly salary", "Acme Digital", 85000, first_of_month, "income", "salary", "Bank transfer", "HDFC Salary", "visible"),
            ("Apartment rent", "Urban Nest", 22000, first_of_month + timedelta(days=1), "expense", "housing", "UPI", "HDFC Salary", "private"),
            ("Weekly groceries", "Fresh Basket", 2180, today - timedelta(days=1), "expense", "food-dining", "Credit card", "ICICI Coral", "private"),
            ("Coffee catch-up", "Bean Theory", 320, today - timedelta(days=2), "expense", "food-dining", "UPI", "HDFC Salary", "shared"),
            ("Metro recharge", "Delhi Metro", 600, today - timedelta(days=4), "expense", "transport", "UPI", "HDFC Salary", "private"),
            ("Streaming subscription", "CineVerse", 499, today - timedelta(days=6), "expense", "entertainment", "Credit card", "ICICI Coral", "private"),
            ("Gym membership", "Pulse Studio", 1499, today - timedelta(days=9), "expense", "health-wellness", "UPI", "HDFC Salary", "private"),
            ("Online course", "Design Lab", 1299, today - timedelta(days=12), "expense", "education", "Credit card", "ICICI Coral", "private"),
            ("Electricity bill", "City Power", 1840, today - timedelta(days=15), "expense", "utilities", "UPI", "HDFC Salary", "private"),
            ("Weekend fund", "Goal contribution", 4000, today - timedelta(days=16), "expense", "savings", "Bank transfer", "HDFC Salary", "private"),
        ]
        for title, merchant, amount, happened_on, direction, category_slug, method, account, privacy in seed_expenses:
            db.add(
                Expense(
                    title=title,
                    merchant=merchant,
                    amount=amount,
                    date=happened_on,
                    direction=direction,
                    category_id=categories[category_slug].id,
                    payment_method=method,
                    account=account,
                    privacy=privacy,
                    expense_scope="personal",
                    tags="demo,personal",
                    is_recurring=title in {"Apartment rent", "Streaming subscription", "Gym membership"},
                    recurrence="monthly" if title in {"Apartment rent", "Streaming subscription", "Gym membership"} else None,
                )
            )

    if not db.scalar(select(func.count()).select_from(Budget)):
        today = date.today()
        start = today.replace(day=1)
        db.add_all(
            [
                Budget(name="Food freedom", limit_amount=8000, category_id=categories["food-dining"].id, start_date=start, color="#F97316"),
                Budget(name="Getting around", limit_amount=3500, category_id=categories["transport"].id, start_date=start, color="#3B82F6"),
                Budget(name="Fun money", limit_amount=3000, category_id=categories["entertainment"].id, start_date=start, color="#F59E0B"),
                Budget(name="Whole month", limit_amount=48000, start_date=start, color="#8B5CF6"),
            ]
        )

    if not db.scalar(select(func.count()).select_from(Goal)):
        today = date.today()
        db.add_all(
            [
                Goal(name="Japan adventure", target_amount=180000, current_amount=62000, target_date=today + timedelta(days=190), icon="plane", color="#14B8A6", priority="high"),
                Goal(name="Emergency cushion", target_amount=150000, current_amount=98000, target_date=today + timedelta(days=100), icon="shield-check", color="#22C55E", priority="high"),
                Goal(name="New work setup", target_amount=70000, current_amount=21500, target_date=today + timedelta(days=280), icon="laptop", color="#8B5CF6", priority="medium"),
            ]
        )

    if not db.scalar(select(func.count()).select_from(RecurringBill)):
        today = date.today()
        db.add_all(
            [
                RecurringBill(name="Apartment rent", amount=22000, due_day=1, next_due_date=safe_next_due_date(today, 1), autopay=True, account="HDFC Salary", category_id=categories["housing"].id),
                RecurringBill(name="CineVerse", amount=499, due_day=min(today.day + 2, 28), next_due_date=safe_next_due_date(today, min(today.day + 2, 28)), autopay=True, account="ICICI Coral", category_id=categories["entertainment"].id),
                RecurringBill(name="Mobile plan", amount=699, due_day=min(today.day + 6, 28), next_due_date=safe_next_due_date(today, min(today.day + 6, 28)), autopay=False, account="HDFC Salary", category_id=categories["utilities"].id),
            ]
        )
    db.commit()

