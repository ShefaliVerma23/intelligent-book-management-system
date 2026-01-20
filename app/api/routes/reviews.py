"""
Review-related API endpoints

All mutating endpoints (POST/PUT/DELETE) require authentication.
Users can only modify their own reviews unless they are admins.

Exception Handling:
- Service exceptions are caught and converted to appropriate HTTP responses
- All errors are logged for debugging
- Ownership checks prevent unauthorized access
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.base import get_db
from app.api.schemas import ReviewCreate, ReviewUpdate, ReviewResponse
from app.services.review_service import ReviewService, ReviewServiceError
from app.services.auth_service import AuthService, security

router = APIRouter(prefix="/reviews", tags=["reviews"])


@router.post("/", response_model=ReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_review(
    review: ReviewCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Create a new review (requires authentication).
    
    The user_id is automatically set from the authenticated user.
    Users cannot submit multiple reviews for the same book.
    
    Returns:
        201: Review created successfully
        400: Already reviewed this book or invalid data
        401: Not authenticated
        404: Book not found
        422: Validation error
    """
    try:
        auth_service = AuthService(db)
        current_user = await auth_service.get_current_active_user(credentials)
        
        review_service = ReviewService(db)
        
        # Check if user already reviewed this book
        existing_review = await review_service.get_user_review_for_book(
            user_id=current_user.id,
            book_id=review.book_id
        )
        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this book. Use PUT to update your review."
            )
        
        created_review = await review_service.create_review(review, user_id=current_user.id)
        
        logger.info(
            f"Review created: user {current_user.id} reviewed book {review.book_id} "
            f"with rating {review.rating}"
        )
        return created_review
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except ReviewServiceError as e:
        logger.error(f"Failed to create review: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[ReviewResponse])
async def get_reviews(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    book_id: Optional[int] = Query(None, description="Filter by book ID"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    db: AsyncSession = Depends(get_db)
):
    """Get reviews with optional filtering (Public).
    
    Returns:
        200: List of reviews
        500: Server error
    """
    try:
        review_service = ReviewService(db)
        return await review_service.get_reviews(
            skip=skip, 
            limit=limit, 
            book_id=book_id, 
            user_id=user_id
        )
    except ReviewServiceError as e:
        logger.error(f"Failed to fetch reviews: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch reviews"
        )


@router.get("/{review_id}", response_model=ReviewResponse)
async def get_review(review_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific review by ID (Public).
    
    Returns:
        200: Review details
        404: Review not found
    """
    try:
        review_service = ReviewService(db)
        review = await review_service.get_review_by_id(review_id)
        
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review with ID {review_id} not found"
            )
        return review
        
    except ReviewServiceError as e:
        logger.error(f"Failed to fetch review {review_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch review"
        )


@router.put("/{review_id}", response_model=ReviewResponse)
async def update_review(
    review_id: int,
    review_update: ReviewUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Update a specific review (requires authentication).
    
    Users can only update their own reviews unless they are admins.
    
    Returns:
        200: Updated review
        401: Not authenticated
        403: Not authorized (not owner or admin)
        404: Review not found
        422: Validation error
    """
    try:
        auth_service = AuthService(db)
        current_user = await auth_service.get_current_active_user(credentials)
        
        review_service = ReviewService(db)
        review = await review_service.get_review_by_id(review_id)
        
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review with ID {review_id} not found"
            )
        
        # Check ownership: only review owner or admin can update
        if review.user_id != current_user.id and not current_user.is_admin:
            logger.warning(
                f"Unauthorized update attempt: user {current_user.id} "
                f"tried to update review {review_id} owned by user {review.user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update your own reviews"
            )
        
        updated_review = await review_service.update_review(review_id, review_update)
        
        logger.info(f"Review updated: {review_id} by user {current_user.id}")
        return updated_review
        
    except HTTPException:
        raise
    except ReviewServiceError as e:
        logger.error(f"Failed to update review {review_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{review_id}", status_code=status.HTTP_200_OK)
async def delete_review(
    review_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Delete a specific review (requires authentication).
    
    Users can only delete their own reviews unless they are admins.
    
    Returns:
        200: Review deleted successfully
        401: Not authenticated
        403: Not authorized (not owner or admin)
        404: Review not found
    """
    try:
        auth_service = AuthService(db)
        current_user = await auth_service.get_current_active_user(credentials)
        
        review_service = ReviewService(db)
        review = await review_service.get_review_by_id(review_id)
        
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review with ID {review_id} not found"
            )
        
        # Check ownership: only review owner or admin can delete
        if review.user_id != current_user.id and not current_user.is_admin:
            logger.warning(
                f"Unauthorized delete attempt: user {current_user.id} "
                f"tried to delete review {review_id} owned by user {review.user_id}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own reviews"
            )
        
        await review_service.delete_review(review_id)
        
        logger.info(f"Review deleted: {review_id} by user {current_user.id}")
        return {"message": "Review deleted successfully", "review_id": review_id}
        
    except HTTPException:
        raise
    except ReviewServiceError as e:
        logger.error(f"Failed to delete review {review_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete review"
        )


@router.get("/book/{book_id}/summary")
async def get_book_review_summary(
    book_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get AI-generated summary of reviews for a book (Public).
    
    Returns aggregated sentiment and key themes from reviews.
    
    Returns:
        200: Review summary with sentiment
        500: Summary generation failed
    """
    try:
        review_service = ReviewService(db)
        summary = await review_service.generate_review_summary(book_id)
        
        return {
            "book_id": book_id,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Failed to generate review summary for book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate review summary"
        )
