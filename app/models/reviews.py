"""
Review model for the database
"""
from sqlalchemy import Column, Text, Integer, ForeignKey, Float, CheckConstraint
from sqlalchemy.orm import relationship
from .base import BaseModel


class Review(BaseModel):
    """
    Reviews table with fields:
    - id: Primary key (inherited from BaseModel)
    - book_id: Foreign key referencing books table
    - user_id: Foreign key referencing users table
    - review_text: The review content
    - rating: Numeric rating (1-5)
    """
    __tablename__ = "reviews"
    
    # Foreign keys
    book_id = Column(Integer, ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Review content
    review_text = Column(Text)
    rating = Column(Float, nullable=False)
    
    # Add check constraint for rating range
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='valid_rating'),
    )
    
    # Relationships
    book = relationship("Book", back_populates="reviews")
    user = relationship("User", back_populates="reviews")
    
    def __repr__(self):
        return f"<Review(id={self.id}, book_id={self.book_id}, user_id={self.user_id}, rating={self.rating})>"
