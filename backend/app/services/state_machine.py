"""Complaint status state machine as an explicit transition table.
To change the rules, change this table - there is no other copy anywhere
(the frontend just shows the server's answer)."""

from app.domain import Status
from app.errors import InvalidTransitionError

TRANSITIONS: dict[Status, frozenset[Status]] = {
    Status.OPEN: frozenset({Status.IN_PROGRESS, Status.REJECTED}),
    Status.IN_PROGRESS: frozenset({Status.RESOLVED, Status.REJECTED}),
    Status.RESOLVED: frozenset(),  # terminal
    Status.REJECTED: frozenset(),  # terminal
}


def ensure_transition(current: Status, target: Status) -> None:
    allowed = TRANSITIONS[current]
    if target not in allowed:
        raise InvalidTransitionError(current, target, allowed)
