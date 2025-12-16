"""
Review-related API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.api.schemas import ReviewCreate, ReviewUpdate, ReviewResponse
from app.services.review_service import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/", response_model=ReviewResponse)
async def create_review(
    review: ReviewCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new review"""
    review_service = ReviewService(db)
    return await review_service.create_review(review)


@router.get("/", response_model=List[ReviewResponse])
async def get_reviews(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    book_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get reviews with optional filtering"""
    review_service = ReviewService(db)
    return await review_service.get_reviews(
        skip=skip, 
        limit=limit, 
        book_id=book_id, 
        user_id=user_id
    )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific review by ID"""
    review_service = ReviewService(db)
    review = await review_service.get_review_by_id(review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    review_update: ReviewUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a specific review"""
    review_service = ReviewService(db)
    review = await review_service.update_review(review_id, review_update)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return review


@router.delete("/{review_id}")
async def delete_review(review_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a specific review"""
    review_service = ReviewService(db)
    success = await review_service.delete_review(review_id)
    if not success:
        raise HTTPException(status_code=404, detail="Review not found")
    return {"message": "Review deleted successfully"}


@router.get("/book/{book_id}/summary")
async def get_book_review_summary(
    book_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get AI-generated summary of reviews for a book"""
    review_service = ReviewService(db)
    summary = await review_service.generate_review_summary(book_id)
    return {"book_id": book_id, "summary": summary}
