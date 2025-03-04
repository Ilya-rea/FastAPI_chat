"""
Файл содержит настройки для подключения к базе данных PostgreSQL с использованием SQLAlchemy.
Определяет асинхронный движок и сессию для работы с базой данных.
"""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from .models import Base

DATABASE_URL = "postgresql+asyncpg://postgres:1234@db:5432/fastapi_messenger"

engine = create_async_engine(DATABASE_URL, echo=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)