"""
Pydantic schemas for API request/response models
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=255)
    full_name: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None
    preferred_genres: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = None
    preferred_genres: Optional[str] = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# Book schemas
class BookBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    author: str = Field(..., min_length=1, max_length=255)
    isbn: Optional[str] = Field(None, max_length=13)
    publisher: Optional[str] = Field(None, max_length=255)
    publication_year: Optional[int] = Field(None, ge=1000, le=2024)
    description: Optional[str] = None
    genre: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field("English", max_length=50)
    pages: Optional[int] = Field(None, ge=1)
    available_copies: Optional[int] = Field(1, ge=0)
    total_copies: Optional[int] = Field(1, ge=1)


class BookCreate(BookBase):
    pass


class BookUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    author: Optional[str] = Field(None, min_length=1, max_length=255)
    isbn: Optional[str] = Field(None, max_length=13)
    publisher: Optional[str] = Field(None, max_length=255)
    publication_year: Optional[int] = Field(None, ge=1000, le=2024)
    description: Optional[str] = None
    genre: Optional[str] = Field(None, max_length=100)
    language: Optional[str] = Field(None, max_length=50)
    pages: Optional[int] = Field(None, ge=1)
    available_copies: Optional[int] = Field(None, ge=0)
    total_copies: Optional[int] = Field(None, ge=1)


class BookResponse(BookBase):
    id: int
    ai_summary: Optional[str] = None
    summary_generated: bool = False
    average_rating: float = 0.0
    total_reviews: int = 0
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Review schemas
class ReviewBase(BaseModel):
    rating: float = Field(..., ge=1.0, le=5.0)
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None


class ReviewCreate(ReviewBase):
    book_id: int


class ReviewUpdate(BaseModel):
    rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None


class ReviewResponse(ReviewBase):
    id: int
    book_id: int
    user_id: int
    helpful_votes: int = 0
    ai_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# AI-related schemas
class SummaryRequest(BaseModel):
    book_id: int


class SummaryResponse(BaseModel):
    book_id: int
    summary: str
    generated_at: datetime


class RecommendationRequest(BaseModel):
    user_id: Optional[int] = None
    genre: Optional[str] = None
    count: int = Field(5, ge=1, le=20)


class RecommendationResponse(BaseModel):
    books: List[BookResponse]
    reasoning: str


# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
