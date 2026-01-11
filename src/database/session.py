# src/database/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from config.settings import settings
from src.database.models import Base


async_engine = create_async_engine(
    url=settings.DATABASE_URL,
    echo=True,
)

async_session_maker = async_sessionmaker(
    bind=async_engine,
    expire_on_commit=False
)


async def init_db():

    async with async_engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)