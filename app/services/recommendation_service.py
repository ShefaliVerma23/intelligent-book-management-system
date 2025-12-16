"""
Recommendation service for book suggestions and AI-powered recommendations
"""
import json
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func

from app.models.books import Book
from app.models.users import User
from app.models.reviews import Review
from app.api.schemas import RecommendationResponse, BookResponse
from app.services.llama_service import LlamaService


class RecommendationService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llama_service = LlamaService()
    
    async def get_recommendations_for_user(
        self, 
        user: User, 
        genre: Optional[str] = None, 
        count: int = 5
    ) -> RecommendationResponse:
        """Get personalized book recommendations for a user"""
        # Get user's preferred genres
        user_preferences = []
        if user.preferred_genres:
            try:
                user_preferences = json.loads(user.preferred_genres)
            except json.JSONDecodeError:
                user_preferences = [user.preferred_genres] if user.preferred_genres else []
        
        # If genre is specified, use it; otherwise use user preferences
        target_genre = genre if genre else (user_preferences[0] if user_preferences else None)
        
        # Get highly rated books, optionally filtered by genre
        books = await self._get_recommended_books(target_genre, count)
        
        # Generate AI reasoning for recommendations
        books_context = "\n".join([
            f"- {book.title} by {book.author} ({book.genre}, Rating: {book.average_rating:.1f}/5)"
            for book in books
        ])
        
        user_context = f"User preferences: {', '.join(user_preferences) if user_preferences else 'No specific preferences'}"
        if target_genre:
            user_context += f", Current filter: {target_genre}"
        
        reasoning = await self.llama_service.generate_recommendations(
            user_preferences=user_context,
            books_context=books_context
        )
        
        return RecommendationResponse(
            books=[BookResponse.from_orm(book) for book in books],
            reasoning=reasoning
        )
    
    async def get_popular_books(self, limit: int = 10, genre: Optional[str] = None) -> List[Book]:
        """Get popular books (highest rated)"""
        query = select(Book).where(Book.average_rating > 0)
        
        if genre:
            query = query.where(Book.genre.ilike(f"%{genre}%"))
        
        query = query.order_by(desc(Book.average_rating)).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def generate_content_summary(self, content: str) -> str:
        """Generate a summary for given content"""
        if not content or len(content.strip()) == 0:
            return "No content provided to summarize."
        
        return await self.llama_service.generate_summary(content)
    
    async def _get_recommended_books(self, genre: Optional[str], count: int) -> List[Book]:
        """Get books for recommendations based on rating and genre"""
        query = select(Book)
        
        if genre:
            query = query.where(Book.genre.ilike(f"%{genre}%"))
        
        # Order by average rating (descending) and then by total reviews (descending)
        # This prioritizes highly rated books that also have more reviews
        query = query.where(Book.average_rating > 0).order_by(
            desc(Book.average_rating),
            desc(Book.total_reviews)
        ).limit(count * 2)  # Get more books to have variety
        
        result = await self.db.execute(query)
        all_books = result.scalars().all()
        
        # Return the requested count, but ensure we have variety
        return all_books[:count] if all_books else []
    
    async def get_books_by_user_history(self, user_id: int, limit: int = 5) -> List[Book]:
        """Get book recommendations based on user's review history"""
        # Get genres of books the user has reviewed positively (rating >= 4)
        subquery = select(Review.book_id).where(
            Review.user_id == user_id,
            Review.rating >= 4.0
        ).subquery()
        
        # Find books in similar genres that the user hasn't reviewed
        query = select(Book).join(
            subquery, Book.id == subquery.c.book_id, isouter=True
        ).where(
            subquery.c.book_id.is_(None),  # User hasn't reviewed this book
            Book.average_rating >= 4.0  # Highly rated books
        ).order_by(desc(Book.average_rating)).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
