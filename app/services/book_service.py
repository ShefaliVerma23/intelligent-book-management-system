"""
Book service for business logic
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func, desc
from sqlalchemy.orm import selectinload

from app.models.books import Book
from app.api.schemas import BookCreate, BookUpdate
from app.services.llama_service import LlamaService


class BookService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llama_service = LlamaService()

    async def create_book(self, book_data: BookCreate) -> Book:
        """Create a new book"""
        book = Book(**book_data.dict())
        self.db.add(book)
        await self.db.commit()
        await self.db.refresh(book)
        return book

    async def get_books(
        self, 
        skip: int = 0, 
        limit: int = 100,
        genre: Optional[str] = None,
        author: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Book]:
        """Get books with optional filtering"""
        query = select(Book)
        
        if genre:
            query = query.where(Book.genre.ilike(f"%{genre}%"))
        
        if author:
            query = query.where(Book.author.ilike(f"%{author}%"))
        
        if search:
            query = query.where(
                or_(
                    Book.title.ilike(f"%{search}%"),
                    Book.author.ilike(f"%{search}%"),
                    Book.description.ilike(f"%{search}%")
                )
            )
        
        query = query.offset(skip).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_book_by_id(self, book_id: int) -> Optional[Book]:
        """Get a book by ID"""
        query = select(Book).where(Book.id == book_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_book(self, book_id: int, book_data: BookUpdate) -> Optional[Book]:
        """Update a book"""
        book = await self.get_book_by_id(book_id)
        if not book:
            return None
        
        for field, value in book_data.dict(exclude_unset=True).items():
            setattr(book, field, value)
        
        await self.db.commit()
        await self.db.refresh(book)
        return book

    async def delete_book(self, book_id: int) -> bool:
        """Delete a book"""
        book = await self.get_book_by_id(book_id)
        if not book:
            return False
        
        await self.db.delete(book)
        await self.db.commit()
        return True

    async def generate_summary(self, book_id: int) -> Optional[str]:
        """Generate AI summary for a book"""
        book = await self.get_book_by_id(book_id)
        if not book:
            return None
        
        # Create prompt for summarization
        prompt = f"Title: {book.title}\nAuthor: {book.author}\nDescription: {book.description or 'No description available'}"
        
        summary = await self.llama_service.generate_summary(prompt)
        
        # Update book with generated summary
        book.ai_summary = summary
        book.summary_generated = True
        await self.db.commit()
        
        return summary

    async def get_books_for_recommendations(self, limit: int = 50) -> List[Book]:
        """Get books for recommendations (highest rated)"""
        query = select(Book).where(Book.average_rating > 0).order_by(desc(Book.average_rating)).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_books_by_genre(self, genre: str, limit: int = 10) -> List[Book]:
        """Get books by genre for recommendations"""
        query = select(Book).where(Book.genre.ilike(f"%{genre}%")).order_by(desc(Book.average_rating)).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
