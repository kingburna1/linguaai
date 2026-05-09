from sqlalchemy.ext.asyncio import AsyncEngine
from app.db.base import Base
from app.db.session import engine

# Import ALL models here so SQLAlchemy knows about every table
from app.models import user, language, session, message, progress


async def init_db() -> None:
  
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ All database tables created successfully.")


async def drop_db() -> None:
    """
    DANGER: Drops ALL tables. Only use during development to reset the database.
    Never run this in production.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    print("⚠️  All tables dropped.")