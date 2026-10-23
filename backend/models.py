"""SQLAlchemy models used by PayArc."""

from __future__ import annotations

from datetime import date as date_type
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class Category(TimestampMixin, Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), default="expense", nullable=False)
    color: Mapped[str] = mapped_column(String(16), default="#8B5CF6", nullable=False)
    icon: Mapped[str] = mapped_column(String(48), default="wallet", nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    expenses: Mapped[list["Expense"]] = relationship(back_populates="category")
    budgets: Mapped[list["Budget"]] = relationship(back_populates="category")
    recurring_bills: Mapped[list["RecurringBill"]] = relationship(back_populates="category")


class Expense(TimestampMixin, Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    merchant: Mapped[str | None] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    date: Mapped[date_type] = mapped_column(Date, default=date_type.today, index=True, nullable=False)
    direction: Mapped[str] = mapped_column(String(16), default="expense", nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="posted", nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(60))
    account: Mapped[str | None] = mapped_column(String(80))
    expense_scope: Mapped[str] = mapped_column(String(24), default="personal", nullable=False)
    privacy: Mapped[str] = mapped_column(String(24), default="private", nullable=False)
    split_with: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[str | None] = mapped_column(String(300))
    receipt_url: Mapped[str | None] = mapped_column(String(500))
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    recurrence: Mapped[str | None] = mapped_column(String(32))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)
    profile_id: Mapped[int | None] = mapped_column(Integer, index=True)

    category: Mapped[Category | None] = relationship(back_populates="expenses")


class Budget(TimestampMixin, Base):
    __tablename__ = "budgets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    limit_amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    period: Mapped[str] = mapped_column(String(20), default="monthly", nullable=False)
    start_date: Mapped[date_type] = mapped_column(Date, default=date_type.today, nullable=False)
    end_date: Mapped[date_type | None] = mapped_column(Date)
    alert_percentage: Mapped[int] = mapped_column(Integer, default=80, nullable=False)
    color: Mapped[str] = mapped_column(String(16), default="#8B5CF6", nullable=False)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)

    category: Mapped[Category | None] = relationship(back_populates="budgets")


class Goal(TimestampMixin, Base):
    __tablename__ = "goals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    target_amount: Mapped[float] = mapped_column(Float, nullable=False)
    current_amount: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    target_date: Mapped[date_type | None] = mapped_column(Date)
    icon: Mapped[str] = mapped_column(String(48), default="sparkles", nullable=False)
    color: Mapped[str] = mapped_column(String(16), default="#22C55E", nullable=False)
    priority: Mapped[str] = mapped_column(String(16), default="medium", nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class RecurringBill(TimestampMixin, Base):
    __tablename__ = "recurring_bills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="INR", nullable=False)
    frequency: Mapped[str] = mapped_column(String(20), default="monthly", nullable=False)
    due_day: Mapped[int | None] = mapped_column(Integer)
    next_due_date: Mapped[date_type | None] = mapped_column(Date, index=True)
    autopay: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    account: Mapped[str | None] = mapped_column(String(80))
    notes: Mapped[str | None] = mapped_column(Text)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), index=True)

    category: Mapped[Category | None] = relationship(back_populates="recurring_bills")


class AssistantInteraction(Base):
    __tablename__ = "assistant_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    response: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

