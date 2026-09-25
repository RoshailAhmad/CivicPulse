"""Writes the OpenAPI schema the frontend's typed client is generated from.

python -m app.export_openapi            (from backend/)
cd ../frontend && npm run gen:api
"""

import json
import os
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://unused:unused@unused/unused")

from app.main import app  # noqa: E402


def main() -> None:
    target = Path(__file__).resolve().parents[1] / "openapi.json"
    target.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
