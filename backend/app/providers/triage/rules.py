"""Deterministic keyword triage. Always available, never fails.
Includes common Roman-Urdu words (pani, bijli, sarak, kachra...)."""

import re

from app.domain import Category, Priority, TriageResult

# Order matters on ties: streetlights before electricity ("street light" contains "light").
KEYWORDS: dict[Category, tuple[str, ...]] = {
    Category.STREETLIGHTS: (
        "streetlight",
        "street light",
        "street-light",
        "lamp post",
        "pole light",
        "khamba",
        "lights are off",
        "light pole",
    ),
    Category.WATER: (
        "water",
        "pani",
        "paani",
        "pipe",
        "pipeline",
        "leak",
        "tanker",
        "supply",
        "tap",
        "water main",
    ),
    Category.SANITATION: (
        "sewer",
        "sewage",
        "gutter",
        "drain",
        "nala",
        "nullah",
        "garbage",
        "kachra",
        "trash",
        "waste",
        "smell",
        "manhole",
        "overflow",
    ),
    Category.ELECTRICITY: (
        "electricity",
        "bijli",
        "power",
        "load shedding",
        "loadshedding",
        "transformer",
        "wire",
        "voltage",
        "meter",
        "outage",
        "current",
    ),
    Category.ROADS: (
        "road",
        "sarak",
        "sadak",
        "pothole",
        "gadha",
        "gadda",
        "asphalt",
        "speed breaker",
        "footpath",
        "bridge",
        "traffic",
    ),
}

HIGH_WORDS = (
    "burst",
    "flood",
    "fire",
    "spark",
    "electrocut",
    "live wire",
    "naked wire",
    "danger",
    "urgent",
    "accident",
    "collapse",
    "injured",
    "child",
    "overflow",
    "entering",
    "since fajr",
    "whole night",
    "hospital",
    "school",
    "open manhole",
    "short circuit",
)
LOW_WORDS = (
    "suggest",
    "request",
    "minor",
    "paint",
    "faded",
    "cosmetic",
    "whenever possible",
    "not urgent",
    "small",
)


def _hits(text: str, words: tuple[str, ...]) -> int:
    return sum(1 for w in words if re.search(rf"\b{re.escape(w)}", text))


class RuleBasedTriage:
    name = "rules"

    def triage(self, text: str, location: str) -> TriageResult:
        lowered = text.lower()
        scores = {cat: _hits(lowered, words) for cat, words in KEYWORDS.items()}
        best = max(scores, key=lambda c: scores[c])  # first max wins on ties
        category = best if scores[best] > 0 else Category.OTHER

        if _hits(lowered, HIGH_WORDS):
            priority = Priority.HIGH
        elif _hits(lowered, LOW_WORDS):
            priority = Priority.LOW
        else:
            priority = Priority.NORMAL

        first_sentence = re.split(r"(?<=[.!?])\s", " ".join(text.split()), maxsplit=1)[0]
        summary = f"{category.value.title()} issue at {location}: {first_sentence}"
        if len(summary) > 140:
            summary = summary[:137].rstrip() + "..."

        confidence = 0.2 if category is Category.OTHER else min(0.9, 0.4 + 0.15 * scores[best])
        return TriageResult(
            category=category, priority=priority, summary=summary, confidence=round(confidence, 2)
        )
