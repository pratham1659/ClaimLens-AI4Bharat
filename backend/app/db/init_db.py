# backend/app/db/init_db.py
"""
Database initialization and migration utilities.
"""

import logging
from sqlalchemy import text
from app.db.session import engine
from app.models.base import Base

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """
    Initialize database with required extensions and tables.
    """
    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        logger.info("pgvector extension enabled")

        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")


async def drop_db() -> None:
    """
    Drop all database tables. Use with caution!
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        logger.warning("All database tables dropped")
