"""Complaint business rules: validate -> triage -> persist -> invalidate stats."""

import uuid

from app.domain import Category, Priority, Status
from app.errors import NotFoundError
from app.repositories.complaints import ComplaintRepository
from app.schemas import ComplaintCreate, ComplaintOut, ComplaintPage
from app.services.state_machine import ensure_transition
from app.services.stats_service import StatsCache
from app.services.triage_service import TriageService


class ComplaintService:
    def __init__(
        self, repo: ComplaintRepository, triage: TriageService, stats_cache: StatsCache
    ) -> None:
        self._repo = repo
        self._triage = triage
        self._stats_cache = stats_cache

    def create(self, data: ComplaintCreate) -> ComplaintOut:
        # Id first, so a fallback WARNING can name the complaint it belongs to.
        complaint_id = uuid.uuid4()
        # Triage BEFORE touching the DB: no transaction held open during a slow AI call.
        outcome = self._triage.triage(complaint_id, data.text, data.location)
        row = self._repo.create(
            id=complaint_id,
            text=data.text,
            location=data.location,
            reporter_contact=data.reporter_contact,
            category=outcome.result.category,
            priority=outcome.result.priority,
            ai_summary=outcome.result.summary,
            triaged_by=outcome.triaged_by,
            triage_latency_ms=outcome.latency_ms,
        )
        self._stats_cache.invalidate()
        return ComplaintOut.model_validate(row)

    def get(self, complaint_id: uuid.UUID) -> ComplaintOut:
        row = self._repo.get(complaint_id)
        if row is None:
            raise NotFoundError(complaint_id)
        return ComplaintOut.model_validate(row)

    def list_complaints(
        self,
        *,
        category: Category | None,
        priority: Priority | None,
        status: Status | None,
        page: int,
        page_size: int,
    ) -> ComplaintPage:
        rows, total = self._repo.search(
            category=category,
            priority=priority,
            status=status,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return ComplaintPage(
            items=[ComplaintOut.model_validate(r) for r in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    def change_status(self, complaint_id: uuid.UUID, target: Status) -> ComplaintOut:
        row = self._repo.get(complaint_id)
        if row is None:
            raise NotFoundError(complaint_id)
        ensure_transition(row.status, target)  # raises InvalidTransitionError -> 409
        row = self._repo.update_status(row, target)
        self._stats_cache.invalidate()
        return ComplaintOut.model_validate(row)
