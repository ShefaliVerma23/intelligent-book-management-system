"""
Book model for the database
"""
from sqlalchemy import Column, String, Text, Integer, Float, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel


class Book(BaseModel):
    __tablename__ = "books"
    
    # Basic book information
    title = Column(String(255), nullable=False, index=True)
    author = Column(String(255), nullable=False, index=True)
    isbn = Column(String(13), unique=True, index=True)
    publisher = Column(String(255))
    publication_year = Column(Integer)
    
    # Book details
    description = Column(Text)
    genre = Column(String(100), index=True)
    language = Column(String(50), default="English")
    pages = Column(Integer)
    
    # AI-generated content
    ai_summary = Column(Text)
    summary_generated = Column(Boolean, default=False)
    
    # Ratings and reviews
    average_rating = Column(Float, default=0.0)
    total_reviews = Column(Integer, default=0)
    
    # Book availability
    available_copies = Column(Integer, default=1)
    total_copies = Column(Integer, default=1)
    
    # Relationships
    reviews = relationship("Review", back_populates="book", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Book(title='{self.title}', author='{self.author}')>"
    
    def update_rating_stats(self):
        """Update average rating and total reviews count"""
        if self.reviews:
            self.total_reviews = len(self.reviews)
            self.average_rating = sum(review.rating for review in self.reviews) / self.total_reviews
        else:
            self.total_reviews = 0
            self.average_rating = 0.0
