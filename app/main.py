"""
Main FastAPI application
"""
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.api.routes import books, users, reviews, auth, recommendations
from app.models.base import engine, Base, get_db
from app.services.llama_service import llama_service
from app.services.recommendation_service import RecommendationService
from app.services.cache_service import cache_service


# Schema for generate-summary endpoint
class GenerateSummaryRequest(BaseModel):
    content: str


class GenerateSummaryResponse(BaseModel):
    summary: str
    content_length: int
    generated_at: datetime


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("Starting up the application...")
    
    # Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")
    
    # Initialize AI model
    await llama_service.initialize()
    logger.info("AI service initialized")
    
    # Initialize Redis cache
    if settings.CACHE_ENABLED:
        await cache_service.connect()
        if cache_service.is_connected:
            logger.info("Redis cache initialized")
        else:
            logger.warning("Redis cache not available - running without cache")
    
    yield
    
    # Shutdown
    logger.info("Shutting down the application...")
    
    # Disconnect cache
    if cache_service.is_connected:
        await cache_service.disconnect()
    
    await engine.dispose()


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_hosts_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(books.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(reviews.router, prefix=settings.API_V1_STR)
app.include_router(recommendations.router, prefix=settings.API_V1_STR)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to the Intelligent Book Management System",
        "version": settings.VERSION,
        "docs": "/docs",
        "api": settings.API_V1_STR
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": settings.VERSION,
        "ai_model": "OpenRouter Llama3" if llama_service.use_api else "Local Model",
        "cache_enabled": cache_service.is_connected
    }


@app.get("/cache/stats")
async def get_cache_stats():
    """
    Get Redis cache statistics.
    Returns cache hit/miss counts and connection status.
    """
    stats = await cache_service.get_cache_stats()
    return stats


@app.post("/cache/clear")
async def clear_cache():
    """
    Clear all cache entries.
    Useful for forcing data refresh.
    """
    if not cache_service.is_connected:
        return {"status": "cache not connected", "cleared": 0}
    
    # Clear all cache patterns
    total = 0
    total += await cache_service.clear_pattern("rec:*")
    total += await cache_service.clear_pattern("popular:*")
    total += await cache_service.clear_pattern("summary:*")
    total += await cache_service.clear_pattern("similar:*")
    
    return {"status": "cleared", "keys_removed": total}


@app.post(f"{settings.API_V1_STR}/generate-summary", response_model=GenerateSummaryResponse)
async def generate_summary(
    request: GenerateSummaryRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a summary for given book content using Llama3/OpenRouter AI.
    
    This endpoint uses the configured AI model (OpenRouter Llama3 or local)
    to generate a concise summary of the provided content.
    
    As per requirement: POST /generate-summary endpoint.
    """
    if not request.content or len(request.content.strip()) == 0:
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    recommendation_service = RecommendationService(db)
    summary = await recommendation_service.generate_content_summary(request.content)
    
    return GenerateSummaryResponse(
        summary=summary,
        content_length=len(request.content),
        generated_at=datetime.utcnow()
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
