# Run ON PURPOSE to rebuild the schema and reload the original seed data:  python resetdb.py
# The web app never does this, so restarting the app never erases data.
# demo.py imports reset_database() to start (and finish) from the seed data.
from pathlib import Path
from sqlalchemy import text
from db import engine

here = Path(__file__).resolve().parent


def find(name):
    for folder in (here.parent, here):
        if (folder / name).exists():
            return folder / name
    raise FileNotFoundError(name)


def reset_database():
    with engine.connect() as conn:
        for name in ("sql1.sql", "dummy_data.sql"):
            conn.execute(text(find(name).read_text(encoding="utf-8")))
        conn.commit()


if __name__ == "__main__":
    reset_database()
    print("Database rebuilt from sql1.sql and dummy_data.sql")
