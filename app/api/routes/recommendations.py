"""
Book recommendation API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.api.schemas import BookResponse, RecommendationRequest, RecommendationResponse
from app.services.auth_service import AuthService, security
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/", response_model=RecommendationResponse)
async def get_recommendations(
    genre: Optional[str] = Query(None, description="Filter by genre"),
    count: int = Query(5, ge=1, le=20, description="Number of recommendations"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get book recommendations based on user preferences"""
    auth_service = AuthService(db)
    current_user = await auth_service.get_current_active_user(credentials)
    
    recommendation_service = RecommendationService(db)
    return await recommendation_service.get_recommendations_for_user(
        user=current_user,
        genre=genre,
        count=count
    )


@router.get("/popular", response_model=List[BookResponse])
async def get_popular_books(
    limit: int = Query(10, ge=1, le=50),
    genre: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get popular books (highest rated)"""
    recommendation_service = RecommendationService(db)
    return await recommendation_service.get_popular_books(
        limit=limit,
        genre=genre
    )


@router.post("/generate-summary", response_model=dict)
async def generate_content_summary(
    book_content: dict,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Generate a summary for given book content"""
    auth_service = AuthService(db)
    await auth_service.get_current_active_user(credentials)  # Ensure authenticated
    
    recommendation_service = RecommendationService(db)
    summary = await recommendation_service.generate_content_summary(book_content.get("content", ""))
    
    return {
        "summary": summary,
        "content_length": len(book_content.get("content", "")),
        "generated_at": "2024-01-01T00:00:00Z"  # This would be current timestamp in real implementation
    }
