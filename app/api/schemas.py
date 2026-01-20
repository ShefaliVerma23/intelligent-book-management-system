"""
Pydantic schemas for API request/response models

All schemas include proper validation with:
- Field constraints (min/max length, patterns)
- Custom validators where needed
- Clear error messages
"""
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, model_validator
import re


# =============================================================================
# User Schemas
# =============================================================================

class UserBase(BaseModel):
    """Base user schema with validation"""
    username: str = Field(
        ..., 
        min_length=3, 
        max_length=50, 
        pattern=r'^[a-zA-Z0-9_]+$',
        description="Username (alphanumeric and underscores only)",
        examples=["john_doe", "user123"]
    )
    email: str = Field(
        ..., 
        min_length=5, 
        max_length=255,
        description="Valid email address",
        examples=["user@example.com"]
    )
    full_name: Optional[str] = Field(
        None, 
        max_length=255,
        description="Full display name"
    )
    bio: Optional[str] = Field(
        None, 
        max_length=1000,
        description="User biography"
    )
    preferred_genres: Optional[str] = Field(
        None, 
        max_length=500,
        description="Comma-separated list of preferred genres"
    )
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
        if not re.match(email_pattern, v):
            raise ValueError('Invalid email format')
        return v.lower().strip()
    
    @field_validator('username')
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate and normalize username"""
        return v.strip().lower()
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean full name"""
        if v is not None:
            v = v.strip()
            if v and len(v) < 2:
                raise ValueError('Full name must be at least 2 characters')
        return v or None


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(
        ..., 
        min_length=8, 
        max_length=128,
        description="Password (min 8 chars, must contain letter and number)"
    )
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """Validate password strength"""
        if not any(c.isalpha() for c in v):
            raise ValueError('Password must contain at least one letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v


class AdminUserCreate(UserCreate):
    """Schema for admin to create users with additional privileges"""
    is_active: bool = Field(
        default=True, 
        description="Whether the user account is active"
    )
    is_admin: bool = Field(
        default=False, 
        description="Whether the user has admin privileges"
    )


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    full_name: Optional[str] = Field(None, max_length=255)
    bio: Optional[str] = Field(None, max_length=1000)
    preferred_genres: Optional[str] = Field(None, max_length=500)
    
    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = v.strip()
            if v and len(v) < 2:
                raise ValueError('Full name must be at least 2 characters')
        return v or None


class UserResponse(UserBase):
    id: int
    is_active: bool
    is_admin: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


# =============================================================================
# Book Schemas
# =============================================================================

class BookBase(BaseModel):
    """Base book schema with validation"""
    title: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="Book title",
        examples=["The Great Gatsby"]
    )
    author: str = Field(
        ..., 
        min_length=1, 
        max_length=255,
        description="Author name",
        examples=["F. Scott Fitzgerald"]
    )
    genre: Optional[str] = Field(
        None, 
        max_length=100,
        description="Book genre/category",
        examples=["Fiction", "Science Fiction", "Mystery"]
    )
    year_published: Optional[int] = Field(
        None, 
        ge=1000, 
        le=2100,
        description="Year of publication"
    )
    summary: Optional[str] = Field(
        None,
        max_length=10000,
        description="Book summary/description"
    )
    
    @field_validator('title', 'author')
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        """Ensure title and author are not just whitespace"""
        v = v.strip()
        if not v:
            raise ValueError('Cannot be empty or whitespace only')
        return v
    
    @field_validator('genre')
    @classmethod
    def validate_genre(cls, v: Optional[str]) -> Optional[str]:
        """Normalize genre"""
        if v is not None:
            v = v.strip()
        return v or None


class BookCreate(BookBase):
    """Schema for creating a new book"""
    pass


class BookUpdate(BaseModel):
    """Schema for updating a book (all fields optional)"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    author: Optional[str] = Field(None, min_length=1, max_length=255)
    genre: Optional[str] = Field(None, max_length=100)
    year_published: Optional[int] = Field(None, ge=1000, le=2100)
    summary: Optional[str] = Field(None, max_length=10000)
    
    @field_validator('title', 'author')
    @classmethod
    def validate_not_empty(cls, v: Optional[str]) -> Optional[str]:
        """Ensure title and author are not just whitespace"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError('Cannot be empty or whitespace only')
        return v


class BookResponse(BookBase):
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# =============================================================================
# Review Schemas
# =============================================================================

class ReviewBase(BaseModel):
    """Base review schema with validation"""
    rating: float = Field(
        ..., 
        ge=1.0, 
        le=5.0,
        description="Rating from 1.0 to 5.0",
        examples=[4.5]
    )
    review_text: Optional[str] = Field(
        None, 
        max_length=5000,
        description="Review content"
    )
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v: float) -> float:
        """Round rating to 1 decimal place"""
        return round(v, 1)
    
    @field_validator('review_text')
    @classmethod
    def validate_review_text(cls, v: Optional[str]) -> Optional[str]:
        """Clean and validate review text"""
        if v is not None:
            v = v.strip()
            if v and len(v) < 10:
                raise ValueError('Review text must be at least 10 characters if provided')
        return v or None


class ReviewCreate(ReviewBase):
    """Schema for creating a review (requires authentication)"""
    book_id: int = Field(
        ..., 
        ge=1, 
        description="ID of the book being reviewed"
    )


class ReviewUpdate(BaseModel):
    """Schema for updating a review"""
    rating: Optional[float] = Field(None, ge=1.0, le=5.0)
    review_text: Optional[str] = Field(None, max_length=5000)
    
    @field_validator('rating')
    @classmethod
    def validate_rating(cls, v: Optional[float]) -> Optional[float]:
        """Round rating to 1 decimal place"""
        if v is not None:
            return round(v, 1)
        return v
    
    @field_validator('review_text')
    @classmethod
    def validate_review_text(cls, v: Optional[str]) -> Optional[str]:
        """Clean review text"""
        if v is not None:
            v = v.strip()
        return v or None


class ReviewResponse(ReviewBase):
    id: int
    book_id: int
    user_id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# =============================================================================
# AI-related Schemas
# =============================================================================

class SummaryRequest(BaseModel):
    """Request schema for book summary generation"""
    book_id: int = Field(..., ge=1, description="ID of the book")


class SummaryResponse(BaseModel):
    """Response schema for book summary"""
    book_id: int
    summary: str
    generated_at: datetime


class GenerateSummaryRequest(BaseModel):
    """Request schema for generating content summary"""
    content: str = Field(
        ...,
        min_length=10,
        max_length=50000,
        description="Content to summarize"
    )
    
    @field_validator('content')
    @classmethod
    def validate_content(cls, v: str) -> str:
        """Validate content is not just whitespace"""
        v = v.strip()
        if not v:
            raise ValueError('Content cannot be empty')
        if len(v) < 10:
            raise ValueError('Content must be at least 10 characters')
        return v


class RecommendationRequest(BaseModel):
    """Request schema for book recommendations"""
    user_id: Optional[int] = Field(None, ge=1, description="User ID for personalized recommendations")
    genre: Optional[str] = Field(None, max_length=100, description="Genre filter")
    count: int = Field(5, ge=1, le=20, description="Number of recommendations")


class RecommendationResponse(BaseModel):
    """Response schema for book recommendations"""
    books: List[BookResponse]
    reasoning: str


# =============================================================================
# LLM Structured Output Models
# =============================================================================

class LLMGenerationMetadata(BaseModel):
    """Metadata about the LLM generation"""
    model: str = Field(..., description="Model used for generation")
    input_tokens: Optional[int] = Field(None, description="Number of input tokens")
    output_tokens: Optional[int] = Field(None, description="Number of output tokens")
    temperature: float = Field(..., description="Temperature used")
    max_tokens: int = Field(..., description="Max tokens limit")
    generation_time_ms: Optional[int] = Field(None, description="Generation time in milliseconds")


class LLMSummaryOutput(BaseModel):
    """Structured output for AI-generated summaries"""
    summary: str = Field(..., description="Generated summary text", max_length=500)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    metadata: Optional[LLMGenerationMetadata] = None
    success: bool = Field(True, description="Whether generation was successful")
    error: Optional[str] = Field(None, description="Error message if generation failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "summary": "This book explores the journey of a young wizard...",
                "confidence": 0.85,
                "success": True,
                "metadata": {
                    "model": "meta-llama/llama-3-8b-instruct:free",
                    "output_tokens": 50,
                    "temperature": 0.7,
                    "max_tokens": 150
                }
            }
        }


class LLMRecommendationOutput(BaseModel):
    """Structured output for AI-generated recommendations"""
    reasoning: str = Field(..., description="Explanation of why books are recommended", max_length=500)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="Confidence score")
    metadata: Optional[LLMGenerationMetadata] = None
    success: bool = Field(True, description="Whether generation was successful")
    error: Optional[str] = Field(None, description="Error message if generation failed")


class LLMReviewSummaryOutput(BaseModel):
    """Structured output for AI-generated review summaries"""
    summary: str = Field(..., description="Summary of reviews", max_length=500)
    sentiment: Optional[str] = Field(None, description="Overall sentiment: positive, negative, mixed, neutral")
    average_rating_mentioned: Optional[float] = Field(None, ge=1.0, le=5.0)
    key_themes: Optional[List[str]] = Field(None, description="Key themes from reviews")
    metadata: Optional[LLMGenerationMetadata] = None
    success: bool = Field(True, description="Whether generation was successful")
    error: Optional[str] = Field(None, description="Error message if generation failed")


# Authentication schemas
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
