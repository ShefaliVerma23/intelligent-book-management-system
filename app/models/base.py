"""
Base database model and configuration
"""
import re
import ssl
from datetime import datetime
from typing import AsyncGenerator
from sqlalchemy import Column, Integer, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.config.settings import settings

Base = declarative_base()


def _create_engine():
    """
    Create the appropriate async database engine based on DATABASE_URL.
    
    Handles:
    - PostgreSQL URLs (postgresql:// or postgresql+asyncpg://)
    - SQLite URLs (sqlite:// or sqlite+aiosqlite://)
    - SSL configuration for cloud databases (Neon, etc.)
    - Removal of unsupported parameters (channel_binding, sslmode)
    """
    database_url = settings.DATABASE_URL
    
    # Check if SSL is required (for cloud databases like Neon) - do this before modifying URL
    use_ssl = "sslmode=require" in database_url or "neon" in database_url.lower()
    
    # Remove parameters not supported by asyncpg
    if "channel_binding" in database_url:
        database_url = re.sub(r'[&?]channel_binding=[^&]*', '', database_url)
    
    # Remove sslmode parameter (asyncpg uses 'ssl' argument instead)
    if "sslmode" in database_url:
        database_url = re.sub(r'[&?]sslmode=[^&]*', '', database_url)
    
    # Clean up URL (remove trailing ? or &)
    database_url = re.sub(r'[?&]$', '', database_url)
    
    # Handle PostgreSQL URLs
    if database_url.startswith("postgresql://") or database_url.startswith("postgresql+asyncpg://"):
        # Convert to async format if needed
        if database_url.startswith("postgresql://"):
            async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        else:
            async_database_url = database_url
        
        # Configure SSL for asyncpg
        connect_args = {}
        if use_ssl:
            # Create SSL context for secure connection
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            connect_args["ssl"] = ssl_context
        
        return create_async_engine(async_database_url, echo=False, connect_args=connect_args)
    
    # Handle SQLite URLs
    elif database_url.startswith("sqlite://") or database_url.startswith("sqlite+aiosqlite://"):
        # Convert to async format if needed
        if database_url.startswith("sqlite://"):
            async_database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
        else:
            async_database_url = database_url
        
        return create_async_engine(
            async_database_url, 
            echo=False,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    
    # Handle other database URLs (assume async-compatible)
    else:
        return create_async_engine(database_url, echo=False)


# Create the engine
engine = _create_engine()

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class BaseModel(Base):
    """Base model with common fields.
    
    All models inherit:
    - id: Primary key with index
    - created_at: Creation timestamp with index (for sorting/filtering)
    - updated_at: Last update timestamp
    """
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database dependency"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
