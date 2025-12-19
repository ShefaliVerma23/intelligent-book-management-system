"""
Book recommendation API endpoints with ML-powered recommendations
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.models.base import get_db
from app.api.schemas import BookResponse, RecommendationRequest, RecommendationResponse
from app.services.auth_service import AuthService, security
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


class SummaryRequest(BaseModel):
    content: str


class SummaryResponse(BaseModel):
    summary: str
    content_length: int
    generated_at: datetime


@router.get("/", response_model=RecommendationResponse)
async def get_recommendations(
    genre: Optional[str] = Query(None, description="Filter by genre"),
    count: int = Query(5, ge=1, le=20, description="Number of recommendations"),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Get personalized book recommendations based on user preferences.
    
    Uses ML-based content filtering and collaborative filtering to find
    books that match user interests.
    """
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
    """
    Get popular books based on average ratings from reviews.
    
    No authentication required - public endpoint.
    """
    recommendation_service = RecommendationService(db)
    return await recommendation_service.get_popular_books(
        limit=limit,
        genre=genre
    )


@router.get("/similar/{book_id}", response_model=List[BookResponse])
async def get_similar_books(
    book_id: int,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """
    Get books similar to the specified book using ML content-based filtering.
    
    Uses TF-IDF vectorization on genre, author, and summary to find
    similar books based on content similarity.
    """
    recommendation_service = RecommendationService(db)
    similar_books = await recommendation_service.get_similar_books(
        book_id=book_id,
        limit=limit
    )
    
    if not similar_books:
        raise HTTPException(
            status_code=404, 
            detail="Book not found or no similar books available"
        )
    
    return similar_books


@router.get("/for-user/{user_id}", response_model=List[BookResponse])
async def get_recommendations_by_history(
    user_id: int,
    limit: int = Query(5, ge=1, le=20),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Get book recommendations based on user's review history.
    
    Uses collaborative filtering to find books in genres the user
    has rated highly.
    """
    auth_service = AuthService(db)
    await auth_service.get_current_active_user(credentials)
    
    recommendation_service = RecommendationService(db)
    return await recommendation_service.get_books_by_user_history(
        user_id=user_id,
        limit=limit
    )


@router.post("/generate-summary", response_model=SummaryResponse)
async def generate_content_summary(
    request: SummaryRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a summary for given book content using Llama3/OpenRouter AI.
    
    This endpoint uses the configured AI model (OpenRouter Llama3 or local)
    to generate a concise summary of the provided content.
    """
    auth_service = AuthService(db)
    await auth_service.get_current_active_user(credentials)
    
    recommendation_service = RecommendationService(db)
    summary = await recommendation_service.generate_content_summary(request.content)
    
    return SummaryResponse(
        summary=summary,
        content_length=len(request.content),
        generated_at=datetime.utcnow()
    )
