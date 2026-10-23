"""A hybrid financial assistant for PayArc.

Works with Gemini when connected, falls back to local rule-based mode when offline.
Private data is never logged; Gemini context is limited to financial summaries.
"""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from .models import Budget, Expense, Goal, RecurringBill
from .services import budget_spend, month_bounds, serialize_budget

def _money(value: float, currency: str = "INR") -> str:
    symbol = "₹" if currency.upper() == "INR" else f"{currency.upper()} "
    return f"{symbol}{value:,.0f}"


def finance_snapshot(db: Session, reference: date | None = None) -> dict:
    reference = reference or date.today()
    start, end = month_bounds(reference)
    rows = list(
        db.scalars(
            select(Expense)
            .options(joinedload(Expense.category))
            .where(Expense.date >= start, Expense.date <= end, Expense.status != "void")
        )
    )
    spending = [row for row in rows if row.direction == "expense"]
    incomes = [row for row in rows if row.direction == "income"]
    by_category: dict[str, float] = {}
    for item in spending:
        key = item.category.name if item.category else "Uncategorized"
        by_category[key] = by_category.get(key, 0) + item.amount
    return {
        "month_start": start,
        "month_end": end,
        "spending": round(sum(item.amount for item in spending), 2),
        "income": round(sum(item.amount for item in incomes), 2),
        "transaction_count": len(spending),
        "by_category": by_category,
        "currency": (rows[0].currency if rows else "INR"),
    }


def build_recommendations(db: Session, reference: date | None = None) -> list[dict]:
    """Generate actionable and explainable observations from stored data."""
    reference = reference or date.today()
    snapshot = finance_snapshot(db, reference)
    currency = snapshot["currency"]
    recommendations: list[dict] = []

    budgets = list(db.scalars(select(Budget).options(joinedload(Budget.category))))
    for budget in budgets:
        data = serialize_budget(db, budget, reference)
        if data["percent_used"] >= 100:
            recommendations.append(
                {
                    "id": f"budget-over-{budget.id}",
                    "kind": "budget",
                    "priority": "high",
                    "title": f"{budget.name} is over budget",
                    "message": (
                        f"You have used {_money(data['spent_amount'], budget.currency)} of your "
                        f"{_money(budget.limit_amount, budget.currency)} {budget.period} limit."
                    ),
                    "action": "Review recent transactions",
                }
            )
        elif data["percent_used"] >= budget.alert_percentage:
            recommendations.append(
                {
                    "id": f"budget-watch-{budget.id}",
                    "kind": "budget",
                    "priority": "medium",
                    "title": f"Watch your {budget.name} budget",
                    "message": (
                        f"{data['percent_used']:.0f}% is used; "
                        f"{_money(max(data['remaining_amount'], 0), budget.currency)} remains."
                    ),
                    "action": "Plan remaining spend",
                }
            )

    if snapshot["by_category"]:
        category, value = max(snapshot["by_category"].items(), key=lambda entry: entry[1])
        share = (value / snapshot["spending"] * 100) if snapshot["spending"] else 0
        recommendations.append(
            {
                "id": "top-category",
                "kind": "spending",
                "priority": "low",
                "title": f"{category} leads this month",
                "message": f"It represents {share:.0f}% of your {_money(snapshot['spending'], currency)} monthly spending.",
                "action": "Explore category activity",
            }
        )

    bills = list(
        db.scalars(
            select(RecurringBill).where(
                RecurringBill.active.is_(True),
                RecurringBill.next_due_date.is_not(None),
                RecurringBill.next_due_date >= reference,
                RecurringBill.next_due_date <= reference + timedelta(days=7),
            )
        )
    )
    for bill in bills[:2]:
        days = (bill.next_due_date - reference).days if bill.next_due_date else 0
        recommendations.append(
            {
                "id": f"bill-{bill.id}",
                "kind": "bill",
                "priority": "high" if days <= 2 else "medium",
                "title": f"{bill.name} is due {'today' if days == 0 else f'in {days} days'}",
                "message": f"Set aside {_money(bill.amount, bill.currency)}{'; autopay is on' if bill.autopay else ''}.",
                "action": "Open recurring bills",
            }
        )

    goals = list(db.scalars(select(Goal).where(Goal.is_archived.is_(False))))
    if goals:
        nearest_goal = min(
            goals,
            key=lambda goal: (goal.target_date or date.max, -(goal.current_amount / goal.target_amount)),
        )
        remaining = max(nearest_goal.target_amount - nearest_goal.current_amount, 0)
        if remaining > 0:
            recommendations.append(
                {
                    "id": f"goal-{nearest_goal.id}",
                    "kind": "goal",
                    "priority": "low",
                    "title": f"Keep building {nearest_goal.name}",
                    "message": f"Only {_money(remaining, nearest_goal.currency)} remains to reach this goal.",
                    "action": "Add a contribution",
                }
            )
    elif snapshot["income"] > snapshot["spending"]:
        recommendations.append(
            {
                "id": "new-goal",
                "kind": "goal",
                "priority": "low",
                "title": "Turn your surplus into a goal",
                "message": "Your income is above your tracked spending this month. A small automatic saving goal can preserve that momentum.",
                "action": "Create a goal",
            }
        )

    if not recommendations:
        recommendations.append(
            {
                "id": "first-step",
                "kind": "welcome",
                "priority": "low",
                "title": "Start with one expense",
                "message": "The assistant becomes more useful as you add expenses, budgets, goals, and recurring bills.",
                "action": "Add transaction",
            }
        )
    return recommendations[:6]


def respond_to_message(db: Session, message: str) -> tuple[str, list[str], list[dict]]:
    """Create answer using Gemini if available, fallback to local rules if offline."""
    question = message.lower().strip()
    snapshot = finance_snapshot(db)
    currency = snapshot["currency"]
    recommendations = build_recommendations(db)
    suggestions = ["Show my budgets", "What bills are due?", "How can I save more?"]
    
    # Local rule-based fallback

    if any(term in question for term in ("spend", "spent", "expense", "summary", "month")):
        response = (
            f"This month you have tracked {_money(snapshot['spending'], currency)} in spending across "
            f"{snapshot['transaction_count']} expense{'s' if snapshot['transaction_count'] != 1 else ''}. "
        )
        if snapshot["by_category"]:
            category, value = max(snapshot["by_category"].items(), key=lambda entry: entry[1])
            response += f"Your largest category is {category} at {_money(value, currency)}."
        else:
            response += "Add a few categorized transactions and I can identify patterns."
    elif any(term in question for term in ("budget", "limit", "overspend")):
        budgets = list(db.scalars(select(Budget).options(joinedload(Budget.category))))
        if budgets:
            attention = sorted((serialize_budget(db, item) for item in budgets), key=lambda item: item["percent_used"], reverse=True)[0]
            response = (
                f"Your closest budget is {attention['name']}: {attention['percent_used']:.0f}% used "
                f"({_money(attention['spent_amount'], attention['currency'])} of "
                f"{_money(attention['limit_amount'], attention['currency'])})."
            )
        else:
            response = "You do not have a budget yet. Start with one flexible monthly cap for your largest spending category."
    elif any(term in question for term in ("save", "saving", "goal", "invest")):
        surplus = snapshot["income"] - snapshot["spending"]
        if snapshot["income"]:
            response = (
                f"Your current tracked surplus is {_money(surplus, currency)}. "
                "A practical next move is to automate a portion of it toward your highest-priority goal."
            )
        else:
            response = "Set a small goal and add income records too; that lets me calculate a realistic savings amount rather than guessing."
    elif any(term in question for term in ("bill", "subscription", "due", "renewal")):
        bills = [item for item in recommendations if item["kind"] == "bill"]
        response = bills[0]["message"] if bills else "No active recurring bills are due within the next week. You can add subscriptions, rent, EMIs, and utilities in Recurring Bills."
    elif any(term in question for term in ("hello", "hi", "help", "what can")):
        response = "I’m your private PayArc assistant. I can summarize spending, flag budgets, surface upcoming bills, and suggest next steps from the data stored in this app."
    else:
        response = (
            "I can help with your spending, budgets, savings goals, and upcoming bills. "
            f"Right now, {_money(snapshot['spending'], currency)} is tracked for this month. What would you like to explore?"
        )
    return response, suggestions, recommendations

