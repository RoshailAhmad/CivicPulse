"""ORM table definition. The real schema is created by Alembic
(alembic/versions/0001_create_complaints.py), never at app startup;
this class only tells SQLAlchemy how to map rows to objects."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, Index, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.domain import Category, Priority, Status
from app.repositories.db import Base


def _enum(enum_cls: type, name: str) -> Enum:
    return Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])


def _now() -> datetime:
    return datetime.now(UTC)


class ComplaintRow(Base):
    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint("length(text) BETWEEN 10 AND 2000", name="ck_complaints_text_len"),
        CheckConstraint("length(location) BETWEEN 3 AND 200", name="ck_complaints_location_len"),
        CheckConstraint("triage_latency_ms >= 0", name="ck_complaints_latency_nonneg"),
        CheckConstraint(
            "triaged_by IN ('llm:groq','llm:ollama','rules','rules:fallback','simulated')",
            name="ck_complaints_triaged_by",
        ),
        Index("ix_complaints_status_priority", "status", "priority"),
        Index("ix_complaints_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False)
    reporter_contact: Mapped[str | None] = mapped_column(String(200), nullable=True)
    category: Mapped[Category] = mapped_column(_enum(Category, "complaint_category"))
    priority: Mapped[Priority] = mapped_column(_enum(Priority, "complaint_priority"))
    status: Mapped[Status] = mapped_column(
        _enum(Status, "complaint_status"), default=Status.OPEN, server_default="open"
    )
    ai_summary: Mapped[str | None] = mapped_column(String(140), nullable=True)
    triaged_by: Mapped[str] = mapped_column(String(32), nullable=False)
    triage_latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, server_default=func.now(), onupdate=_now
    )
