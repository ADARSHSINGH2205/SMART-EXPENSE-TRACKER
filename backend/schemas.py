"""Pydantic v2 request and response models for PayArc."""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    slug: str | None = Field(default=None, max_length=80)
    kind: Literal["expense", "income", "transfer"] = "expense"
    color: str = Field(default="#8B5CF6", max_length=16)
    icon: str = Field(default="wallet", max_length=48)


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    slug: str | None = Field(default=None, min_length=1, max_length=80)
    kind: Literal["expense", "income", "transfer"] | None = None
    color: str | None = Field(default=None, max_length=16)
    icon: str | None = Field(default=None, max_length=48)


class CategoryRead(CategoryBase, ORMModel):
    id: int
    is_system: bool
    created_at: datetime
    updated_at: datetime


class ExpenseBase(BaseModel):
    title: str = Field(default="Expense", min_length=1, max_length=160)
    merchant: str | None = Field(default=None, max_length=160)
    description: str | None = None
    amount: float = Field(gt=0, le=100_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=8)
    date: date_type = Field(default_factory=date_type.today)
    direction: Literal["expense", "income", "transfer"] = "expense"
    status: Literal["posted", "pending", "void"] = "posted"
    payment_method: str | None = Field(default=None, max_length=60)
    account: str | None = Field(default=None, max_length=80)
    expense_scope: Literal["personal", "shared", "business", "family"] = "personal"
    privacy: Literal["private", "shared", "visible"] = "private"
    split_with: str | None = Field(default=None, max_length=200)
    notes: str | None = None
    tags: str | None = Field(default=None, max_length=300)
    receipt_url: str | None = Field(default=None, max_length=500)
    is_recurring: bool = False
    recurrence: Literal["weekly", "monthly", "quarterly", "yearly"] | None = None
    category_id: int | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.upper().strip()


class ExpenseCreate(ExpenseBase):
    pass


class ExpenseUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    merchant: str | None = Field(default=None, max_length=160)
    description: str | None = None
    amount: float | None = Field(default=None, gt=0, le=100_000_000)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    date: date_type | None = None
    direction: Literal["expense", "income", "transfer"] | None = None
    status: Literal["posted", "pending", "void"] | None = None
    payment_method: str | None = Field(default=None, max_length=60)
    account: str | None = Field(default=None, max_length=80)
    expense_scope: Literal["personal", "shared", "business", "family"] | None = None
    privacy: Literal["private", "shared", "visible"] | None = None
    split_with: str | None = Field(default=None, max_length=200)
    notes: str | None = None
    tags: str | None = Field(default=None, max_length=300)
    receipt_url: str | None = Field(default=None, max_length=500)
    is_recurring: bool | None = None
    recurrence: Literal["weekly", "monthly", "quarterly", "yearly"] | None = None
    category_id: int | None = None

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str | None) -> str | None:
        return value.upper().strip() if value else value


class ExpenseRead(ExpenseBase, ORMModel):
    id: int
    category: CategoryRead | None = None
    created_at: datetime
    updated_at: datetime


class BudgetBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    limit_amount: float = Field(gt=0, le=100_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=8)
    period: Literal["weekly", "monthly", "quarterly", "yearly", "custom"] = "monthly"
    start_date: date_type = Field(default_factory=date_type.today)
    end_date: date_type | None = None
    alert_percentage: int = Field(default=80, ge=1, le=100)
    color: str = Field(default="#8B5CF6", max_length=16)
    category_id: int | None = None


class BudgetCreate(BudgetBase):
    pass


class BudgetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    limit_amount: float | None = Field(default=None, gt=0, le=100_000_000)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    period: Literal["weekly", "monthly", "quarterly", "yearly", "custom"] | None = None
    start_date: date_type | None = None
    end_date: date_type | None = None
    alert_percentage: int | None = Field(default=None, ge=1, le=100)
    color: str | None = Field(default=None, max_length=16)
    category_id: int | None = None


class BudgetRead(BudgetBase, ORMModel):
    id: int
    category: CategoryRead | None = None
    created_at: datetime
    updated_at: datetime
    spent_amount: float = 0
    remaining_amount: float = 0
    percent_used: float = 0
    health: str = "on_track"


class GoalBase(BaseModel):
    name: str = Field(min_length=1, max_length=140)
    target_amount: float = Field(gt=0, le=100_000_000)
    current_amount: float = Field(default=0, ge=0, le=100_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=8)
    target_date: date_type | None = None
    icon: str = Field(default="sparkles", max_length=48)
    color: str = Field(default="#22C55E", max_length=16)
    priority: Literal["low", "medium", "high"] = "medium"
    is_archived: bool = False
    notes: str | None = None


class GoalCreate(GoalBase):
    pass


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=140)
    target_amount: float | None = Field(default=None, gt=0, le=100_000_000)
    current_amount: float | None = Field(default=None, ge=0, le=100_000_000)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    target_date: date_type | None = None
    icon: str | None = Field(default=None, max_length=48)
    color: str | None = Field(default=None, max_length=16)
    priority: Literal["low", "medium", "high"] | None = None
    is_archived: bool | None = None
    notes: str | None = None


class GoalContribution(BaseModel):
    amount: float = Field(gt=0, le=100_000_000)


class GoalRead(GoalBase, ORMModel):
    id: int
    created_at: datetime
    updated_at: datetime
    remaining_amount: float = 0
    progress_percentage: float = 0
    days_remaining: int | None = None


class RecurringBillBase(BaseModel):
    name: str = Field(min_length=1, max_length=140)
    amount: float = Field(gt=0, le=100_000_000)
    currency: str = Field(default="INR", min_length=3, max_length=8)
    frequency: Literal["weekly", "monthly", "quarterly", "yearly"] = "monthly"
    due_day: int | None = Field(default=None, ge=1, le=31)
    next_due_date: date_type | None = None
    autopay: bool = False
    active: bool = True
    account: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    category_id: int | None = None


class RecurringBillCreate(RecurringBillBase):
    pass


class RecurringBillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=140)
    amount: float | None = Field(default=None, gt=0, le=100_000_000)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    frequency: Literal["weekly", "monthly", "quarterly", "yearly"] | None = None
    due_day: int | None = Field(default=None, ge=1, le=31)
    next_due_date: date_type | None = None
    autopay: bool | None = None
    active: bool | None = None
    account: str | None = Field(default=None, max_length=80)
    notes: str | None = None
    category_id: int | None = None


class RecurringBillRead(RecurringBillBase, ORMModel):
    id: int
    category: CategoryRead | None = None
    created_at: datetime
    updated_at: datetime
    days_until_due: int | None = None


class AssistantChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class AssistantChatResponse(BaseModel):
    response: str
    suggestions: list[str] = []
    recommendations: list[dict] = []

