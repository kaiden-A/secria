"""Small connectivity check used by the README and local setup.

Run from the repo root:
    uv run --directory server python scripts/check_db.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text  # noqa: E402

from app.database import engine  # noqa: E402


def main() -> None:
    with engine.connect() as connection:
        connection.execute(text("select 1"))
        print("database: ok")
        try:
            revision = connection.execute(text("select version_num from public.alembic_version")).scalar()
            print(f"alembic revision: {revision}")
        except Exception:
            print("alembic revision: (alembic_version table not found)")


if __name__ == "__main__":
    main()
