"""HTTP request/response models. These define the OpenAPI schema the
frontend's typed client is generated from."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain import Category, Priority, Status


class ComplaintCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    text: str = Field(min_length=10, max_length=2000)
    location: str = Field(min_length=3, max_length=200)
    reporter_contact: str | None = Field(default=None, max_length=200)


class ComplaintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    text: str
    location: str
    reporter_contact: str | None
    category: Category
    priority: Priority
    status: Status
    ai_summary: str | None
    triaged_by: str
    triage_latency_ms: int
    created_at: datetime
    updated_at: datetime


class ComplaintPage(BaseModel):
    items: list[ComplaintOut]
    total: int
    page: int
    page_size: int


class StatusUpdate(BaseModel):
    status: Status


class StatsOut(BaseModel):
    total: int
    by_category: dict[str, int]
    by_priority: dict[str, int]
    by_status: dict[str, int]


class TriageCacheStats(BaseModel):
    hits: int
    misses: int
    hit_rate: float


class ProvidersMeta(BaseModel):
    active_provider: str
    recent: list[dict[str, Any]]
    triage_cache: TriageCacheStats


class FieldError(BaseModel):
    field: str
    message: str


class ValidationErrorBody(BaseModel):
    detail: str
    errors: list[FieldError]


class ErrorBody(BaseModel):
    detail: str
