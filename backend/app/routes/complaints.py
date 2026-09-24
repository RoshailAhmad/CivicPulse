"""HTTP only: parse, validate, call the service, return. No business rules."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.dependencies import enforce_rate_limit, get_complaint_service
from app.domain import Category, Priority, Status
from app.schemas import (
    ComplaintCreate,
    ComplaintOut,
    ComplaintPage,
    ErrorBody,
    StatusUpdate,
    ValidationErrorBody,
)
from app.services.complaint_service import ComplaintService

router = APIRouter(prefix="/api/complaints", tags=["complaints"])


@router.post(
    "",
    status_code=201,
    response_model=ComplaintOut,
    dependencies=[Depends(enforce_rate_limit)],
    responses={400: {"model": ValidationErrorBody}, 429: {"model": ErrorBody}},
)
def create_complaint(
    body: ComplaintCreate, service: ComplaintService = Depends(get_complaint_service)
) -> ComplaintOut:
    return service.create(body)


@router.get("", response_model=ComplaintPage, responses={400: {"model": ValidationErrorBody}})
def list_complaints(
    category: Category | None = None,
    priority: Priority | None = None,
    status: Status | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintPage:
    return service.list_complaints(
        category=category, priority=priority, status=status, page=page, page_size=page_size
    )


@router.get("/{complaint_id}", response_model=ComplaintOut, responses={404: {"model": ErrorBody}})
def get_complaint(
    complaint_id: UUID, service: ComplaintService = Depends(get_complaint_service)
) -> ComplaintOut:
    return service.get(complaint_id)


@router.patch(
    "/{complaint_id}/status",
    response_model=ComplaintOut,
    responses={404: {"model": ErrorBody}, 409: {"model": ErrorBody}},
)
def change_status(
    complaint_id: UUID,
    body: StatusUpdate,
    service: ComplaintService = Depends(get_complaint_service),
) -> ComplaintOut:
    return service.change_status(complaint_id, body.status)
