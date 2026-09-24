import pytest
from sqlalchemy.orm import Session, sessionmaker

from app.domain import Status
from app.errors import InvalidTransitionError
from app.repositories.complaints import ComplaintRepository
from app.seed import COMPLAINTS, build_rows
from app.services.state_machine import ensure_transition


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (Status.OPEN, Status.IN_PROGRESS),
        (Status.OPEN, Status.REJECTED),
        (Status.IN_PROGRESS, Status.RESOLVED),
        (Status.IN_PROGRESS, Status.REJECTED),
    ],
)
def test_allowed_transitions(current: Status, target: Status) -> None:
    ensure_transition(current, target)


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (Status.OPEN, Status.RESOLVED),
        (Status.RESOLVED, Status.OPEN),
        (Status.REJECTED, Status.IN_PROGRESS),
        (Status.IN_PROGRESS, Status.OPEN),
    ],
)
def test_forbidden_transitions(current: Status, target: Status) -> None:
    with pytest.raises(InvalidTransitionError):
        ensure_transition(current, target)


def test_seed_is_idempotent(session_factory: sessionmaker[Session]) -> None:
    assert len(COMPLAINTS) >= 30
    with session_factory() as session:
        repo = ComplaintRepository(session)
        assert repo.seed(build_rows()) == len(COMPLAINTS)
        assert repo.seed(build_rows()) == 0  # second run changes nothing
        assert repo.stats()["total"] == len(COMPLAINTS)
        categories = {k for k, v in repo.stats()["by_category"].items() if v > 0}
        assert len(categories) == 6  # spread across every category
