"""All SQL for complaints lives here and nowhere else."""

import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.domain import Category, Priority, Status
from app.repositories.models import ComplaintRow


class ComplaintRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, **fields: Any) -> ComplaintRow:
        row = ComplaintRow(**fields)
        self._session.add(row)
        self._session.commit()
        self._session.refresh(row)
        return row

    def get(self, complaint_id: uuid.UUID) -> ComplaintRow | None:
        return self._session.get(ComplaintRow, complaint_id)

    def search(
        self,
        *,
        category: Category | None,
        priority: Priority | None,
        status: Status | None,
        limit: int,
        offset: int,
    ) -> tuple[list[ComplaintRow], int]:
        filters = []
        if category is not None:
            filters.append(ComplaintRow.category == category)
        if priority is not None:
            filters.append(ComplaintRow.priority == priority)
        if status is not None:
            filters.append(ComplaintRow.status == status)

        total = self._session.scalar(select(func.count()).select_from(ComplaintRow).where(*filters))
        rows = self._session.scalars(
            select(ComplaintRow)
            .where(*filters)
            .order_by(ComplaintRow.created_at.desc(), ComplaintRow.id)
            .limit(limit)
            .offset(offset)
        ).all()
        return list(rows), int(total or 0)

    def update_status(self, row: ComplaintRow, new_status: Status) -> ComplaintRow:
        row.status = new_status
        self._session.commit()
        self._session.refresh(row)
        return row

    def stats(self) -> dict[str, Any]:
        def counts(column: Any, enum_cls: type[StrEnum]) -> dict[str, int]:
            result = {member.value: 0 for member in enum_cls}
            for value, count in self._session.execute(
                select(column, func.count()).group_by(column)
            ):
                result[str(value.value if hasattr(value, "value") else value)] = int(count)
            return result

        by_category = counts(ComplaintRow.category, Category)
        return {
            "total": sum(by_category.values()),
            "by_category": by_category,
            "by_priority": counts(ComplaintRow.priority, Priority),
            "by_status": counts(ComplaintRow.status, Status),
        }

    def seed(self, rows: list[dict[str, Any]]) -> int:
        """Insert rows whose id is not already present. Returns how many were new."""
        if self._session.get_bind().dialect.name == "postgresql":
            # Pods seeding at the same moment wait for each other instead of racing.
            self._session.execute(text("SELECT pg_advisory_xact_lock(7240002)"))
        inserted = 0
        for fields in rows:
            if self._session.get(ComplaintRow, fields["id"]) is None:
                self._session.add(ComplaintRow(**fields))
                inserted += 1
        self._session.commit()
        return inserted


class HealthRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def ping(self) -> None:
        self._session.execute(text("SELECT 1"))
