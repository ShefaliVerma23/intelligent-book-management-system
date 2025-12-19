"""
Book service for business logic
"""
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, desc

from app.models.books import Book
from app.api.schemas import BookCreate, BookUpdate
from app.services.llama_service import LlamaService


class BookService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.llama_service = LlamaService()

    async def create_book(self, book_data: BookCreate) -> Book:
        """Create a new book"""
        book = Book(**book_data.model_dump())
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
                    Book.summary.ilike(f"%{search}%")
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
        
        for field, value in book_data.model_dump(exclude_unset=True).items():
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
        """Generate AI summary for a book using Llama"""
        book = await self.get_book_by_id(book_id)
        if not book:
            return None
        
        # Create prompt for summarization
        prompt = f"Title: {book.title}\nAuthor: {book.author}\nSummary: {book.summary or 'No summary available'}"
        
        generated_summary = await self.llama_service.generate_summary(prompt)
        return generated_summary

    async def get_books_for_recommendations(self, limit: int = 50) -> List[Book]:
        """Get books for recommendations"""
        query = select(Book).order_by(desc(Book.id)).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_books_by_genre(self, genre: str, limit: int = 10) -> List[Book]:
        """Get books by genre for recommendations"""
        query = select(Book).where(Book.genre.ilike(f"%{genre}%")).limit(limit)
        result = await self.db.execute(query)
        return result.scalars().all()
