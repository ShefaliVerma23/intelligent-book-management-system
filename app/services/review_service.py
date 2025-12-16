"""
Review service for business logic
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.reviews import Review
from app.models.books import Book
from app.api.schemas import ReviewCreate, ReviewUpdate
from app.services.llama_service import LlamaService


class ReviewService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llama_service = LlamaService()

    async def create_review(self, review_data: ReviewCreate) -> Review:
        """Create a new review"""
        review = Review(**review_data.dict())
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        
        # Update book rating statistics
        await self._update_book_stats(review.book_id)
        
        return review

    async def create_review_for_book(self, book_id: int, review_data: dict) -> Optional[Review]:
        """Create a review for a specific book"""
        # First verify book exists
        book_query = select(Book).where(Book.id == book_id)
        book_result = await self.db.execute(book_query)
        book = book_result.scalar_one_or_none()
        
        if not book:
            return None
        
        review = Review(
            book_id=book_id,
            user_id=review_data.get('user_id', 1),  # Default user for demo
            rating=review_data['rating'],
            title=review_data.get('title'),
            content=review_data.get('content')
        )
        
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)
        
        # Update book rating statistics
        await self._update_book_stats(book_id)
        
        return review

    async def get_reviews(
        self, 
        skip: int = 0, 
        limit: int = 100,
        book_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> List[Review]:
        """Get reviews with optional filtering"""
        query = select(Review)
        
        if book_id:
            query = query.where(Review.book_id == book_id)
        
        if user_id:
            query = query.where(Review.user_id == user_id)
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_reviews_for_book(self, book_id: int, skip: int = 0, limit: int = 100) -> List[Review]:
        """Get all reviews for a specific book"""
        return await self.get_reviews(skip=skip, limit=limit, book_id=book_id)

    async def get_review_by_id(self, review_id: int) -> Optional[Review]:
        """Get a review by ID"""
        query = select(Review).where(Review.id == review_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_review(self, review_id: int, review_data: ReviewUpdate) -> Optional[Review]:
        """Update a review"""
        review = await self.get_review_by_id(review_id)
        if not review:
            return None
        
        for field, value in review_data.dict(exclude_unset=True).items():
            setattr(review, field, value)
        
        await self.db.commit()
        await self.db.refresh(review)
        
        # Update book rating statistics
        await self._update_book_stats(review.book_id)
        
        return review

    async def delete_review(self, review_id: int) -> bool:
        """Delete a review"""
        review = await self.get_review_by_id(review_id)
        if not review:
            return False
        
        book_id = review.book_id
        await self.db.delete(review)
        await self.db.commit()
        
        # Update book rating statistics
        await self._update_book_stats(book_id)
        
        return True

    async def generate_review_summary(self, book_id: int) -> str:
        """Generate AI summary of reviews for a book"""
        reviews = await self.get_reviews(book_id=book_id, limit=1000)
        
        if not reviews:
            return "No reviews available for this book."
        
        # Create prompt with review contents
        review_texts = []
        for review in reviews:
            if review.content:
                review_texts.append(f"Rating: {review.rating}/5 - {review.content}")
        
        if not review_texts:
            return f"This book has {len(reviews)} ratings with an average of {sum(r.rating for r in reviews)/len(reviews):.1f}/5 stars, but no written reviews."
        
        prompt = f"Summarize these book reviews:\n" + "\n".join(review_texts[:10])  # Limit to first 10 reviews
        
        return await self.llama_service.generate_summary(prompt)

    async def get_review_summary_for_book(self, book_id: int) -> str:
        """Get review summary for a book"""
        return await self.generate_review_summary(book_id)

    async def _update_book_stats(self, book_id: int):
        """Update book rating statistics"""
        # Get all reviews for this book
        query = select(Review).where(Review.book_id == book_id)
        result = await self.db.execute(query)
        reviews = result.scalars().all()
        
        # Get the book
        book_query = select(Book).where(Book.id == book_id)
        book_result = await self.db.execute(book_query)
        book = book_result.scalar_one_or_none()
        
        if book:
            if reviews:
                book.total_reviews = len(reviews)
                book.average_rating = sum(review.rating for review in reviews) / len(reviews)
            else:
                book.total_reviews = 0
                book.average_rating = 0.0
            
            await self.db.commit()
