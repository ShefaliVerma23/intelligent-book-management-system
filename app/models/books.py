"""
Book model for the database
"""
from sqlalchemy import Column, String, Text, Integer, Index
from sqlalchemy.orm import relationship
from .base import BaseModel


class Book(BaseModel):
    """
    Books table with fields:
    - id: Primary key (inherited from BaseModel)
    - title: Book title
    - author: Book author
    - genre: Book genre/category
    - year_published: Year the book was published
    - summary: Brief description/summary of the book
    
    Indexes:
    - title, author, genre, year_published (for filtering/searching)
    - Composite index on (genre, year_published) for common query patterns
    
    Relationships:
    - reviews: One-to-many with Review (cascade delete)
    """
    __tablename__ = "books"
    
    # Required fields as per specification
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(255), nullable=False, index=True)
    genre = Column(String(100), index=True)
    year_published = Column(Integer, index=True)  # Index for year filtering
    summary = Column(Text)
    
    # Composite indexes for common query patterns
    __table_args__ = (
        # Index for filtering by genre and year together
        Index('ix_books_genre_year', 'genre', 'year_published'),
    )
    
    # Relationships with proper configuration for async and cascade
    # - cascade="all, delete-orphan": SQLAlchemy handles cascades in session
    # - passive_deletes=True: Trust database ON DELETE CASCADE, don't load children
    # - lazy="selectin": Efficient async-compatible loading strategy
    reviews = relationship(
        "Review", 
        back_populates="book", 
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin"
    )
    
    def __repr__(self):
        return f"<Book(id={self.id}, title='{self.title}', author='{self.author}')>"
