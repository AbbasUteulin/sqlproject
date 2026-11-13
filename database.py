from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

#The general connection URL IS: postgresql+psycopg2://user:pass@localhost:port/mydb
#default port: 5432
#default mydb name = postgres
#default user = postgres
SQLALCHEMY_DATABASE_URL = "postgresql+psycopg2://postgres:mysecretpassword@localhost:5431/postgres"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
)

with Session(engine) as session:
    with open("sql1.sql") as file:
        query = text(file.read())
        session.execute(query)
    session.commit()
