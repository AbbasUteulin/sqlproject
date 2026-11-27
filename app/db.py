import os
from sqlalchemy import create_engine

url = os.environ["DATABASE_URL"]
if url.startswith("postgres://"):
    url = url.replace("postgres://", "postgresql+psycopg2://", 1)
elif url.startswith("postgresql://"):
    url = url.replace("postgresql://", "postgresql+psycopg2://", 1)

# pool_pre_ping: test a pooled connection before using it. The cloud database (Neon) closes idle
# connections when it scales to zero, and this reconnects transparently instead of failing a request.
engine = create_engine(url, echo=False, pool_pre_ping=True)


def is_local_database():
    """True when DATABASE_URL points at this computer (the Docker container), not the deployed
    cloud database. resetdb.py and demo.py use it so the live data is never erased by accident."""
    return engine.url.host in (None, "", "localhost", "127.0.0.1", "::1")