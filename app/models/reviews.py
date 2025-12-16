"""
Review model for the database
"""
from sqlalchemy import Column, String, Text, Integer, ForeignKey, Float
from sqlalchemy.orm import relationship
from .base import BaseModel


class Review(BaseModel):
    __tablename__ = "reviews"
    
    # Foreign keys
    book_id = Column(Integer, ForeignKey("books.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Review content
    rating = Column(Float, nullable=False)  # 1.0 to 5.0
    title = Column(String(255))
    content = Column(Text)
    
    # Review metadata
    helpful_votes = Column(Integer, default=0)
    
    # AI-generated review summary (for aggregating multiple reviews)
    ai_summary = Column(Text)
    
    # Relationships
    book = relationship("Book", back_populates="reviews")
    user = relationship("User", back_populates="reviews")
    
    def __repr__(self):
        return f"<Review(book_id={self.book_id}, user_id={self.user_id}, rating={self.rating})>"
