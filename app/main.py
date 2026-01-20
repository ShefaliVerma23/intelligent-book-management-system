"""
Intelligent Book Management System - Main Application

Reliability Features:
- Graceful startup with proper error handling
- Health checks for all services
- Request tracing with unique IDs
- Comprehensive exception handling
- Clean shutdown

Startup Flow:
1. Validate configuration (fails fast if invalid)
2. Create database tables
3. Initialize AI service (non-blocking, has fallback)
4. Connect to Redis cache (optional, continues without)
5. Start accepting requests
"""
import sys
import time
import uuid
from datetime import datetime
from contextlib import asynccontextmanager
from typing import Callable

from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger

from app.config.settings import settings
from app.api.routes import books, users, reviews, auth, recommendations
from app.api.schemas import GenerateSummaryRequest
from app.models.base import engine, Base, get_db
from app.services.llama_service import llama_service
from app.services.recommendation_service import RecommendationService
from app.services.cache_service import cache_service
from app.services.auth_service import AuthService, security
from fastapi.security import HTTPAuthorizationCredentials


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Remove default handler
logger.remove()

# Add structured logging
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{extra[request_id]}</cyan> | <level>{message}</level>",
    level=settings.LOG_LEVEL,
    colorize=True,
    filter=lambda record: "request_id" in record["extra"]
)

# Fallback for logs without request_id
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level=settings.LOG_LEVEL,
    colorize=True,
    filter=lambda record: "request_id" not in record["extra"]
)


# =============================================================================
# STARTUP STATE TRACKING
# =============================================================================

class StartupState:
    """Track initialization state for health checks"""
    database_ready: bool = False
    ai_ready: bool = False
    ai_mode: str = "unknown"
    cache_ready: bool = False
    startup_time: float = 0
    startup_errors: list = []


startup_state = StartupState()


# =============================================================================
# EXCEPTION HANDLERS
# =============================================================================

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors with detailed messages"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    errors = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        errors.append({
            "field": field,
            "message": error["msg"],
            "type": error["type"]
        })
    
    logger.warning(
        f"Validation error: {len(errors)} fields invalid",
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Validation error",
            "errors": errors,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.warning(
        f"HTTP {exc.status_code}: {exc.detail}",
        request_id=request_id
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Database error: {type(exc).__name__}",
        request_id=request_id,
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Database error occurred",
            "error_code": "DATABASE_ERROR",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    request_id = getattr(request.state, "request_id", "unknown")
    
    logger.error(
        f"Unexpected error: {type(exc).__name__}: {exc}",
        request_id=request_id,
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "An unexpected error occurred",
            "error_code": "INTERNAL_ERROR",
            "request_id": request_id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )


# =============================================================================
# REQUEST MIDDLEWARE
# =============================================================================

async def request_middleware(request: Request, call_next: Callable):
    """Add request ID and timing to all requests"""
    # Generate unique request ID
    request_id = str(uuid.uuid4())[:8]
    request.state.request_id = request_id
    
    start_time = time.time()
    
    # Bind request_id to logger context
    with logger.contextualize(request_id=request_id):
        logger.info(f"{request.method} {request.url.path}")
        
        try:
            response = await call_next(request)
            
            # Log response
            process_time = (time.time() - start_time) * 1000
            logger.info(
                f"{request.method} {request.url.path} -> {response.status_code} ({process_time:.1f}ms)"
            )
            
            # Add headers for tracing
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = f"{process_time:.2f}ms"
            
            return response
            
        except Exception as e:
            process_time = (time.time() - start_time) * 1000
            logger.error(
                f"{request.method} {request.url.path} -> ERROR ({process_time:.1f}ms): {e}"
            )
            raise


# =============================================================================
# LIFESPAN MANAGEMENT
# =============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown with proper error handling"""
    start_time = time.time()
    
    logger.info("=" * 60)
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION}")
    logger.info("=" * 60)
    
    # Log configuration
    logger.info(f"Database: {settings.DATABASE_URL[:30]}...")
    logger.info(f"AI Mode: {'OpenRouter' if settings.is_ai_available() else 'Fallback'}")
    logger.info(f"Caching: {'Enabled' if settings.is_cache_available() else 'Disabled'}")
    
    try:
        # Step 1: Initialize database (required)
        logger.info("Initializing database...")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            startup_state.database_ready = True
            logger.info("Database ready")
        except Exception as e:
            startup_state.startup_errors.append(f"Database: {e}")
            logger.error(f"Database initialization failed: {e}")
            raise  # Database is required
        
        # Step 2: Initialize AI service (optional, has fallback)
        logger.info("Initializing AI service...")
        try:
            await llama_service.initialize()
            startup_state.ai_ready = llama_service._initialized
            startup_state.ai_mode = "openrouter" if llama_service.use_openrouter else "fallback"
            
            if startup_state.ai_ready:
                logger.info(f"AI service ready ({startup_state.ai_mode} mode)")
            else:
                logger.warning("AI service using fallback mode")
        except Exception as e:
            startup_state.startup_errors.append(f"AI Service: {e}")
            logger.warning(f"AI service init error (using fallback): {e}")
            startup_state.ai_mode = "fallback"
        
        # Step 3: Connect to cache (optional)
        if settings.is_cache_available():
            logger.info("Connecting to cache...")
            try:
                await cache_service.connect()
                startup_state.cache_ready = cache_service.is_connected
                
                if startup_state.cache_ready:
                    logger.info("Cache connected")
                else:
                    logger.warning("Cache connection failed - running without cache")
            except Exception as e:
                startup_state.startup_errors.append(f"Cache: {e}")
                logger.warning(f"Cache error (continuing without): {e}")
        else:
            logger.info("Caching disabled by configuration")
        
        # Startup complete
        startup_state.startup_time = time.time() - start_time
        
        logger.info("=" * 60)
        logger.info(f"Startup complete in {startup_state.startup_time:.2f}s")
        logger.info(f"  Database: {'OK' if startup_state.database_ready else 'FAILED'}")
        logger.info(f"  AI:       {startup_state.ai_mode}")
        logger.info(f"  Cache:    {'OK' if startup_state.cache_ready else 'OFF'}")
        logger.info("=" * 60)
        
        yield
        
    except Exception as e:
        logger.error(f"Startup failed: {e}", exc_info=True)
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down...")
        
        if cache_service.is_connected:
            try:
                await cache_service.disconnect()
                logger.info("Cache disconnected")
            except Exception as e:
                logger.warning(f"Cache disconnect error: {e}")
        
        try:
            await engine.dispose()
            logger.info("Database connections closed")
        except Exception as e:
            logger.warning(f"Database dispose error: {e}")
        
        logger.info("Shutdown complete")


# =============================================================================
# FASTAPI APPLICATION
# =============================================================================

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Middleware
app.middleware("http")(request_middleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.get_allowed_hosts_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(books.router, prefix=settings.API_V1_STR)
app.include_router(users.router, prefix=settings.API_V1_STR)
app.include_router(reviews.router, prefix=settings.API_V1_STR)
app.include_router(recommendations.router, prefix=settings.API_V1_STR)


# =============================================================================
# HEALTH AND STATUS ENDPOINTS
# =============================================================================

@app.get("/", tags=["status"])
async def root():
    """API information"""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health",
        "api": settings.API_V1_STR
    }


@app.get("/health", tags=["status"])
async def health_check():
    """
    Health check endpoint.
    
    Returns detailed status of all services.
    Use this for monitoring and load balancer health checks.
    """
    is_healthy = startup_state.database_ready
    
    return {
        "status": "healthy" if is_healthy else "degraded",
        "version": settings.VERSION,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": time.time() - startup_state.startup_time if startup_state.startup_time > 0 else 0,
        "services": {
            "database": {
                "status": "ok" if startup_state.database_ready else "error",
            },
            "ai": {
                "status": "ok" if startup_state.ai_ready else "degraded",
                "mode": startup_state.ai_mode
            },
            "cache": {
                "status": "ok" if startup_state.cache_ready else "disabled",
                "enabled": settings.is_cache_available()
            }
        },
        "errors": startup_state.startup_errors if startup_state.startup_errors else None
    }


@app.get("/ready", tags=["status"])
async def readiness_check():
    """
    Readiness probe for Kubernetes/Docker.
    
    Returns 200 if ready to accept traffic, 503 otherwise.
    """
    if not startup_state.database_ready:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"ready": False, "reason": "Database not ready"}
        )
    
    return {"ready": True}


# =============================================================================
# CACHE MANAGEMENT
# =============================================================================

@app.get("/cache/stats", tags=["cache"])
async def get_cache_stats():
    """Get cache statistics"""
    if not cache_service.is_connected:
        return {"status": "disconnected"}
    
    return await cache_service.get_cache_stats()


@app.post("/cache/clear", tags=["cache"])
async def clear_cache(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Clear cache (admin only)"""
    auth_service = AuthService(db)
    await auth_service.require_admin(credentials)
    
    if not cache_service.is_connected:
        return {"status": "disconnected", "cleared": 0}
    
    total = 0
    for pattern in ["rec:*", "popular:*", "summary:*", "similar:*"]:
        total += await cache_service.clear_pattern(pattern)
    
    logger.info(f"Cache cleared: {total} keys")
    return {"status": "cleared", "keys_removed": total}


# =============================================================================
# AI SUMMARY ENDPOINT
# =============================================================================

@app.post(f"{settings.API_V1_STR}/generate-summary", tags=["ai"])
async def generate_summary(
    request: GenerateSummaryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate AI summary (requires authentication).
    
    Uses OpenRouter API or fallback mode based on configuration.
    """
    auth_service = AuthService(db)
    current_user = await auth_service.get_current_active_user(credentials)
    
    logger.info(f"Summary requested by user {current_user.id}")
    
    try:
        recommendation_service = RecommendationService(db)
        summary = await recommendation_service.generate_content_summary(request.content)
        
        return {
            "summary": summary,
            "content_length": len(request.content),
            "generated_at": datetime.utcnow().isoformat(),
            "ai_mode": startup_state.ai_mode
        }
        
    except Exception as e:
        logger.error(f"Summary generation failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary"
        )


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True
    )
