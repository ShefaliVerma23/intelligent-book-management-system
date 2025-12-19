"""
Book-related API endpoints
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.api.schemas import BookCreate, BookUpdate, BookResponse, ReviewResponse
from app.services.book_service import BookService
from app.services.review_service import ReviewService

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/", response_model=BookResponse)
async def create_book(
    book: BookCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new book"""
    book_service = BookService(db)
    return await book_service.create_book(book)


@router.get("/", response_model=List[BookResponse])
async def get_books(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    genre: Optional[str] = Query(None),
    author: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """Get books with optional filtering"""
    book_service = BookService(db)
    return await book_service.get_books(
        skip=skip, 
        limit=limit, 
        genre=genre, 
        author=author, 
        search=search
    )


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific book by ID"""
    book_service = BookService(db)
    book = await book_service.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book_update: BookUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a specific book"""
    book_service = BookService(db)
    book = await book_service.update_book(book_id, book_update)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


@router.delete("/{book_id}")
async def delete_book(book_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a specific book"""
    book_service = BookService(db)
    success = await book_service.delete_book(book_id)
    if not success:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"message": "Book deleted successfully"}


@router.post("/{book_id}/generate-summary")
async def generate_book_summary(
    book_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Generate AI summary for a book"""
    book_service = BookService(db)
    summary = await book_service.generate_summary(book_id)
    if not summary:
        raise HTTPException(status_code=404, detail="Book not found")
    return {"book_id": book_id, "summary": summary}


# Book review endpoints
@router.post("/{book_id}/reviews", response_model=ReviewResponse)
async def add_review_to_book(
    book_id: int,
    review_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Add a review for a book"""
    # Note: This would normally require authentication to get user_id
    review_service = ReviewService(db)
    # For now, using user_id from request body, but should come from JWT token
    review = await review_service.create_review_for_book(book_id, review_data)
    if not review:
        raise HTTPException(status_code=404, detail="Book not found")
    return review


@router.get("/{book_id}/reviews", response_model=List[ReviewResponse])
async def get_book_reviews(
    book_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all reviews for a book"""
    review_service = ReviewService(db)
    return await review_service.get_reviews_for_book(
        book_id=book_id,
        skip=skip,
        limit=limit
    )


@router.get("/{book_id}/summary")
async def get_book_summary(
    book_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a summary and aggregated rating for a book"""
    book_service = BookService(db)
    review_service = ReviewService(db)
    
    book = await book_service.get_book_by_id(book_id)
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    
    review_summary = await review_service.get_review_summary_for_book(book_id)
    
    return {
        "book_id": book_id,
        "title": book.title,
        "author": book.author,
        "summary": book.summary,
        "review_summary": review_summary
    }
