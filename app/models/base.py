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

# Convert DATABASE_URL to async format
database_url = settings.DATABASE_URL

# Remove parameters not supported by asyncpg
if "channel_binding" in database_url:
    database_url = re.sub(r'[&?]channel_binding=[^&]*', '', database_url)

# Check if SSL is required (for cloud databases like Neon)
use_ssl = "sslmode=require" in database_url or "neon" in database_url

# Remove sslmode parameter (asyncpg uses 'ssl' instead)
if "sslmode" in database_url:
    database_url = re.sub(r'[&?]sslmode=[^&]*', '', database_url)

# Clean up URL (remove trailing ? or &)
database_url = re.sub(r'[?&]$', '', database_url)

if database_url.startswith("postgresql://"):
    async_database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")
    
    # Configure SSL for asyncpg
    connect_args = {}
    if use_ssl:
        # Create SSL context for secure connection
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        connect_args["ssl"] = ssl_context
    
    engine = create_async_engine(async_database_url, echo=False, connect_args=connect_args)
elif database_url.startswith("sqlite://"):
    async_database_url = database_url.replace("sqlite://", "sqlite+aiosqlite://")
    engine = create_async_engine(
        async_database_url, 
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
else:
    async_database_url = database_url
    engine = create_async_engine(async_database_url, echo=False)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class BaseModel(Base):
    """Base model with common fields"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database dependency"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
