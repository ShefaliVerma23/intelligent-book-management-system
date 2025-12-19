"""
Book model for the database
"""
from sqlalchemy import Column, String, Text, Integer
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
    """
    __tablename__ = "books"
    
    # Required fields as per specification
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(255), nullable=False, index=True)
    genre = Column(String(100), index=True)
    year_published = Column(Integer)
    summary = Column(Text)
    
    # Relationships
    reviews = relationship("Review", back_populates="book", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Book(id={self.id}, title='{self.title}', author='{self.author}')>"
