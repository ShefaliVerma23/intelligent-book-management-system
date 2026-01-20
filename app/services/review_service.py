"""
Review service for business logic

Provides CRUD operations for reviews with:
- Proper exception handling
- Structured logging
- Efficient database queries
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from loguru import logger

from app.models.reviews import Review
from app.models.books import Book
from app.api.schemas import ReviewCreate, ReviewUpdate
from app.services.llama_service import LlamaService


class ReviewServiceError(Exception):
    """Base exception for review service errors"""
    pass


class ReviewNotFoundError(ReviewServiceError):
    """Raised when a review is not found"""
    pass


class DuplicateReviewError(ReviewServiceError):
    """Raised when user tries to review a book twice"""
    pass


class ReviewService:
    """Service for review-related business logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llama_service = LlamaService()

    async def create_review(self, review_data: ReviewCreate, user_id: int) -> Review:
        """Create a new review.
        
        Args:
            review_data: The review data (book_id, rating, review_text)
            user_id: The authenticated user's ID (from JWT token)
            
        Returns:
            Created Review instance
            
        Raises:
            HTTPException: If book not found or duplicate review
        """
        logger.debug(
            "Creating review",
            extra={
                "book_id": review_data.book_id,
                "user_id": user_id,
                "rating": review_data.rating
            }
        )
        
        try:
            # First verify book exists
            book_query = select(Book).where(Book.id == review_data.book_id)
            book_result = await self.db.execute(book_query)
            book = book_result.scalar_one_or_none()
            
            if not book:
                logger.warning(
                    "Book not found for review",
                    extra={"book_id": review_data.book_id}
                )
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Book not found"
                )
            
            review = Review(
                book_id=review_data.book_id,
                user_id=user_id,
                rating=review_data.rating,
                review_text=review_data.review_text
            )
            self.db.add(review)
            await self.db.commit()
            await self.db.refresh(review)
            
            logger.info(
                "Review created successfully",
                extra={
                    "review_id": review.id,
                    "book_id": review.book_id,
                    "user_id": user_id,
                    "rating": review.rating
                }
            )
            return review
            
        except IntegrityError as e:
            await self.db.rollback()
            # Check if it's a unique constraint violation (duplicate review)
            if "uq_review_book_user" in str(e).lower() or "unique" in str(e).lower():
                logger.warning(
                    "Duplicate review attempt",
                    extra={"book_id": review_data.book_id, "user_id": user_id}
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="You have already reviewed this book"
                )
            logger.error(f"Integrity error creating review: {e}", exc_info=True)
            raise ReviewServiceError(f"Failed to create review: {str(e)}")
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error creating review: {e}", exc_info=True)
            raise ReviewServiceError(f"Database error: {str(e)}")
    
    async def get_user_review_for_book(self, user_id: int, book_id: int) -> Optional[Review]:
        """Check if a user has already reviewed a specific book.
        
        Args:
            user_id: The user's ID
            book_id: The book's ID
            
        Returns:
            Review if exists, None otherwise
        """
        logger.debug(
            "Checking for existing review",
            extra={"user_id": user_id, "book_id": book_id}
        )
        
        try:
            query = select(Review).where(
                Review.user_id == user_id,
                Review.book_id == book_id
            )
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except SQLAlchemyError as e:
            logger.error(f"Database error checking for review: {e}", exc_info=True)
            raise ReviewServiceError(f"Failed to check review: {str(e)}")

    async def create_review_for_book(
        self, 
        book_id: int, 
        review_data: dict, 
        user_id: int
    ) -> Optional[Review]:
        """Create a review for a specific book (legacy method).
        
        Args:
            book_id: The book to review
            review_data: Dictionary containing rating and review_text
            user_id: The authenticated user's ID
            
        Returns:
            Created Review or None if book not found
        """
        logger.debug(
            "Creating review for book",
            extra={"book_id": book_id, "user_id": user_id}
        )
        
        try:
            # First verify book exists
            book_query = select(Book).where(Book.id == book_id)
            book_result = await self.db.execute(book_query)
            book = book_result.scalar_one_or_none()
            
            if not book:
                logger.warning("Book not found", extra={"book_id": book_id})
                return None
            
            review = Review(
                book_id=book_id,
                user_id=user_id,
                rating=review_data['rating'],
                review_text=review_data.get('review_text')
            )
            
            self.db.add(review)
            await self.db.commit()
            await self.db.refresh(review)
            
            logger.info(
                "Review created for book",
                extra={"review_id": review.id, "book_id": book_id, "user_id": user_id}
            )
            return review
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error creating review: {e}", exc_info=True)
            raise ReviewServiceError(f"Failed to create review: {str(e)}")
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error creating review: {e}", exc_info=True)
            raise ReviewServiceError(f"Database error: {str(e)}")

    async def get_reviews(
        self, 
        skip: int = 0, 
        limit: int = 100,
        book_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> List[Review]:
        """Get reviews with optional filtering.
        
        Args:
            skip: Number of records to skip
            limit: Maximum records to return
            book_id: Filter by book ID
            user_id: Filter by user ID
            
        Returns:
            List of Review instances
        """
        logger.debug(
            "Fetching reviews",
            extra={"skip": skip, "limit": limit, "book_id": book_id, "user_id": user_id}
        )
        
        try:
            query = select(Review)
            
            if book_id:
                query = query.where(Review.book_id == book_id)
            
            if user_id:
                query = query.where(Review.user_id == user_id)
            
            # Add ordering for consistent pagination
            query = query.order_by(Review.created_at.desc()).offset(skip).limit(limit)
            
            result = await self.db.execute(query)
            reviews = list(result.scalars().all())
            
            logger.debug(f"Found {len(reviews)} reviews")
            return reviews
            
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching reviews: {e}", exc_info=True)
            raise ReviewServiceError(f"Failed to fetch reviews: {str(e)}")

    async def get_reviews_for_book(
        self, 
        book_id: int, 
        skip: int = 0, 
        limit: int = 100
    ) -> List[Review]:
        """Get all reviews for a specific book.
        
        Args:
            book_id: The book's ID
            skip: Number of records to skip
            limit: Maximum records to return
            
        Returns:
            List of Review instances for the book
        """
        return await self.get_reviews(skip=skip, limit=limit, book_id=book_id)

    async def get_review_by_id(self, review_id: int) -> Optional[Review]:
        """Get a review by ID.
        
        Args:
            review_id: The review's ID
            
        Returns:
            Review instance or None if not found
        """
        logger.debug(f"Fetching review by ID", extra={"review_id": review_id})
        
        try:
            query = select(Review).where(Review.id == review_id)
            result = await self.db.execute(query)
            review = result.scalar_one_or_none()
            
            if review:
                logger.debug(f"Found review", extra={"review_id": review_id})
            else:
                logger.debug(f"Review not found", extra={"review_id": review_id})
            
            return review
            
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching review: {e}", exc_info=True)
            raise ReviewServiceError(f"Failed to fetch review: {str(e)}")

    async def update_review(
        self, 
        review_id: int, 
        review_data: ReviewUpdate
    ) -> Optional[Review]:
        """Update a review.
        
        Args:
            review_id: The review's ID
            review_data: Update data
            
        Returns:
            Updated Review or None if not found
        """
        logger.debug(f"Updating review", extra={"review_id": review_id})
        
        try:
            review = await self.get_review_by_id(review_id)
            if not review:
                logger.debug(f"Review not found for update", extra={"review_id": review_id})
                return None
            
            update_data = review_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(review, field, value)
            
            await self.db.commit()
            await self.db.refresh(review)
            
            logger.info(
                "Review updated successfully",
                extra={"review_id": review_id, "updated_fields": list(update_data.keys())}
            )
            return review
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error updating review: {e}", exc_info=True)
            raise ReviewServiceError(f"Failed to update review: {str(e)}")

    async def delete_review(self, review_id: int) -> bool:
        """Delete a review.
        
        Args:
            review_id: The review's ID
            
        Returns:
            True if deleted, False if not found
        """
        logger.debug(f"Deleting review", extra={"review_id": review_id})
        
        try:
            review = await self.get_review_by_id(review_id)
            if not review:
                logger.debug(f"Review not found for deletion", extra={"review_id": review_id})
                return False
            
            await self.db.delete(review)
            await self.db.commit()
            
            logger.info(f"Review deleted successfully", extra={"review_id": review_id})
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error deleting review: {e}", exc_info=True)
            raise ReviewServiceError(f"Failed to delete review: {str(e)}")

    async def generate_review_summary(self, book_id: int) -> str:
        """Generate AI summary of reviews for a book.
        
        Args:
            book_id: The book's ID
            
        Returns:
            Text summary of the reviews including sentiment analysis
        """
        logger.debug(f"Generating review summary", extra={"book_id": book_id})
        
        try:
            reviews = await self.get_reviews(book_id=book_id, limit=1000)
            
            if not reviews:
                logger.debug(f"No reviews found for book", extra={"book_id": book_id})
                return "No reviews available for this book."
            
            # Create prompt with review contents
            review_texts = []
            for review in reviews:
                if review.review_text:
                    review_texts.append(f"Rating: {review.rating}/5 - {review.review_text}")
            
            if not review_texts:
                avg_rating = sum(r.rating for r in reviews) / len(reviews)
                return f"This book has {len(reviews)} ratings with an average of {avg_rating:.1f}/5 stars, but no written reviews."
            
            # Limit to first 10 reviews for summary
            reviews_content = "\n".join(review_texts[:10])
            
            logger.debug(
                f"Generating summary for reviews",
                extra={"book_id": book_id, "review_count": len(review_texts)}
            )
            
            # Get structured output with sentiment analysis
            result = await self.llama_service.generate_review_summary(reviews_content)
            
            if result.success:
                logger.info(
                    "Review summary generated",
                    extra={
                        "book_id": book_id,
                        "sentiment": result.sentiment,
                        "generation_time_ms": result.metadata.generation_time_ms if result.metadata else None
                    }
                )
            else:
                logger.warning(
                    "Review summary generation had issues",
                    extra={"book_id": book_id, "error": result.error}
                )
            
            # Include sentiment in response if available
            if result.sentiment:
                return f"{result.summary} (Overall sentiment: {result.sentiment})"
            return result.summary
            
        except Exception as e:
            logger.error(f"Error generating review summary: {e}", exc_info=True)
            return "Unable to generate review summary at this time."

    async def get_review_summary_for_book(self, book_id: int) -> str:
        """Get review summary for a book (alias method).
        
        Args:
            book_id: The book's ID
            
        Returns:
            Text summary of the reviews
        """
        return await self.generate_review_summary(book_id)
