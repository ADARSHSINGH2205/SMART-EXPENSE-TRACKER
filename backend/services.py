"""Shared calculations and API serialization helpers."""

from __future__ import annotations

import calendar
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Budget, Expense, Goal, RecurringBill


def month_bounds(reference: date | None = None) -> tuple[date, date]:
    reference = reference or date.today()
    start = reference.replace(day=1)
    if reference.month == 12:
        end = date(reference.year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(reference.year, reference.month + 1, 1) - timedelta(days=1)
    return start, end


def shift_month(reference: date, months: int) -> date:
    """Return the first date in a month moved by a signed number of months."""
    absolute_month = reference.year * 12 + (reference.month - 1) + months
    year, month_zero_based = divmod(absolute_month, 12)
    return date(year, month_zero_based + 1, 1)


def budget_bounds(budget: Budget, reference: date | None = None) -> tuple[date, date]:
    """Find the active evaluation window for a budget."""
    reference = reference or date.today()
    if budget.period == "weekly":
        start = reference - timedelta(days=reference.weekday())
        end = start + timedelta(days=6)
    elif budget.period == "quarterly":
        quarter_month = ((reference.month - 1) // 3) * 3 + 1
        start = date(reference.year, quarter_month, 1)
        if quarter_month == 10:
            end = date(reference.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(reference.year, quarter_month + 3, 1) - timedelta(days=1)
    elif budget.period == "yearly":
        start = date(reference.year, 1, 1)
        end = date(reference.year, 12, 31)
    elif budget.period == "custom" and budget.end_date:
        start = budget.start_date
        end = budget.end_date
    else:
        start, end = month_bounds(reference)

    # Do not include expenses before an explicitly selected budget start date.
    start = max(start, budget.start_date)
    if budget.end_date:
        end = min(end, budget.end_date)
    return start, end


def budget_spend(db: Session, budget: Budget, reference: date | None = None) -> float:
    start, end = budget_bounds(budget, reference)
    if end < start:
        return 0.0
    statement = select(Expense).where(
        Expense.direction == "expense",
        Expense.status != "void",
        Expense.date >= start,
        Expense.date <= end,
    )
    if budget.category_id is not None:
        statement = statement.where(Expense.category_id == budget.category_id)
    return round(sum(item.amount for item in db.scalars(statement)), 2)


def serialize_category(category) -> dict | None:
    if category is None:
        return None
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "kind": category.kind,
        "color": category.color,
        "icon": category.icon,
        "is_system": category.is_system,
        "created_at": category.created_at.isoformat(),
        "updated_at": category.updated_at.isoformat(),
    }


def serialize_expense(expense: Expense) -> dict:
    category = serialize_category(expense.category)
    raw_tags = expense.tags or ""
    return {
        "id": expense.id,
        "title": expense.title,
        "merchant": expense.merchant,
        "description": expense.description,
        "amount": round(expense.amount, 2),
        "currency": expense.currency,
        "date": expense.date.isoformat(),
        "direction": expense.direction,
        # Compatibility with UI clients that use type instead of direction.
        "type": expense.direction,
        "status": expense.status,
        "payment_method": expense.payment_method,
        "account": expense.account,
        "expense_scope": expense.expense_scope,
        "scope": expense.expense_scope,
        "privacy": expense.privacy,
        "split_with": expense.split_with,
        "notes": expense.notes,
        "tags": [tag.strip() for tag in raw_tags.split(",") if tag.strip()],
        "receipt_url": expense.receipt_url,
        "is_recurring": expense.is_recurring,
        "recurrence": expense.recurrence,
        "category_id": expense.category_id,
        "category": category,
        "category_name": category["name"] if category else "Uncategorized",
        "category_color": category["color"] if category else "#94A3B8",
        "category_icon": category["icon"] if category else "circle",
        "created_at": expense.created_at.isoformat(),
        "updated_at": expense.updated_at.isoformat(),
    }


def serialize_budget(db: Session, budget: Budget, reference: date | None = None) -> dict:
    spent = budget_spend(db, budget, reference)
    percent = round((spent / budget.limit_amount) * 100, 1) if budget.limit_amount else 0
    if percent >= 100:
        health = "over_budget"
    elif percent >= budget.alert_percentage:
        health = "needs_attention"
    else:
        health = "on_track"
    return {
        "id": budget.id,
        "name": budget.name,
        "limit_amount": round(budget.limit_amount, 2),
        "limit": round(budget.limit_amount, 2),
        "currency": budget.currency,
        "period": budget.period,
        "start_date": budget.start_date.isoformat(),
        "end_date": budget.end_date.isoformat() if budget.end_date else None,
        "alert_percentage": budget.alert_percentage,
        "color": budget.color,
        "category_id": budget.category_id,
        "category": serialize_category(budget.category),
        "spent_amount": spent,
        "spent": spent,
        "remaining_amount": round(budget.limit_amount - spent, 2),
        "remaining": round(budget.limit_amount - spent, 2),
        "percent_used": percent,
        "progress": min(percent, 100),
        "health": health,
        "created_at": budget.created_at.isoformat(),
        "updated_at": budget.updated_at.isoformat(),
    }


def serialize_goal(goal: Goal, reference: date | None = None) -> dict:
    reference = reference or date.today()
    progress = round((goal.current_amount / goal.target_amount) * 100, 1) if goal.target_amount else 0
    days_remaining = (goal.target_date - reference).days if goal.target_date else None
    return {
        "id": goal.id,
        "name": goal.name,
        "target_amount": round(goal.target_amount, 2),
        "target": round(goal.target_amount, 2),
        "current_amount": round(goal.current_amount, 2),
        "saved": round(goal.current_amount, 2),
        "currency": goal.currency,
        "target_date": goal.target_date.isoformat() if goal.target_date else None,
        "icon": goal.icon,
        "color": goal.color,
        "priority": goal.priority,
        "is_archived": goal.is_archived,
        "notes": goal.notes,
        "remaining_amount": round(max(goal.target_amount - goal.current_amount, 0), 2),
        "remaining": round(max(goal.target_amount - goal.current_amount, 0), 2),
        "progress_percentage": progress,
        "progress": min(progress, 100),
        "days_remaining": days_remaining,
        "created_at": goal.created_at.isoformat(),
        "updated_at": goal.updated_at.isoformat(),
    }


def serialize_bill(bill: RecurringBill, reference: date | None = None) -> dict:
    reference = reference or date.today()
    days_until_due = (bill.next_due_date - reference).days if bill.next_due_date else None
    return {
        "id": bill.id,
        "name": bill.name,
        "amount": round(bill.amount, 2),
        "currency": bill.currency,
        "frequency": bill.frequency,
        "due_day": bill.due_day,
        "next_due_date": bill.next_due_date.isoformat() if bill.next_due_date else None,
        "autopay": bill.autopay,
        "active": bill.active,
        "account": bill.account,
        "notes": bill.notes,
        "category_id": bill.category_id,
        "category": serialize_category(bill.category),
        "days_until_due": days_until_due,
        "created_at": bill.created_at.isoformat(),
        "updated_at": bill.updated_at.isoformat(),
    }


def safe_next_due_date(reference: date, due_day: int | None) -> date | None:
    """Return the next valid calendar date for a recurring bill due-day."""
    if due_day is None:
        return None
    day = min(due_day, calendar.monthrange(reference.year, reference.month)[1])
    candidate = reference.replace(day=day)
    if candidate >= reference:
        return candidate
    upcoming_month = shift_month(reference.replace(day=1), 1)
    return upcoming_month.replace(day=min(due_day, calendar.monthrange(upcoming_month.year, upcoming_month.month)[1]))

