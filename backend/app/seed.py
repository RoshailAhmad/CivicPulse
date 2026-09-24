"""Idempotent seed: `python -m app.seed`.

Each complaint gets a fixed id derived from its text (uuid5), so running the
seed twice finds the ids already present and inserts nothing new."""

import logging
import uuid
from typing import Any

from app.domain import Status
from app.logging_config import configure_logging
from app.providers.triage.rules import RuleBasedTriage
from app.repositories.complaints import ComplaintRepository
from app.repositories.db import get_sessionmaker

SEED_NAMESPACE = uuid.UUID("6f1c2b1e-9c8a-4d3e-8f7a-2b5c9e0d1a47")

# (text, location, contact)
COMPLAINTS: list[tuple[str, str, str | None]] = [
    (
        "Burst water main flooding Street 12 since fajr, water entering ground floors of houses.",
        "Street 12, G-9/2, Islamabad",
        "0300-1234567",
    ),
    (
        "Pani ki supply 3 din se band hai, tanker wala 4000 maang raha hai. Please restore supply.",
        "Satellite Town, Block C, Rawalpindi",
        None,
    ),
    (
        "Dirty water coming from tap, colour is brown and smells bad. Kids are getting sick.",
        "Dhok Kala Khan, Rawalpindi",
        "0312-9876543",
    ),
    (
        "Water pipeline leak near the mosque, road par pani khara hai for a week.",
        "Chaklala Scheme 3, Rawalpindi",
        None,
    ),
    ("Very low water pressure on upper floors, motor bhi nahi chalti.", "I-10/4, Islamabad", None),
    (
        "Main water pipe burst near school gate, children cannot enter, urgent please.",
        "F-8/1 near Islamabad Model School",
        "0333-5550001",
    ),
    (
        "Bijli 14 ghante se nahi hai, transformer se sparking ho rahi thi raat ko.",
        "Westridge 1, Rawalpindi",
        "0345-1112233",
    ),
    (
        "Live wire hanging low over the street after the storm, bachay wahan khelte hain. Danger!",
        "Street 5, Bahria Town Phase 4",
        None,
    ),
    (
        "Unannounced load shedding every evening from 6 to 10, our area schedule is not followed.",
        "Adiala Road, Rawalpindi",
        None,
    ),
    (
        "Electricity meter is showing wrong reading, bill aya 25000 for a two room house.",
        "Gulzar-e-Quaid, Rawalpindi",
        "0301-4445566",
    ),
    (
        "Voltage bohat low hai, fridge and AC are not working properly since last week.",
        "G-11/3, Islamabad",
        None,
    ),
    (
        "Transformer caught fire near the market, smoke is still coming, please send team.",
        "Commercial Market, Satellite Town",
        "0321-7778899",
    ),
    (
        "Gutter overflow on main road, ganda pani ghar ke andar aa raha hai.",
        "Dhoke Hassu, Rawalpindi",
        None,
    ),
    (
        "Garbage not collected for 10 days, kachra dher ban gaya hai, smell is unbearable.",
        "Sector G-7/1, Islamabad",
        None,
    ),
    (
        "Manhole cover missing on the street, a motorcyclist fell in last night.",
        "Street 22, F-10/2, Islamabad",
        "0302-6667788",
    ),
    (
        "Nala is blocked with plastic bags, before barish please clean it.",
        "Nullah Leh, near Kohati Bazar, Rawalpindi",
        None,
    ),
    (
        "Sewage water mixing with drinking water line in our street, many people have diarrhoea.",
        "Muslim Town, Rawalpindi",
        "0311-2223344",
    ),
    (
        "Request to place a proper garbage bin at the park entrance whenever possible.",
        "F-9 Park, Islamabad",
        None,
    ),
    (
        "Bohat bara pothole on the main road, two accidents already happened this week.",
        "Murree Road near Committee Chowk",
        None,
    ),
    (
        "Sarak toot gayi hai after the gas pipeline work, nobody repaired it.",
        "Street 3, PWD Colony, Islamabad",
        None,
    ),
    (
        "Speed breaker without any paint or sign, cars hit it at full speed at night.",
        "Kashmir Highway service road",
        None,
    ),
    (
        "Footpath tiles broken, elderly people are tripping while going to the mosque.",
        "Sector I-8/3, Islamabad",
        None,
    ),
    (
        "Road markings are faded near the roundabout, minor issue but please repaint.",
        "Zero Point interchange, Islamabad",
        None,
    ),
    (
        "Streetlights are off on the whole road for two weeks, chori ki warda'at barh gayi hai.",
        "Jinnah Avenue service lane, Blue Area",
        None,
    ),
    (
        "Street light pole is leaning and about to collapse on the parked cars.",
        "Street 9, G-10/1, Islamabad",
        "0346-9990011",
    ),
    (
        "Street lights stay on during the day, wasting bijli. Please fix the timer.",
        "Park Road, Chak Shahzad",
        None,
    ),
    (
        "Only one lamp post working in our lane, very dark for women coming from work.",
        "Lane 4, Scheme 2, Chaklala",
        None,
    ),
    (
        "Khamba light flickering all night, minor issue but it is annoying.",
        "Saddar, Bank Road, Rawalpindi",
        None,
    ),
    (
        "Stray dogs have become aggressive near the school, a child was bitten yesterday.",
        "Sector F-11/1, Islamabad",
        "0300-3334455",
    ),
    (
        "Illegal construction on the green belt, bulldozer is working at night.",
        "Sector E-11/3, Islamabad",
        None,
    ),
    (
        "Loud wedding music till 3 am on weekdays in the community hall.",
        "Askari 14, Rawalpindi",
        None,
    ),
    (
        "Suggest adding more benches and shade in the public park for old people.",
        "Lake View Park, Islamabad",
        None,
    ),
]

# Deterministic spread of statuses so the dashboard shows every state.
STATUS_CYCLE = [Status.OPEN, Status.OPEN, Status.IN_PROGRESS, Status.RESOLVED, Status.REJECTED]


def build_rows() -> list[dict[str, Any]]:
    rules = RuleBasedTriage()
    rows = []
    for index, (text, location, contact) in enumerate(COMPLAINTS):
        result = rules.triage(text, location)
        rows.append(
            {
                "id": uuid.uuid5(SEED_NAMESPACE, text),
                "text": text,
                "location": location,
                "reporter_contact": contact,
                "category": result.category,
                "priority": result.priority,
                "status": STATUS_CYCLE[index % len(STATUS_CYCLE)],
                "ai_summary": result.summary,
                "triaged_by": "rules",
                "triage_latency_ms": 0,
            }
        )
    return rows


def main() -> None:
    configure_logging()
    with get_sessionmaker()() as session:
        inserted = ComplaintRepository(session).seed(build_rows())
    logging.getLogger("civicpulse.seed").info(
        "seed complete", extra={"inserted": inserted, "total_seed_rows": len(COMPLAINTS)}
    )


if __name__ == "__main__":
    main()
