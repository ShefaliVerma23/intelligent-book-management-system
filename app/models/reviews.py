"""
Review model for the database
"""
from sqlalchemy import Column, Text, Integer, ForeignKey, Float, CheckConstraint, UniqueConstraint, Index
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
    
    Constraints:
    - Unique constraint on (book_id, user_id) - one review per user per book
    - Check constraint on rating (1-5)
    - Cascade delete when book or user is deleted
    """
    __tablename__ = "reviews"
    
    # Foreign keys with cascade delete
    book_id = Column(
        Integer, 
        ForeignKey("books.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    user_id = Column(
        Integer, 
        ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False, 
        index=True
    )
    
    # Review content
    review_text = Column(Text)
    rating = Column(Float, nullable=False, index=True)  # Index for rating filtering/sorting
    
    # Table constraints and indexes
    __table_args__ = (
        # One review per user per book
        UniqueConstraint('book_id', 'user_id', name='uq_review_book_user'),
        # Composite index for efficient lookups
        Index('ix_review_book_user', 'book_id', 'user_id'),
        # Index for finding high-rated reviews by book
        Index('ix_review_book_rating', 'book_id', 'rating'),
        # Rating must be between 1 and 5
        CheckConstraint('rating >= 1 AND rating <= 5', name='ck_review_valid_rating'),
    )
    
    # Relationships with proper lazy loading for async
    # Using 'joined' for eager loading when Review is queried
    book = relationship(
        "Book", 
        back_populates="reviews",
        lazy="joined"
    )
    user = relationship(
        "User", 
        back_populates="reviews",
        lazy="joined"
    )
    
    def __repr__(self):
        return f"<Review(id={self.id}, book_id={self.book_id}, user_id={self.user_id}, rating={self.rating})>"
