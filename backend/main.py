"""PayArc FastAPI application.

Run locally from the project root with:
    uvicorn backend.main:app --reload --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import Any

from fastapi import Body, Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from .assistant import build_recommendations, finance_snapshot, respond_to_message
from .database import Base, SessionLocal, engine, get_db
from .models import AssistantInteraction, Budget, Category, Expense, Goal, RecurringBill
from .schemas import (
    AssistantChatRequest,
    BudgetCreate,
    BudgetUpdate,
    CategoryCreate,
    CategoryUpdate,
    ExpenseCreate,
    ExpenseUpdate,
    GoalContribution,
    GoalCreate,
    GoalUpdate,
    RecurringBillCreate,
    RecurringBillUpdate,
)
from .seed import seed_database
from .extensions import ensure_extensions, router as productivity_router
from .gemini import ask_gemini, gemini_status, verify_gemini
from .services import (
    month_bounds,
    safe_next_due_date,
    serialize_bill,
    serialize_budget,
    serialize_category,
    serialize_expense,
    serialize_goal,
    shift_month,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_database(db)
        ensure_extensions(db)
    yield


app = FastAPI(
    title="PayArc API",
    version="1.0.0",
    description="A privacy-friendly personal expense management API.",
    lifespan=lifespan,
)

# Vite's standard dev / preview ports, plus a localhost regex for custom ports.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_origin_regex=r"^https?://(localhost|127\\.0\\.0\\.1)(:\\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(productivity_router)


def get_or_404(db: Session, model: type[Any], item_id: int, label: str):
    item = db.get(model, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"{label} {item_id} was not found")
    return item


def category_by_id(db: Session, category_id: int | None) -> None:
    if category_id is not None and db.get(Category, category_id) is None:
        raise HTTPException(status_code=422, detail="The selected category does not exist")


def category_from_value(db: Session, value: object) -> int | None:
    """Resolve a category ID or readable category name for frontend-friendly writes."""
    if value in (None, "", "Uncategorized"):
        return None
    if isinstance(value, dict):
        value = value.get("id") or value.get("name")
    if isinstance(value, int):
        category_by_id(db, value)
        return value
    text = str(value).strip()
    if text.isdigit():
        category_id = int(text)
        category_by_id(db, category_id)
        return category_id
    category = db.scalar(select(Category).where(func.lower(Category.name) == text.lower()))
    if category:
        return category.id
    # A custom category can be created implicitly when a user types a new one.
    slug = "-".join(part for part in text.lower().split() if part.isalnum())[:80] or "custom"
    suffix = 2
    candidate = slug
    while db.scalar(select(Category.id).where(Category.slug == candidate)) is not None:
        candidate = f"{slug[:72]}-{suffix}"
        suffix += 1
    category = Category(name=text[:80], slug=candidate, kind="expense", color="#8B5CF6", icon="circle", is_system=False)
    db.add(category)
    db.flush()
    return category.id


def normalize_transaction_payload(db: Session, payload: dict[str, Any]) -> dict[str, Any]:
    """Accept both the rich API payload and the compact dashboard card payload."""
    data = dict(payload)
    if "type" in data and "direction" not in data:
        data["direction"] = data.pop("type")
    if "note" in data and "notes" not in data:
        data["notes"] = data.pop("note")
    if "private" in data and "privacy" not in data:
        data["privacy"] = "private" if data.pop("private") else "visible"
    if "scope" in data and "expense_scope" not in data:
        data["expense_scope"] = data.pop("scope")
    if "category" in data and "category_id" not in data:
        data["category_id"] = category_from_value(db, data.pop("category"))
    if data.get("category_id") is not None:
        data["category_id"] = category_from_value(db, data["category_id"])
    if data.get("merchant") and not data.get("title"):
        data["title"] = data["merchant"]
    amount = data.get("amount")
    if amount is not None:
        try:
            amount_number = float(amount)
        except (TypeError, ValueError):
            raise HTTPException(status_code=422, detail="amount must be a number") from None
        if amount_number < 0:
            data["direction"] = data.get("direction", "expense")
            data["amount"] = abs(amount_number)
        else:
            data["amount"] = amount_number
    return data


def transaction_card(expense: Expense) -> dict[str, Any]:
    category = expense.category
    signed_amount = -expense.amount if expense.direction == "expense" else expense.amount
    return {
        "id": expense.id,
        "merchant": expense.merchant or expense.title,
        "title": expense.title,
        "category": category.name if category else "Uncategorized",
        "category_id": expense.category_id,
        "account": expense.account or "Cash",
        "amount": round(signed_amount, 2),
        "date": expense.date.isoformat(),
        "icon": category.icon if category else "circle",
        "color": category.color if category else "#94A3B8",
        "type": expense.direction,
        "direction": expense.direction,
        "note": expense.notes or expense.description or "",
        "private": expense.privacy == "private",
        "privacy": expense.privacy,
        "status": expense.status,
        "tags": [tag.strip() for tag in (expense.tags or "").split(",") if tag.strip()],
    }


def budget_card(db: Session, budget: Budget) -> dict[str, Any]:
    rich = serialize_budget(db, budget)
    category = budget.category
    return {
        "id": budget.id,
        "category": category.name if category else budget.name,
        "name": budget.name,
        "spent": rich["spent_amount"],
        "limit": budget.limit_amount,
        "color": budget.color,
        "icon": category.icon if category else "wallet",
        "period": budget.period,
        "currency": budget.currency,
        "progress": rich["progress"],
        "health": rich["health"],
        "category_id": budget.category_id,
        "alert_percentage": budget.alert_percentage,
        "start_date": budget.start_date.isoformat(),
        "end_date": budget.end_date.isoformat() if budget.end_date else None,
    }


def goal_card(goal: Goal) -> dict[str, Any]:
    rich = serialize_goal(goal)
    emoji_by_icon = {
        "plane": "✈️",
        "shield-check": "🛡️",
        "laptop": "💻",
        "sparkles": "✨",
        "home": "🏠",
        "car": "🚗",
    }
    return {
        "id": goal.id,
        "name": goal.name,
        "emoji": emoji_by_icon.get(goal.icon, "✨"),
        "icon": goal.icon,
        "saved": goal.current_amount,
        "target": goal.target_amount,
        "monthly": 0,
        "date": goal.target_date.isoformat() if goal.target_date else None,
        "target_date": goal.target_date.isoformat() if goal.target_date else None,
        "color": goal.color,
        "currency": goal.currency,
        "priority": goal.priority,
        "progress": rich["progress"],
        "remaining": rich["remaining"],
        "days_remaining": rich["days_remaining"],
        "is_archived": goal.is_archived,
        "notes": goal.notes,
    }


def bill_card(bill: RecurringBill) -> dict[str, Any]:
    rich = serialize_bill(bill)
    category = bill.category
    return {
        "id": bill.id,
        "name": bill.name,
        "category": category.name if category else "Other",
        "category_id": bill.category_id,
        "amount": bill.amount,
        "currency": bill.currency,
        "cadence": bill.frequency,
        "frequency": bill.frequency,
        "due": bill.next_due_date.isoformat() if bill.next_due_date else None,
        "next_due_date": bill.next_due_date.isoformat() if bill.next_due_date else None,
        "icon": category.icon if category else "refresh-cw",
        "color": category.color if category else "#8B5CF6",
        "active": bill.active,
        "autopay": bill.autopay,
        "account": bill.account,
        "notes": bill.notes,
        "days_until_due": rich["days_until_due"],
    }


def dashboard_payload(db: Session) -> dict[str, Any]:
    today = date.today()
    current_start, current_end = month_bounds(today)
    snapshot = finance_snapshot(db, today)
    prior_reference = current_start - timedelta(days=1)
    prior_snapshot = finance_snapshot(db, prior_reference)
    currency = snapshot["currency"]
    budgets = list(db.scalars(select(Budget).options(joinedload(Budget.category)).order_by(Budget.created_at.desc())))
    goals = list(db.scalars(select(Goal).where(Goal.is_archived.is_(False)).order_by(Goal.priority.desc(), Goal.target_date)))
    bills = list(
        db.scalars(
            select(RecurringBill)
            .options(joinedload(RecurringBill.category))
            .where(RecurringBill.active.is_(True))
            .order_by(RecurringBill.next_due_date)
        )
    )
    expenses = list(
        db.scalars(
            select(Expense)
            .options(joinedload(Expense.category))
            .order_by(Expense.date.desc(), Expense.created_at.desc())
            .limit(8)
        )
    )
    current_spend = snapshot["spending"]
    prior_spend = prior_snapshot["spending"]
    change = round(((current_spend - prior_spend) / prior_spend) * 100, 1) if prior_spend else 0
    upcoming_bills_total = sum(
        bill.amount
        for bill in bills
        if bill.next_due_date and current_start <= bill.next_due_date <= current_end
    )
    balance = round(snapshot["income"] - current_spend, 2)
    safe_to_spend = round(max(balance - upcoming_bills_total, 0), 2)
    budget_cards = [budget_card(db, item) for item in budgets]
    budget_attention = sum(1 for item in budget_cards if item["health"] != "on_track")
    health_score = max(0, min(100, int(90 - budget_attention * 12 - max(change, 0) * 0.2 + (8 if balance >= 0 else -15))))

    category_totals: dict[str, dict[str, Any]] = {}
    monthly_expenses = list(
        db.scalars(
            select(Expense)
            .options(joinedload(Expense.category))
            .where(
                Expense.direction == "expense",
                Expense.status != "void",
                Expense.date >= current_start,
                Expense.date <= current_end,
            )
        )
    )
    for item in monthly_expenses:
        key = item.category.name if item.category else "Uncategorized"
        category_totals.setdefault(
            key,
            {
                "name": key,
                "amount": 0.0,
                "color": item.category.color if item.category else "#94A3B8",
                "icon": item.category.icon if item.category else "circle",
            },
        )
        category_totals[key]["amount"] += item.amount
    category_breakdown = [
        {**item, "amount": round(item["amount"], 2), "percentage": round(item["amount"] / current_spend * 100, 1) if current_spend else 0}
        for item in sorted(category_totals.values(), key=lambda value: value["amount"], reverse=True)
    ]

    trend: list[dict[str, Any]] = []
    for offset in range(-5, 1):
        reference = shift_month(current_start, offset)
        start, end = month_bounds(reference)
        rows = list(
            db.scalars(
                select(Expense).where(Expense.date >= start, Expense.date <= end, Expense.status != "void")
            )
        )
        trend.append(
            {
                "label": reference.strftime("%b"),
                "month": reference.strftime("%Y-%m"),
                "income": round(sum(row.amount for row in rows if row.direction == "income"), 2),
                "spend": round(sum(row.amount for row in rows if row.direction == "expense"), 2),
            }
        )

    daily_spending: list[dict[str, Any]] = []
    for days_ago in range(6, -1, -1):
        moment = today - timedelta(days=days_ago)
        amount = sum(item.amount for item in monthly_expenses if item.date == moment)
        daily_spending.append({"label": moment.strftime("%a"), "date": moment.isoformat(), "amount": round(amount, 2)})

    active_dates = {item.date for item in db.scalars(select(Expense).where(Expense.status != "void"))}
    streak = 0
    cursor = today
    while cursor in active_dates:
        streak += 1
        cursor -= timedelta(days=1)

    recommendations = build_recommendations(db, today)
    first_insight = recommendations[0]
    return {
        "user": {"name": "Alex", "initials": "AL", "greeting": "Good to see you"},
        "balance": balance,
        "income": snapshot["income"],
        "spent": current_spend,
        "saved": round(sum(item.current_amount for item in goals), 2),
        "monthlyChange": change,
        "financialHealth": {
            "score": health_score,
            "label": "Excellent" if health_score >= 80 else "Steady" if health_score >= 60 else "Needs attention",
            "summary": "Your plan is on track." if health_score >= 70 else "A few quick adjustments can improve your month.",
        },
        "safeToSpend": safe_to_spend,
        "streak": {"days": streak, "label": f"{streak}-day tracking streak" if streak else "Log today to start a streak"},
        "insight": {"title": first_insight["title"], "body": first_insight["message"], "action": first_insight["action"]},
        "cashflow": trend,
        "currency": currency,
        "period": {"start": current_start.isoformat(), "end": current_end.isoformat()},
        "summary": {
            "income": snapshot["income"],
            "spending": current_spend,
            "balance": balance,
            "safe_to_spend": safe_to_spend,
            "monthly_change": change,
        },
        "recentTransactions": [transaction_card(item) for item in expenses],
        "transactions": [transaction_card(item) for item in expenses],
        "budgets": budget_cards,
        "goals": [goal_card(item) for item in goals],
        "upcomingBills": [bill_card(item) for item in bills[:5]],
        "bills": [bill_card(item) for item in bills],
        "categoryBreakdown": category_breakdown,
        "weeklySpending": daily_spending,
        "monthlyTrend": trend,
        "recommendations": recommendations,
    }


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"name": "PayArc API", "docs": "/docs", "health": "/api/health"}


@app.get("/api/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "payarc-api", "version": app.version}


@app.get("/api/dashboard", tags=["dashboard"])
def get_dashboard(db: Session = Depends(get_db)) -> dict[str, Any]:
    return dashboard_payload(db)


@app.get("/api/analytics", tags=["dashboard"])
def get_analytics(db: Session = Depends(get_db)) -> dict[str, Any]:
    payload = dashboard_payload(db)
    return {
        "period": payload["period"],
        "cashflow": payload["cashflow"],
        "category_breakdown": payload["categoryBreakdown"],
        "weekly_spending": payload["weeklySpending"],
        "financial_health": payload["financialHealth"],
    }


# Categories -----------------------------------------------------------------
@app.get("/api/categories", tags=["categories"])
def list_categories(kind: str | None = Query(default=None), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    statement = select(Category).order_by(Category.kind, Category.name)
    if kind:
        statement = statement.where(Category.kind == kind)
    return [serialize_category(item) for item in db.scalars(statement)]


@app.post("/api/categories", status_code=status.HTTP_201_CREATED, tags=["categories"])
def create_category(payload: CategoryCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    slug = payload.slug or "-".join(part for part in payload.name.lower().split() if part.isalnum())
    if db.scalar(select(Category.id).where((Category.name == payload.name) | (Category.slug == slug))):
        raise HTTPException(status_code=409, detail="A category with this name already exists")
    category = Category(**payload.model_dump(), slug=slug, is_system=False)
    db.add(category)
    db.commit()
    db.refresh(category)
    return serialize_category(category)


@app.patch("/api/categories/{category_id}", tags=["categories"])
def update_category(category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    category = get_or_404(db, Category, category_id, "Category")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return serialize_category(category)


@app.delete("/api/categories/{category_id}", tags=["categories"])
def delete_category(category_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    category = get_or_404(db, Category, category_id, "Category")
    if category.is_system:
        raise HTTPException(status_code=400, detail="System categories are protected")
    if db.scalar(select(func.count()).select_from(Expense).where(Expense.category_id == category_id)):
        raise HTTPException(status_code=409, detail="Reassign transactions before deleting this category")
    db.delete(category)
    db.commit()
    return {"deleted": True, "id": category_id}


# Transactions (compact frontend contract) -----------------------------------
def _transaction_statement(
    *,
    start_date: date | None,
    end_date: date | None,
    category_id: int | None,
    direction: str | None,
    search: str | None,
):
    statement = select(Expense).options(joinedload(Expense.category)).order_by(Expense.date.desc(), Expense.created_at.desc())
    if start_date:
        statement = statement.where(Expense.date >= start_date)
    if end_date:
        statement = statement.where(Expense.date <= end_date)
    if category_id:
        statement = statement.where(Expense.category_id == category_id)
    if direction:
        statement = statement.where(Expense.direction == direction)
    if search:
        match = f"%{search.strip()}%"
        statement = statement.where((Expense.title.ilike(match)) | (Expense.merchant.ilike(match)) | (Expense.notes.ilike(match)))
    return statement


@app.get("/api/transactions", tags=["transactions"])
def list_transactions(
    start_date: date | None = None,
    end_date: date | None = None,
    category_id: int | None = None,
    direction: str | None = None,
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    statement = _transaction_statement(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        direction=direction,
        search=search,
    ).offset(offset).limit(limit)
    return [transaction_card(item) for item in db.scalars(statement)]


@app.post("/api/transactions", status_code=status.HTTP_201_CREATED, tags=["transactions"])
def create_transaction(payload: dict[str, Any] = Body(...), db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        validated = ExpenseCreate.model_validate(normalize_transaction_payload(db, payload))
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    category_by_id(db, validated.category_id)
    expense = Expense(**validated.model_dump())
    from .extensions import active_profile_id
    expense.profile_id = active_profile_id(db)
    db.add(expense)
    db.commit()
    db.refresh(expense, attribute_names=["category"])
    return transaction_card(expense)


@app.patch("/api/transactions/{transaction_id}", tags=["transactions"])
def update_transaction(transaction_id: int, payload: dict[str, Any] = Body(...), db: Session = Depends(get_db)) -> dict[str, Any]:
    expense = get_or_404(db, Expense, transaction_id, "Transaction")
    try:
        values = ExpenseUpdate.model_validate(normalize_transaction_payload(db, payload)).model_dump(exclude_unset=True)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc
    category_by_id(db, values.get("category_id"))
    for field, value in values.items():
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense, attribute_names=["category"])
    return transaction_card(expense)


@app.delete("/api/transactions/{transaction_id}", tags=["transactions"])
def delete_transaction(transaction_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    expense = get_or_404(db, Expense, transaction_id, "Transaction")
    db.delete(expense)
    db.commit()
    return {"deleted": True, "id": transaction_id}


# Rich expenses endpoint ------------------------------------------------------
@app.get("/api/expenses", tags=["expenses"])
def list_expenses(
    start_date: date | None = None,
    end_date: date | None = None,
    category_id: int | None = None,
    direction: str | None = None,
    search: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    statement = _transaction_statement(
        start_date=start_date,
        end_date=end_date,
        category_id=category_id,
        direction=direction,
        search=search,
    ).offset(offset).limit(limit)
    return [serialize_expense(item) for item in db.scalars(statement)]


@app.post("/api/expenses", status_code=status.HTTP_201_CREATED, tags=["expenses"])
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    category_by_id(db, payload.category_id)
    expense = Expense(**payload.model_dump())
    db.add(expense)
    db.commit()
    db.refresh(expense, attribute_names=["category"])
    return serialize_expense(expense)


@app.get("/api/expenses/{expense_id}", tags=["expenses"])
def get_expense(expense_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    expense = get_or_404(db, Expense, expense_id, "Expense")
    db.refresh(expense, attribute_names=["category"])
    return serialize_expense(expense)


@app.patch("/api/expenses/{expense_id}", tags=["expenses"])
def update_expense(expense_id: int, payload: ExpenseUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    expense = get_or_404(db, Expense, expense_id, "Expense")
    values = payload.model_dump(exclude_unset=True)
    category_by_id(db, values.get("category_id"))
    for field, value in values.items():
        setattr(expense, field, value)
    db.commit()
    db.refresh(expense, attribute_names=["category"])
    return serialize_expense(expense)


@app.delete("/api/expenses/{expense_id}", tags=["expenses"])
def delete_expense(expense_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    return delete_transaction(expense_id, db)


# Budgets --------------------------------------------------------------------
@app.get("/api/budgets", tags=["budgets"])
def list_budgets(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    budgets = db.scalars(select(Budget).options(joinedload(Budget.category)).order_by(Budget.created_at.desc()))
    return [budget_card(db, item) for item in budgets]


@app.post("/api/budgets", status_code=status.HTTP_201_CREATED, tags=["budgets"])
def create_budget(payload: BudgetCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    category_by_id(db, payload.category_id)
    budget = Budget(**payload.model_dump())
    db.add(budget)
    db.commit()
    db.refresh(budget, attribute_names=["category"])
    return budget_card(db, budget)


@app.patch("/api/budgets/{budget_id}", tags=["budgets"])
def update_budget(budget_id: int, payload: BudgetUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    budget = get_or_404(db, Budget, budget_id, "Budget")
    values = payload.model_dump(exclude_unset=True)
    category_by_id(db, values.get("category_id"))
    for field, value in values.items():
        setattr(budget, field, value)
    db.commit()
    db.refresh(budget, attribute_names=["category"])
    return budget_card(db, budget)


@app.delete("/api/budgets/{budget_id}", tags=["budgets"])
def delete_budget(budget_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    budget = get_or_404(db, Budget, budget_id, "Budget")
    db.delete(budget)
    db.commit()
    return {"deleted": True, "id": budget_id}


# Goals ----------------------------------------------------------------------
@app.get("/api/goals", tags=["goals"])
def list_goals(include_archived: bool = False, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    statement = select(Goal).order_by(Goal.is_archived, Goal.target_date)
    if not include_archived:
        statement = statement.where(Goal.is_archived.is_(False))
    return [goal_card(item) for item in db.scalars(statement)]


@app.post("/api/goals", status_code=status.HTTP_201_CREATED, tags=["goals"])
def create_goal(payload: GoalCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    goal = Goal(**payload.model_dump())
    db.add(goal)
    db.commit()
    db.refresh(goal)
    return goal_card(goal)


@app.patch("/api/goals/{goal_id}", tags=["goals"])
def update_goal(goal_id: int, payload: GoalUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    goal = get_or_404(db, Goal, goal_id, "Goal")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(goal, field, value)
    db.commit()
    db.refresh(goal)
    return goal_card(goal)


@app.post("/api/goals/{goal_id}/contributions", tags=["goals"])
def contribute_to_goal(goal_id: int, payload: GoalContribution, db: Session = Depends(get_db)) -> dict[str, Any]:
    goal = get_or_404(db, Goal, goal_id, "Goal")
    goal.current_amount += payload.amount
    db.commit()
    db.refresh(goal)
    return goal_card(goal)


@app.delete("/api/goals/{goal_id}", tags=["goals"])
def delete_goal(goal_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    goal = get_or_404(db, Goal, goal_id, "Goal")
    db.delete(goal)
    db.commit()
    return {"deleted": True, "id": goal_id}


# Recurring bills ------------------------------------------------------------
@app.get("/api/recurring-bills", tags=["recurring bills"])
def list_recurring_bills(active_only: bool = False, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    statement = select(RecurringBill).options(joinedload(RecurringBill.category)).order_by(RecurringBill.next_due_date)
    if active_only:
        statement = statement.where(RecurringBill.active.is_(True))
    return [bill_card(item) for item in db.scalars(statement)]


@app.post("/api/recurring-bills", status_code=status.HTTP_201_CREATED, tags=["recurring bills"])
def create_recurring_bill(payload: RecurringBillCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    category_by_id(db, payload.category_id)
    values = payload.model_dump()
    if values.get("next_due_date") is None and values.get("due_day"):
        values["next_due_date"] = safe_next_due_date(date.today(), values["due_day"])
    bill = RecurringBill(**values)
    db.add(bill)
    db.commit()
    db.refresh(bill, attribute_names=["category"])
    return bill_card(bill)


@app.patch("/api/recurring-bills/{bill_id}", tags=["recurring bills"])
def update_recurring_bill(bill_id: int, payload: RecurringBillUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    bill = get_or_404(db, RecurringBill, bill_id, "Recurring bill")
    values = payload.model_dump(exclude_unset=True)
    category_by_id(db, values.get("category_id"))
    for field, value in values.items():
        setattr(bill, field, value)
    if "due_day" in values and "next_due_date" not in values:
        bill.next_due_date = safe_next_due_date(date.today(), bill.due_day)
    db.commit()
    db.refresh(bill, attribute_names=["category"])
    return bill_card(bill)


@app.delete("/api/recurring-bills/{bill_id}", tags=["recurring bills"])
def delete_recurring_bill(bill_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    bill = get_or_404(db, RecurringBill, bill_id, "Recurring bill")
    db.delete(bill)
    db.commit()
    return {"deleted": True, "id": bill_id}


# Personal assistant ---------------------------------------------------------
@app.get("/api/assistant/recommendations", tags=["assistant"])
def get_recommendations(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    return build_recommendations(db)


@app.get("/api/assistant/status", tags=["assistant"])
def assistant_status() -> dict[str, Any]:
    return gemini_status()


@app.post("/api/assistant/verify", tags=["assistant"])
def assistant_verify() -> dict[str, Any]:
    return verify_gemini()

@app.post("/api/assistant/chat", tags=["assistant"])
def assistant_chat(payload: AssistantChatRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    local_response, suggestions, recommendations = respond_to_message(db, payload.message)
    ai_response = ask_gemini(db, payload.message)
    response = ai_response or local_response
    provider = "gemini" if ai_response else "local"
    interaction = AssistantInteraction(message=payload.message, response=response)
    db.add(interaction)
    db.commit()
    return {
        "response": response,
        "message": response,
        "suggestions": suggestions,
        "actions": suggestions,
        "insights": recommendations,
        "recommendations": recommendations,
        "provider": provider,
        "privacy": "Gemini receives only an aggregate financial snapshot when configured; otherwise PayArc uses its local rule-based Copilot.",
    }


@app.get("/api/assistant/history", tags=["assistant"])
def assistant_history(limit: int = Query(default=20, ge=1, le=100), db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.scalars(select(AssistantInteraction).order_by(AssistantInteraction.created_at.desc()).limit(limit))
    return [
        {"id": row.id, "message": row.message, "response": row.response, "created_at": row.created_at.isoformat()}
        for row in rows
    ]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)

