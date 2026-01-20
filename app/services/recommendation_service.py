"""
Recommendation service for book suggestions and AI-powered recommendations

Features:
- ML-based content filtering (TF-IDF)
- Collaborative filtering (based on user reviews)
- AI-generated reasoning (via Llama/OpenRouter)
- Redis caching (AWS ElastiCache compatible)
- Efficient database queries with pagination
- Proper exception handling and logging
"""
import json
import hashlib
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.exc import SQLAlchemyError
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


class RecommendationServiceError(Exception):
    """Base exception for recommendation service errors"""
    pass


class RecommendationService:
    """
    ML-powered recommendation service that uses:
    1. Content-based filtering (TF-IDF on genre, author, summary)
    2. Collaborative filtering (based on user reviews)
    3. AI-generated reasoning (via Llama/OpenRouter)
    4. Redis caching for improved performance
    
    All database operations are optimized with proper pagination
    and avoid loading entire tables into memory.
    """
    
    # Maximum books to load for ML operations (prevents memory issues)
    MAX_BOOKS_FOR_ML = 500
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llama_service = LlamaService()
        # Create a new vectorizer instance for each request to avoid concurrency issues
        self._vectorizer = None
    
    @property
    def vectorizer(self) -> TfidfVectorizer:
        """Lazy-loaded TF-IDF vectorizer"""
        if self._vectorizer is None:
            self._vectorizer = TfidfVectorizer(
                stop_words='english',
                max_features=1000,  # Limit features for performance
                ngram_range=(1, 2)
            )
        return self._vectorizer
    
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
        return Book(
            id=data.get("id"),
            title=data.get("title"),
            author=data.get("author"),
            genre=data.get("genre"),
            year_published=data.get("year_published"),
            summary=data.get("summary")
        )
    
    async def get_recommendations_for_user(
        self, 
        user: User, 
        genre: Optional[str] = None, 
        count: int = 5
    ) -> RecommendationResponse:
        """Get personalized book recommendations for a user.
        
        Args:
            user: The user requesting recommendations
            genre: Optional genre filter
            count: Number of recommendations (max 20)
            
        Returns:
            RecommendationResponse with books and AI-generated reasoning
        """
        logger.debug(
            "Getting recommendations for user",
            extra={
                "user_id": user.id,
                "genre": genre,
                "count": count
            }
        )
        
        try:
            # Get user's preferred genres
            user_preferences = []
            if user.preferred_genres:
                try:
                    user_preferences = json.loads(user.preferred_genres)
                except json.JSONDecodeError:
                    user_preferences = [g.strip() for g in user.preferred_genres.split(",")]
            
            # If genre is specified, use it; otherwise use user preferences
            target_genre = genre if genre else (user_preferences[0] if user_preferences else None)
            
            # Get books with average ratings
            books_with_ratings = await self._get_books_with_ratings(target_genre, count)
            
            if not books_with_ratings:
                logger.info("No books found for recommendations")
                return RecommendationResponse(
                    books=[],
                    reasoning="No books available matching your criteria."
                )
            
            # Generate AI reasoning
            books_context = "\n".join([
                f"- {book['book'].title} by {book['book'].author} ({book['book'].genre or 'General'}, Avg Rating: {book['avg_rating']:.1f}/5)"
                for book in books_with_ratings
            ])
            
            user_context = f"User preferences: {', '.join(user_preferences) if user_preferences else 'No specific preferences'}"
            if target_genre:
                user_context += f", Current filter: {target_genre}"
            
            # Get structured recommendation output
            recommendation_result = await self.llama_service.generate_recommendations(
                user_preferences=user_context,
                books_context=books_context
            )
            
            books = [item['book'] for item in books_with_ratings]
            
            logger.info(
                "Recommendations generated",
                extra={
                    "user_id": user.id,
                    "book_count": len(books),
                    "ai_success": recommendation_result.success
                }
            )
            
            return RecommendationResponse(
                books=[BookResponse.model_validate(book) for book in books],
                reasoning=recommendation_result.reasoning
            )
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting recommendations: {e}", exc_info=True)
            raise RecommendationServiceError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}", exc_info=True)
            raise RecommendationServiceError(f"Failed to get recommendations: {str(e)}")
    
    async def get_popular_books(
        self, 
        limit: int = 10, 
        genre: Optional[str] = None
    ) -> List[Book]:
        """Get popular books based on average ratings.
        
        Uses caching for improved performance.
        
        Args:
            limit: Maximum books to return
            genre: Optional genre filter
            
        Returns:
            List of popular Book instances
        """
        logger.debug(
            "Getting popular books",
            extra={"limit": limit, "genre": genre}
        )
        
        try:
            # Try to get from cache first
            cached = await cache_service.get_popular_books(genre, limit)
            if cached:
                logger.debug("Cache HIT for popular books")
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
            
            query = query.order_by(
                desc(subquery.c.avg_rating),
                desc(subquery.c.review_count)
            ).limit(limit)
            
            result = await self.db.execute(query)
            books = list(result.scalars().all())
            
            # Cache the result
            if books:
                books_data = [self._book_to_dict(b) for b in books]
                await cache_service.set_popular_books(books_data, genre, limit)
                logger.debug("Cache SET for popular books")
            
            logger.info(f"Found {len(books)} popular books")
            return books
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting popular books: {e}", exc_info=True)
            raise RecommendationServiceError(f"Database error: {str(e)}")
    
    async def generate_content_summary(self, content: str) -> str:
        """Generate a summary for given content using AI.
        
        Uses caching to avoid regenerating summaries for identical content.
        
        Args:
            content: Text content to summarize
            
        Returns:
            Generated summary text
        """
        if not content or len(content.strip()) == 0:
            return "No content provided to summarize."
        
        content = content.strip()
        
        # Create a hash of the content for caching
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        logger.debug(
            "Generating content summary",
            extra={"content_length": len(content), "content_hash": content_hash[:8]}
        )
        
        try:
            # Try to get from cache first
            cached = await cache_service.get_ai_summary(content_hash)
            if cached:
                logger.debug("Cache HIT for AI summary")
                return cached
            
            # Generate summary using AI
            result = await self.llama_service.generate_summary(content)
            summary = result.summary
            
            # Cache the result
            await cache_service.set_ai_summary(content_hash, summary)
            
            logger.info(
                "Summary generated",
                extra={
                    "content_length": len(content),
                    "summary_length": len(summary),
                    "success": result.success
                }
            )
            
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            return "Unable to generate summary at this time."
    
    async def _get_books_with_ratings(
        self, 
        genre: Optional[str], 
        count: int
    ) -> List[Dict]:
        """Get books with calculated average ratings.
        
        Efficient query that calculates ratings in the database.
        
        Args:
            genre: Optional genre filter
            count: Number of books to return
            
        Returns:
            List of dicts with book and rating info
        """
        try:
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
            ).limit(count * 2)  # Get extra to filter
            
            result = await self.db.execute(query)
            rows = result.all()
            
            return [
                {
                    'book': row[0],
                    'avg_rating': float(row[1]),
                    'review_count': int(row[2])
                }
                for row in rows
            ][:count]
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting books with ratings: {e}", exc_info=True)
            raise
    
    async def get_similar_books(self, book_id: int, limit: int = 5) -> List[Book]:
        """Get books similar to the specified book using ML.
        
        Uses TF-IDF vectorization on genre, author, and summary
        to find similar books based on content similarity.
        
        Optimized to only load books in the same genre for efficiency.
        
        Args:
            book_id: ID of the target book
            limit: Maximum similar books to return
            
        Returns:
            List of similar Book instances
        """
        logger.debug(
            "Getting similar books",
            extra={"book_id": book_id, "limit": limit}
        )
        
        try:
            # Try to get from cache first
            cached = await cache_service.get_similar_books(book_id, limit)
            if cached:
                logger.debug("Cache HIT for similar books")
                return [self._dict_to_book(b) for b in cached]
            
            # Get the target book
            target_result = await self.db.execute(
                select(Book).where(Book.id == book_id)
            )
            target_book = target_result.scalar_one_or_none()
            
            if not target_book:
                logger.warning(f"Target book not found", extra={"book_id": book_id})
                return []
            
            # Get candidate books (same genre or all if no genre)
            # Limited to avoid loading too many books
            query = select(Book).where(Book.id != book_id)
            
            if target_book.genre:
                # First try same genre
                query = query.where(Book.genre.ilike(f"%{target_book.genre}%"))
            
            query = query.limit(self.MAX_BOOKS_FOR_ML)
            
            result = await self.db.execute(query)
            candidate_books = list(result.scalars().all())
            
            if not candidate_books:
                logger.info("No candidate books found for similarity")
                return []
            
            # Create content strings for TF-IDF
            def create_content(book: Book) -> str:
                parts = []
                if book.genre:
                    # Weight genre more heavily
                    parts.extend([book.genre] * 3)
                if book.author:
                    parts.extend([book.author] * 2)
                if book.summary:
                    parts.append(book.summary[:500])  # Limit summary length
                return " ".join(parts) if parts else book.title
            
            # Include target book in content list
            all_books = [target_book] + candidate_books
            contents = [create_content(book) for book in all_books]
            
            # Handle case where all contents are empty
            if all(not c.strip() for c in contents):
                logger.warning("No content available for TF-IDF")
                similar_books = candidate_books[:limit]
            else:
                try:
                    # Create TF-IDF matrix
                    tfidf_matrix = self.vectorizer.fit_transform(contents)
                    
                    # Calculate cosine similarity (target is at index 0)
                    similarities = cosine_similarity(
                        tfidf_matrix[0:1], 
                        tfidf_matrix[1:]
                    )[0]
                    
                    # Get indices of most similar books
                    similar_indices = np.argsort(similarities)[::-1][:limit]
                    similar_books = [candidate_books[i] for i in similar_indices]
                    
                    logger.debug(
                        "TF-IDF similarity calculated",
                        extra={"top_similarity": float(similarities[similar_indices[0]]) if len(similar_indices) > 0 else 0}
                    )
                    
                except ValueError as e:
                    # TF-IDF failed (e.g., empty vocabulary)
                    logger.warning(f"TF-IDF failed: {e}, using fallback")
                    similar_books = candidate_books[:limit]
            
            # Cache the result
            if similar_books:
                books_data = [self._book_to_dict(b) for b in similar_books]
                await cache_service.set_similar_books(book_id, books_data, limit)
                logger.debug("Cache SET for similar books")
            
            logger.info(
                f"Found {len(similar_books)} similar books",
                extra={"book_id": book_id}
            )
            return similar_books
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting similar books: {e}", exc_info=True)
            raise RecommendationServiceError(f"Database error: {str(e)}")
        except Exception as e:
            logger.error(f"Error getting similar books: {e}", exc_info=True)
            raise RecommendationServiceError(f"Failed to get similar books: {str(e)}")
    
    async def get_books_by_user_history(
        self, 
        user_id: int, 
        limit: int = 5
    ) -> List[Book]:
        """Get recommendations based on user's review history.
        
        Uses collaborative filtering to find books in genres
        the user has rated highly.
        
        Args:
            user_id: The user's ID
            limit: Maximum books to return
            
        Returns:
            List of recommended Book instances
        """
        logger.debug(
            "Getting recommendations by user history",
            extra={"user_id": user_id, "limit": limit}
        )
        
        try:
            # Get genres of books the user has reviewed positively (rating >= 4)
            user_reviews_query = select(Review).where(
                Review.user_id == user_id,
                Review.rating >= 4.0
            ).limit(100)  # Limit reviews to process
            
            user_reviews_result = await self.db.execute(user_reviews_query)
            user_reviews = list(user_reviews_result.scalars().all())
            
            if not user_reviews:
                logger.info("No positive reviews found, returning popular books")
                return await self.get_popular_books(limit=limit)
            
            # Get the book IDs user has already reviewed
            reviewed_book_ids = [r.book_id for r in user_reviews]
            
            # Get genres from positively reviewed books (single query)
            reviewed_books_query = select(Book.genre).where(
                Book.id.in_(reviewed_book_ids)
            ).distinct()
            
            reviewed_books_result = await self.db.execute(reviewed_books_query)
            genres = [row[0] for row in reviewed_books_result.all() if row[0]]
            
            if not genres:
                logger.info("No genres found from reviews, returning popular books")
                return await self.get_popular_books(limit=limit)
            
            # Find books in similar genres that the user hasn't reviewed
            subquery = select(
                Review.book_id,
                func.avg(Review.rating).label('avg_rating')
            ).group_by(Review.book_id).subquery()
            
            query = select(Book).outerjoin(
                subquery, Book.id == subquery.c.book_id
            ).where(
                ~Book.id.in_(reviewed_book_ids),
                Book.genre.in_(genres)
            ).order_by(
                desc(func.coalesce(subquery.c.avg_rating, 0.0))
            ).limit(limit)
            
            result = await self.db.execute(query)
            books = list(result.scalars().all())
            
            logger.info(
                f"Found {len(books)} recommendations from user history",
                extra={"user_id": user_id, "genres_used": len(genres)}
            )
            return books
            
        except SQLAlchemyError as e:
            logger.error(f"Database error getting recommendations by history: {e}", exc_info=True)
            raise RecommendationServiceError(f"Database error: {str(e)}")
