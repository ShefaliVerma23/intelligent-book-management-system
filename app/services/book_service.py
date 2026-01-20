"""
Book service for business logic

Provides CRUD operations for books with:
- Proper exception handling
- Structured logging
- Efficient database queries
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from loguru import logger

from app.models.books import Book
from app.api.schemas import BookCreate, BookUpdate
from app.services.llama_service import LlamaService


class BookServiceError(Exception):
    """Base exception for book service errors"""
    pass


class BookNotFoundError(BookServiceError):
    """Raised when a book is not found"""
    pass


class BookCreationError(BookServiceError):
    """Raised when book creation fails"""
    pass


class BookService:
    """Service for book-related business logic"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llama_service = LlamaService()

    async def create_book(self, book_data: BookCreate) -> Book:
        """Create a new book.
        
        Args:
            book_data: Book creation data
            
        Returns:
            Created Book instance
            
        Raises:
            BookCreationError: If creation fails
        """
        logger.debug(
            "Creating book",
            extra={"title": book_data.title, "author": book_data.author}
        )
        
        try:
            book = Book(**book_data.model_dump())
            self.db.add(book)
            await self.db.commit()
            await self.db.refresh(book)
            
            logger.info(
                "Book created successfully",
                extra={"book_id": book.id, "title": book.title}
            )
            return book
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error creating book: {e}", exc_info=True)
            raise BookCreationError(f"Failed to create book: duplicate or invalid data")
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error creating book: {e}", exc_info=True)
            raise BookCreationError(f"Database error: {str(e)}")

    async def get_books(
        self, 
        skip: int = 0, 
        limit: int = 100,
        genre: Optional[str] = None,
        author: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Book]:
        """Get books with optional filtering.
        
        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            genre: Filter by genre (case-insensitive partial match)
            author: Filter by author (case-insensitive partial match)
            search: Search in title, author, and summary
            
        Returns:
            List of Book instances
        """
        logger.debug(
            "Fetching books",
            extra={
                "skip": skip,
                "limit": limit,
                "genre": genre,
                "author": author,
                "search": search
            }
        )
        
        try:
            query = select(Book)
            
            if genre:
                query = query.where(Book.genre.ilike(f"%{genre}%"))
            
            if author:
                query = query.where(Book.author.ilike(f"%{author}%"))
            
            if search:
                search_filter = or_(
                    Book.title.ilike(f"%{search}%"),
                    Book.author.ilike(f"%{search}%"),
                    Book.summary.ilike(f"%{search}%")
                )
                query = query.where(search_filter)
            
            # Add ordering for consistent pagination
            query = query.order_by(Book.id).offset(skip).limit(limit)
            
            result = await self.db.execute(query)
            books = list(result.scalars().all())
            
            logger.debug(f"Found {len(books)} books")
            return books
            
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching books: {e}", exc_info=True)
            raise BookServiceError(f"Failed to fetch books: {str(e)}")

    async def get_book_by_id(self, book_id: int) -> Optional[Book]:
        """Get a book by ID.
        
        Args:
            book_id: The book's ID
            
        Returns:
            Book instance or None if not found
        """
        logger.debug(f"Fetching book by ID", extra={"book_id": book_id})
        
        try:
            query = select(Book).where(Book.id == book_id)
            result = await self.db.execute(query)
            book = result.scalar_one_or_none()
            
            if book:
                logger.debug(f"Found book", extra={"book_id": book_id, "title": book.title})
            else:
                logger.debug(f"Book not found", extra={"book_id": book_id})
            
            return book
            
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching book: {e}", exc_info=True)
            raise BookServiceError(f"Failed to fetch book: {str(e)}")

    async def update_book(self, book_id: int, book_data: BookUpdate) -> Optional[Book]:
        """Update a book.
        
        Args:
            book_id: The book's ID
            book_data: Update data (only provided fields are updated)
            
        Returns:
            Updated Book instance or None if not found
        """
        logger.debug(f"Updating book", extra={"book_id": book_id})
        
        try:
            book = await self.get_book_by_id(book_id)
            if not book:
                logger.debug(f"Book not found for update", extra={"book_id": book_id})
                return None
            
            update_data = book_data.model_dump(exclude_unset=True)
            for field, value in update_data.items():
                setattr(book, field, value)
            
            await self.db.commit()
            await self.db.refresh(book)
            
            logger.info(
                "Book updated successfully",
                extra={"book_id": book_id, "updated_fields": list(update_data.keys())}
            )
            return book
            
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error updating book: {e}", exc_info=True)
            raise BookServiceError(f"Failed to update book: invalid data")
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error updating book: {e}", exc_info=True)
            raise BookServiceError(f"Failed to update book: {str(e)}")

    async def delete_book(self, book_id: int) -> bool:
        """Delete a book.
        
        Args:
            book_id: The book's ID
            
        Returns:
            True if deleted, False if not found
        """
        logger.debug(f"Deleting book", extra={"book_id": book_id})
        
        try:
            book = await self.get_book_by_id(book_id)
            if not book:
                logger.debug(f"Book not found for deletion", extra={"book_id": book_id})
                return False
            
            await self.db.delete(book)
            await self.db.commit()
            
            logger.info(f"Book deleted successfully", extra={"book_id": book_id})
            return True
            
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error deleting book: {e}", exc_info=True)
            raise BookServiceError(f"Failed to delete book: {str(e)}")

    async def generate_summary(self, book_id: int) -> Optional[str]:
        """Generate AI summary for a book.
        
        Args:
            book_id: The book's ID
            
        Returns:
            Generated summary text, or None if book not found
        """
        logger.debug(f"Generating summary for book", extra={"book_id": book_id})
        
        try:
            book = await self.get_book_by_id(book_id)
            if not book:
                logger.debug(f"Book not found for summary generation", extra={"book_id": book_id})
                return None
            
            # Create prompt for summarization
            content = f"Title: {book.title}\nAuthor: {book.author}\nSummary: {book.summary or 'No summary available'}"
            
            # Get structured output and extract summary text
            result = await self.llama_service.generate_summary(content)
            
            if result.success:
                logger.info(
                    "Summary generated successfully",
                    extra={
                        "book_id": book_id,
                        "generation_time_ms": result.metadata.generation_time_ms if result.metadata else None
                    }
                )
            else:
                logger.warning(
                    "Summary generation had issues",
                    extra={"book_id": book_id, "error": result.error}
                )
            
            return result.summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {e}", exc_info=True)
            raise BookServiceError(f"Failed to generate summary: {str(e)}")

    async def get_books_for_recommendations(self, limit: int = 50) -> List[Book]:
        """Get books for recommendations.
        
        Args:
            limit: Maximum number of books to return
            
        Returns:
            List of Book instances ordered by most recent
        """
        logger.debug(f"Fetching books for recommendations", extra={"limit": limit})
        
        try:
            query = select(Book).order_by(desc(Book.id)).limit(limit)
            result = await self.db.execute(query)
            return list(result.scalars().all())
            
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching books for recommendations: {e}", exc_info=True)
            raise BookServiceError(f"Failed to fetch books: {str(e)}")

    async def get_books_by_genre(self, genre: str, limit: int = 10) -> List[Book]:
        """Get books by genre.
        
        Args:
            genre: Genre to filter by (case-insensitive partial match)
            limit: Maximum number of books to return
            
        Returns:
            List of Book instances matching the genre
        """
        logger.debug(f"Fetching books by genre", extra={"genre": genre, "limit": limit})
        
        try:
            query = select(Book).where(Book.genre.ilike(f"%{genre}%")).limit(limit)
            result = await self.db.execute(query)
            return list(result.scalars().all())
            
        except SQLAlchemyError as e:
            logger.error(f"Database error fetching books by genre: {e}", exc_info=True)
            raise BookServiceError(f"Failed to fetch books: {str(e)}")
