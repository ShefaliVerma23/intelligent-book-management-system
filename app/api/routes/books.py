"""
Book-related API endpoints

Book CRUD operations (POST/PUT/DELETE) require admin authentication.
Read operations (GET) are public.

Exception Handling:
- Service exceptions are caught and converted to appropriate HTTP responses
- All errors are logged for debugging
- Validation errors return 422 with detailed messages
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.base import get_db
from app.api.schemas import BookCreate, BookUpdate, BookResponse, ReviewResponse, ReviewBase
from app.services.book_service import BookService, BookServiceError, BookNotFoundError
from app.services.review_service import ReviewService, ReviewServiceError
from app.services.auth_service import AuthService, security

router = APIRouter(prefix="/books", tags=["books"])


@router.post("/", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
async def create_book(
    book: BookCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Create a new book (Admin only).
    
    Requires admin authentication to add books to the catalog.
    
    Returns:
        201: Book created successfully
        400: Invalid book data
        401: Not authenticated
        403: Not authorized (not admin)
        422: Validation error
    """
    try:
        auth_service = AuthService(db)
        await auth_service.require_admin(credentials)
        
        book_service = BookService(db)
        created_book = await book_service.create_book(book)
        
        logger.info(f"Book created: {created_book.id} - {created_book.title}")
        return created_book
        
    except BookServiceError as e:
        logger.error(f"Failed to create book: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[BookResponse])
async def get_books(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum records to return"),
    genre: Optional[str] = Query(None, description="Filter by genre"),
    author: Optional[str] = Query(None, description="Filter by author"),
    search: Optional[str] = Query(None, description="Search in title, author, summary"),
    db: AsyncSession = Depends(get_db)
):
    """Get books with optional filtering (Public).
    
    Returns:
        200: List of books
        500: Server error
    """
    try:
        book_service = BookService(db)
        return await book_service.get_books(
            skip=skip, 
            limit=limit, 
            genre=genre, 
            author=author, 
            search=search
        )
    except BookServiceError as e:
        logger.error(f"Failed to fetch books: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch books"
        )


@router.get("/{book_id}", response_model=BookResponse)
async def get_book(book_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific book by ID (Public).
    
    Returns:
        200: Book details
        404: Book not found
    """
    try:
        book_service = BookService(db)
        book = await book_service.get_book_by_id(book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        return book
        
    except BookServiceError as e:
        logger.error(f"Failed to fetch book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch book"
        )


@router.put("/{book_id}", response_model=BookResponse)
async def update_book(
    book_id: int,
    book_update: BookUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Update a specific book (Admin only).
    
    Requires admin authentication to modify book details.
    Only provided fields are updated.
    
    Returns:
        200: Updated book
        401: Not authenticated
        403: Not authorized (not admin)
        404: Book not found
        422: Validation error
    """
    try:
        auth_service = AuthService(db)
        await auth_service.require_admin(credentials)
        
        book_service = BookService(db)
        book = await book_service.update_book(book_id, book_update)
        
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        
        logger.info(f"Book updated: {book_id}")
        return book
        
    except BookServiceError as e:
        logger.error(f"Failed to update book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{book_id}", status_code=status.HTTP_200_OK)
async def delete_book(
    book_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Delete a specific book (Admin only).
    
    Requires admin authentication to remove books from the catalog.
    Associated reviews will also be deleted (cascade).
    
    Returns:
        200: Book deleted successfully
        401: Not authenticated
        403: Not authorized (not admin)
        404: Book not found
    """
    try:
        auth_service = AuthService(db)
        await auth_service.require_admin(credentials)
        
        book_service = BookService(db)
        success = await book_service.delete_book(book_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        
        logger.info(f"Book deleted: {book_id}")
        return {"message": "Book deleted successfully", "book_id": book_id}
        
    except BookServiceError as e:
        logger.error(f"Failed to delete book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete book"
        )


@router.post("/{book_id}/generate-summary")
async def generate_book_summary(
    book_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Generate AI summary for a book (Admin only).
    
    Requires admin authentication as this operation uses AI resources.
    
    Returns:
        200: Generated summary
        401: Not authenticated
        403: Not authorized (not admin)
        404: Book not found
        500: Summary generation failed
    """
    try:
        auth_service = AuthService(db)
        await auth_service.require_admin(credentials)
        
        book_service = BookService(db)
        summary = await book_service.generate_summary(book_id)
        
        if summary is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        
        logger.info(f"Summary generated for book: {book_id}")
        return {"book_id": book_id, "summary": summary}
        
    except BookServiceError as e:
        logger.error(f"Failed to generate summary for book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate summary"
        )


# =============================================================================
# Book Review Endpoints
# =============================================================================

@router.post("/{book_id}/reviews", response_model=ReviewResponse)
async def add_review_to_book(
    book_id: int,
    review_data: ReviewBase,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Add a review for a book (requires authentication).
    
    The user_id is automatically set from the authenticated user.
    Users can only have one review per book.
    
    Returns:
        200: Review created
        400: Already reviewed this book
        401: Not authenticated
        404: Book not found
        422: Validation error
    """
    try:
        # Get authenticated user from JWT token
        auth_service = AuthService(db)
        current_user = await auth_service.get_current_active_user(credentials)
        
        review_service = ReviewService(db)
        
        # Check if user already reviewed this book
        existing_review = await review_service.get_user_review_for_book(
            user_id=current_user.id,
            book_id=book_id
        )
        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this book. Use PUT to update your review."
            )
        
        # Create review
        review = await review_service.create_review_for_book(
            book_id=book_id, 
            review_data=review_data.model_dump(),
            user_id=current_user.id
        )
        
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        
        logger.info(f"Review added: user {current_user.id} reviewed book {book_id}")
        return review
        
    except ReviewServiceError as e:
        logger.error(f"Failed to add review for book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{book_id}/reviews", response_model=List[ReviewResponse])
async def get_book_reviews(
    book_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve all reviews for a book (Public).
    
    Returns:
        200: List of reviews
        500: Server error
    """
    try:
        review_service = ReviewService(db)
        return await review_service.get_reviews_for_book(
            book_id=book_id,
            skip=skip,
            limit=limit
        )
    except ReviewServiceError as e:
        logger.error(f"Failed to fetch reviews for book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch reviews"
        )


@router.get("/{book_id}/summary")
async def get_book_summary(
    book_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a summary and aggregated rating for a book (Public).
    
    Includes book details and AI-generated review summary.
    
    Returns:
        200: Book summary with review aggregation
        404: Book not found
    """
    try:
        book_service = BookService(db)
        review_service = ReviewService(db)
        
        book = await book_service.get_book_by_id(book_id)
        if not book:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Book with ID {book_id} not found"
            )
        
        review_summary = await review_service.get_review_summary_for_book(book_id)
        
        return {
            "book_id": book_id,
            "title": book.title,
            "author": book.author,
            "summary": book.summary,
            "review_summary": review_summary
        }
        
    except BookServiceError as e:
        logger.error(f"Failed to get summary for book {book_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get book summary"
        )
