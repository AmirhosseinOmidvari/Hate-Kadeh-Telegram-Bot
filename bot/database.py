from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from bot.config import Config
import asyncio
from functools import partial

engine = create_engine(Config.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _db_task(fn, *args, **kwargs):
    db = SessionLocal()
    try:
        return fn(db, *args, **kwargs)
    finally:
        db.close()


async def run_db_task(fn, *args, **kwargs):
    """Run a synchronous DB task in the default threadpool.

    The provided `fn` should accept a SQLAlchemy `db` session as its first argument.
    """
    loop = asyncio.get_running_loop()
    task = partial(_db_task, fn, *args, **kwargs)
    return await loop.run_in_executor(None, task)