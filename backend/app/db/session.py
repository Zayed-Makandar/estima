import os
from functools import lru_cache
from typing import Iterator

from dotenv import load_dotenv
from sqlmodel import Session, SQLModel, create_engine


load_dotenv()


@lru_cache
def get_database_url() -> str:
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise RuntimeError("DATABASE_URL is not set")
    return db_url


@lru_cache
def get_engine():
    return create_engine(get_database_url(), echo=False, pool_pre_ping=True)


def init_db() -> None:
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    engine = get_engine()
    with Session(engine) as session:
        yield session

