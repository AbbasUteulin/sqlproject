# Run ON PURPOSE to rebuild the schema and reload the original seed data:  python resetdb.py
# The web app never does this, so restarting the app never erases data.
# demo.py imports reset_database() to start (and finish) from the seed data.
#
# Against the deployed (cloud) database it asks for confirmation first, because it erases
# everything graders or users have entered and puts the seed data back.
import sys
from pathlib import Path
from sqlalchemy import text
from db import engine, is_local_database

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
    if not is_local_database():
        answer = input(f"DATABASE_URL points at {engine.url.host}, not this computer.\n"
                       "This ERASES all its data and reloads the seed data. Type yes to continue: ")
        if answer.strip().lower() != "yes":
            sys.exit("Cancelled; nothing was changed.")
    reset_database()
    print("Database rebuilt from sql1.sql and dummy_data.sql")
