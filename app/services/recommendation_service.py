"""
Recommendation service for book suggestions and AI-powered recommendations
Uses ML-based genre matching and collaborative filtering
With Redis caching for improved performance (AWS ElastiCache compatible)
"""
import json
import hashlib
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
from loguru import logger

from app.models.books import Book
from app.models.users import User
from app.models.reviews import Review
from app.api.schemas import RecommendationResponse, BookResponse
from app.services.llama_service import LlamaService
from app.services.cache_service import cache_service


class RecommendationService:
    """
    ML-powered recommendation service that uses:
    1. Content-based filtering (TF-IDF on genre, author, summary)
    2. Collaborative filtering (based on user reviews)
    3. AI-generated reasoning (via Llama/OpenRouter)
    4. Redis caching for improved performance (AWS ElastiCache compatible)
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llama_service = LlamaService()
        self.vectorizer = TfidfVectorizer(stop_words='english')
    
    def _book_to_dict(self, book: Book) -> dict:
        """Convert Book model to dictionary for caching"""
        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "genre": book.genre,
            "year_published": book.year_published,
            "summary": book.summary,
            "created_at": str(book.created_at) if book.created_at else None,
            "updated_at": str(book.updated_at) if book.updated_at else None
        }
    
    def _dict_to_book(self, data: dict) -> Book:
        """Convert dictionary to Book model from cache"""
        book = Book(
            id=data.get("id"),
            title=data.get("title"),
            author=data.get("author"),
            genre=data.get("genre"),
            year_published=data.get("year_published"),
            summary=data.get("summary")
        )
        return book
    
    async def get_recommendations_for_user(
        self, 
        user: User, 
        genre: Optional[str] = None, 
        count: int = 5
    ) -> RecommendationResponse:
        """Get personalized book recommendations for a user using ML"""
        # Get user's preferred genres
        user_preferences = []
        if user.preferred_genres:
            try:
                user_preferences = json.loads(user.preferred_genres)
            except json.JSONDecodeError:
                user_preferences = [g.strip() for g in user.preferred_genres.split(",")]
        
        # If genre is specified, use it; otherwise use user preferences
        target_genre = genre if genre else (user_preferences[0] if user_preferences else None)
        
        # Get books with average ratings calculated from reviews
        books_with_ratings = await self._get_books_with_ratings(target_genre, count)
        
        # Generate AI reasoning for recommendations
        books_context = "\n".join([
            f"- {book['book'].title} by {book['book'].author} ({book['book'].genre or 'General'}, Avg Rating: {book['avg_rating']:.1f}/5)"
            for book in books_with_ratings
        ])
        
        user_context = f"User preferences: {', '.join(user_preferences) if user_preferences else 'No specific preferences'}"
        if target_genre:
            user_context += f", Current filter: {target_genre}"
        
        reasoning = await self.llama_service.generate_recommendations(
            user_preferences=user_context,
            books_context=books_context
        )
        
        # Extract just the books for response
        books = [item['book'] for item in books_with_ratings]
        
        return RecommendationResponse(
            books=[BookResponse.model_validate(book) for book in books],
            reasoning=reasoning
        )
    
    async def get_popular_books(self, limit: int = 10, genre: Optional[str] = None) -> List[Book]:
        """Get popular books based on average ratings from reviews (with caching)"""
        
        # Try to get from cache first
        cached = await cache_service.get_popular_books(genre, limit)
        if cached:
            logger.info(f"Cache HIT for popular books (genre={genre}, limit={limit})")
            # Reconstruct Book objects from cached data
            return [self._dict_to_book(b) for b in cached]
        
        # Calculate average rating for each book from reviews
        subquery = select(
            Review.book_id,
            func.avg(Review.rating).label('avg_rating'),
            func.count(Review.id).label('review_count')
        ).group_by(Review.book_id).subquery()
        
        query = select(Book).join(
            subquery, Book.id == subquery.c.book_id
        )
        
        if genre:
            query = query.where(Book.genre.ilike(f"%{genre}%"))
        
        query = query.order_by(desc(subquery.c.avg_rating)).limit(limit)
        result = await self.db.execute(query)
        books = result.scalars().all()
        
        # Cache the result
        books_data = [self._book_to_dict(b) for b in books]
        await cache_service.set_popular_books(books_data, genre, limit)
        logger.info(f"Cache SET for popular books (genre={genre}, limit={limit})")
        
        return books
    
    async def generate_content_summary(self, content: str) -> str:
        """Generate a summary for given content using Llama/OpenRouter (with caching)"""
        if not content or len(content.strip()) == 0:
            return "No content provided to summarize."
        
        # Create a hash of the content for caching
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Try to get from cache first
        cached = await cache_service.get_ai_summary(content_hash)
        if cached:
            logger.info(f"Cache HIT for AI summary (hash={content_hash[:8]}...)")
            return cached
        
        # Generate summary using AI
        summary = await self.llama_service.generate_summary(content)
        
        # Cache the result
        await cache_service.set_ai_summary(content_hash, summary)
        logger.info(f"Cache SET for AI summary (hash={content_hash[:8]}...)")
        
        return summary
    
    async def _get_books_with_ratings(self, genre: Optional[str], count: int) -> List[Dict]:
        """Get books with calculated average ratings from reviews"""
        # Calculate average rating for each book
        subquery = select(
            Review.book_id,
            func.avg(Review.rating).label('avg_rating'),
            func.count(Review.id).label('review_count')
        ).group_by(Review.book_id).subquery()
        
        query = select(
            Book,
            func.coalesce(subquery.c.avg_rating, 0.0).label('avg_rating'),
            func.coalesce(subquery.c.review_count, 0).label('review_count')
        ).outerjoin(
            subquery, Book.id == subquery.c.book_id
        )
        
        if genre:
            query = query.where(Book.genre.ilike(f"%{genre}%"))
        
        # Order by average rating and review count
        query = query.order_by(
            desc(func.coalesce(subquery.c.avg_rating, 0.0)),
            desc(func.coalesce(subquery.c.review_count, 0))
        ).limit(count * 2)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        # Convert to list of dicts
        books_with_ratings = [
            {
                'book': row[0],
                'avg_rating': float(row[1]),
                'review_count': int(row[2])
            }
            for row in rows
        ]
        
        return books_with_ratings[:count]
    
    async def get_similar_books(self, book_id: int, limit: int = 5) -> List[Book]:
        """
        ML-based content similarity using TF-IDF (with caching)
        Finds books similar to the given book based on genre, author, and summary
        """
        # Try to get from cache first
        cached = await cache_service.get_similar_books(book_id, limit)
        if cached:
            logger.info(f"Cache HIT for similar books (book_id={book_id}, limit={limit})")
            return [self._dict_to_book(b) for b in cached]
        
        # Get all books
        result = await self.db.execute(select(Book))
        all_books = result.scalars().all()
        
        if not all_books:
            return []
        
        # Find the target book
        target_book = None
        for book in all_books:
            if book.id == book_id:
                target_book = book
                break
        
        if not target_book:
            return []
        
        # Create content strings for TF-IDF
        def create_content(book: Book) -> str:
            parts = []
            if book.genre:
                parts.append(book.genre)
            if book.author:
                parts.append(book.author)
            if book.summary:
                parts.append(book.summary)
            return " ".join(parts)
        
        contents = [create_content(book) for book in all_books]
        
        # Handle case where all contents are empty
        if all(not c.strip() for c in contents):
            # Fallback: return books in same genre
            similar_books = [b for b in all_books if b.id != book_id and b.genre == target_book.genre][:limit]
        else:
            # Create TF-IDF matrix
            try:
                tfidf_matrix = self.vectorizer.fit_transform(contents)
                
                # Find index of target book
                target_idx = all_books.index(target_book)
                
                # Calculate cosine similarity
                similarities = cosine_similarity(tfidf_matrix[target_idx:target_idx+1], tfidf_matrix)[0]
                
                # Get indices of most similar books (excluding the book itself)
                similar_indices = np.argsort(similarities)[::-1]
                
                similar_books = []
                for idx in similar_indices:
                    if all_books[idx].id != book_id and len(similar_books) < limit:
                        similar_books.append(all_books[idx])
            except Exception:
                # Fallback: return books in same genre
                similar_books = [b for b in all_books if b.id != book_id and b.genre == target_book.genre][:limit]
        
        # Cache the result
        books_data = [self._book_to_dict(b) for b in similar_books]
        await cache_service.set_similar_books(book_id, books_data, limit)
        logger.info(f"Cache SET for similar books (book_id={book_id}, limit={limit})")
        
        return similar_books
    
    async def get_books_by_user_history(self, user_id: int, limit: int = 5) -> List[Book]:
        """
        Collaborative filtering: Get recommendations based on user's review history
        """
        # Get genres of books the user has reviewed positively (rating >= 4)
        user_reviews_query = select(Review).where(
            Review.user_id == user_id,
            Review.rating >= 4.0
        )
        user_reviews_result = await self.db.execute(user_reviews_query)
        user_reviews = user_reviews_result.scalars().all()
        
        if not user_reviews:
            # No positive reviews, return popular books
            return await self.get_popular_books(limit=limit)
        
        # Get the book IDs user has already reviewed
        reviewed_book_ids = [r.book_id for r in user_reviews]
        
        # Get genres from positively reviewed books
        reviewed_books_query = select(Book).where(Book.id.in_(reviewed_book_ids))
        reviewed_books_result = await self.db.execute(reviewed_books_query)
        reviewed_books = reviewed_books_result.scalars().all()
        
        # Get unique genres
        genres = list(set(b.genre for b in reviewed_books if b.genre))
        
        if not genres:
            return await self.get_popular_books(limit=limit)
        
        # Find books in similar genres that the user hasn't reviewed
        # Also calculate average rating from reviews
        subquery = select(
            Review.book_id,
            func.avg(Review.rating).label('avg_rating')
        ).group_by(Review.book_id).subquery()
        
        query = select(Book).outerjoin(
            subquery, Book.id == subquery.c.book_id
        ).where(
            ~Book.id.in_(reviewed_book_ids),  # User hasn't reviewed this book
            Book.genre.in_(genres)  # Similar genre
        ).order_by(
            desc(func.coalesce(subquery.c.avg_rating, 0.0))
        ).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
