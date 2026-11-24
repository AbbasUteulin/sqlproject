# Run ON PURPOSE to rebuild the schema and reload the original seed data:  py reset_db.py
# The web app never does this, so restarting the app never erases data.
from pathlib import Path
from sqlalchemy import text
from db import engine

here = Path(__file__).resolve().parent


def find(name):
    for folder in (here.parent, here):     
        if (folder / name).exists():
            return folder / name
    raise FileNotFoundError(name)


with engine.connect() as conn:
    for name in ("sql1.sql", "dummy_data.sql"):
        conn.execute(text(find(name).read_text(encoding="utf-8")))
    conn.commit()
print("Database rebuilt from sql1.sql and dummy_data.sql")