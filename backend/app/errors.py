"""Domain errors. Services raise these; main.py maps them to HTTP codes,
so routes never contain if/else for error handling."""

from uuid import UUID

from app.domain import Status


class NotFoundError(Exception):
    def __init__(self, complaint_id: UUID) -> None:
        super().__init__(f"Complaint {complaint_id} not found")


class InvalidTransitionError(Exception):
    def __init__(self, current: Status, target: Status, allowed: frozenset[Status]) -> None:
        allowed_text = ", ".join(sorted(allowed)) if allowed else "none (terminal state)"
        super().__init__(
            f"Invalid status transition: {current} -> {target}. "
            f"Allowed from {current}: {allowed_text}"
        )
