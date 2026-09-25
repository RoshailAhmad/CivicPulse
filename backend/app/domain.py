"""Core domain vocabulary shared by every layer: enums and the triage result.

The same Pydantic model validates LLM output that validates HTTP input,
so a model that invents a category is rejected exactly like a bad request.
"""

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Category(StrEnum):
    WATER = "water"
    ELECTRICITY = "electricity"
    SANITATION = "sanitation"
    ROADS = "roads"
    STREETLIGHTS = "streetlights"
    OTHER = "other"


class Priority(StrEnum):
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class Status(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


TRIAGED_BY_VALUES = ("llm:groq", "llm:ollama", "rules", "rules:fallback", "simulated")
FALLBACK_PROVIDER = "rules:fallback"


class TriageResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category: Category
    priority: Priority
    summary: str = Field(min_length=1, max_length=140)
    confidence: float = Field(ge=0.0, le=1.0)

    @field_validator("category", "priority", mode="before")
    @classmethod
    def _lowercase(cls, value: Any) -> Any:
        # "Water" is accepted as "water"; "flood" is still rejected by the enum.
        return value.strip().lower() if isinstance(value, str) else value

    @field_validator("summary", mode="before")
    @classmethod
    def _one_line(cls, value: Any) -> Any:
        return " ".join(value.split()) if isinstance(value, str) else value
