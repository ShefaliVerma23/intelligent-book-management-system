"""
Tests for review-related API endpoints

Tests cover:
- CRUD operations (Create, Read, Update, Delete)
- Filtering by book and user
- Pagination
- AI-generated review summaries
- Authentication and authorization requirements

Note: 
- POST operations return 201 Created
- PUT, DELETE, GET return 200 OK
- User can only modify their own reviews (or admin can modify any)
"""
import pytest
from httpx import AsyncClient
from typing import Dict

from app.models.reviews import Review
from app.models.books import Book
from app.models.users import User


@pytest.mark.asyncio
class TestReviews:
    """Test all review CRUD operations and related endpoints"""
    
    # =========================================================================
    # Create Review Tests - Returns 201 Created
    # =========================================================================

    async def test_create_review_requires_auth(
        self,
        async_client: AsyncClient,
        test_book: Book
    ):
        """Test that creating a review requires authentication"""
        review_data = {
            "book_id": test_book.id,
            "rating": 4.0,
            "review_text": "This is a good book that I enjoyed reading very much."
        }
        
        response = await async_client.post("/api/v1/reviews/", json=review_data)
        assert response.status_code in [401, 403]

    async def test_create_review(
        self,
        async_client: AsyncClient,
        test_book: Book,
        test_user: User,
        auth_headers: Dict[str, str]
    ):
        """Test creating a new review - POST /reviews (authenticated) - returns 201"""
        review_data = {
            "book_id": test_book.id,
            "rating": 4.0,
            "review_text": "This is a good book that I enjoyed reading very much."
        }
        
        response = await async_client.post(
            "/api/v1/reviews/",
            json=review_data,
            headers=auth_headers
        )
        assert response.status_code == 201  # Created
        
        data = response.json()
        assert data["book_id"] == review_data["book_id"]
        assert data["rating"] == review_data["rating"]
        assert data["review_text"] == review_data["review_text"]
        assert data["user_id"] == test_user.id  # Should be set from auth
        assert "id" in data
        assert "created_at" in data

    async def test_create_review_rating_validation(
        self,
        async_client: AsyncClient,
        test_book: Book,
        auth_headers: Dict[str, str]
    ):
        """Test that rating must be between 1 and 5"""
        # Rating too low
        review_data = {
            "book_id": test_book.id,
            "rating": 0.5,
            "review_text": "Bad rating value test - this should fail validation"
        }
        response = await async_client.post(
            "/api/v1/reviews/",
            json=review_data,
            headers=auth_headers
        )
        assert response.status_code == 422
        
        # Rating too high
        review_data["rating"] = 6.0
        response = await async_client.post(
            "/api/v1/reviews/",
            json=review_data,
            headers=auth_headers
        )
        assert response.status_code == 422
    
    async def test_create_duplicate_review(
        self,
        async_client: AsyncClient,
        test_book: Book,
        test_review: Review,
        auth_headers: Dict[str, str]
    ):
        """Test that users cannot create duplicate reviews for the same book"""
        # test_review already exists for test_user + test_book
        review_data = {
            "book_id": test_book.id,
            "rating": 3.0,
            "review_text": "Trying to add another review for the same book"
        }
        
        response = await async_client.post(
            "/api/v1/reviews/",
            json=review_data,
            headers=auth_headers
        )
        # Should fail because user already reviewed this book
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()
    
    async def test_create_review_nonexistent_book(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test creating a review for a book that doesn't exist"""
        review_data = {
            "book_id": 99999,
            "rating": 4.0,
            "review_text": "This review is for a non-existent book"
        }
        
        response = await async_client.post(
            "/api/v1/reviews/",
            json=review_data,
            headers=auth_headers
        )
        assert response.status_code == 404
        assert "book" in response.json()["detail"].lower()
    
    # =========================================================================
    # Read Review Tests (Public)
    # =========================================================================

    async def test_get_reviews(self, async_client: AsyncClient, test_review: Review):
        """Test getting all reviews - GET /reviews (public)"""
        response = await async_client.get("/api/v1/reviews/")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(review["id"] == test_review.id for review in data)

    async def test_get_review_by_id(self, async_client: AsyncClient, test_review: Review):
        """Test getting a specific review by ID - GET /reviews/<id> (public)"""
        response = await async_client.get(f"/api/v1/reviews/{test_review.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_review.id
        assert data["rating"] == test_review.rating
        assert data["review_text"] == test_review.review_text
        assert data["book_id"] == test_review.book_id
        assert data["user_id"] == test_review.user_id

    async def test_get_nonexistent_review(self, async_client: AsyncClient):
        """Test getting a review that doesn't exist"""
        response = await async_client.get("/api/v1/reviews/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
    
    # =========================================================================
    # Update Review Tests
    # =========================================================================

    async def test_update_review_requires_auth(
        self,
        async_client: AsyncClient,
        test_review: Review
    ):
        """Test that updating a review requires authentication"""
        update_data = {"rating": 5.0}
        
        response = await async_client.put(
            f"/api/v1/reviews/{test_review.id}",
            json=update_data
        )
        assert response.status_code in [401, 403]

    async def test_update_review_owner(
        self,
        async_client: AsyncClient,
        test_review: Review,
        auth_headers: Dict[str, str]
    ):
        """Test updating a review as the owner - PUT /reviews/<id>"""
        update_data = {
            "rating": 5.0,
            "review_text": "Updated: This book is absolutely fantastic!"
        }
        
        response = await async_client.put(
            f"/api/v1/reviews/{test_review.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["rating"] == update_data["rating"]
        assert data["review_text"] == update_data["review_text"]

    async def test_update_review_admin(
        self,
        async_client: AsyncClient,
        test_review: Review,
        admin_auth_headers: Dict[str, str]
    ):
        """Test updating any review as admin"""
        update_data = {
            "rating": 4.0,
            "review_text": "Admin modified this review for moderation"
        }
        
        response = await async_client.put(
            f"/api/v1/reviews/{test_review.id}",
            json=update_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["rating"] == update_data["rating"]

    async def test_update_nonexistent_review(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test updating a review that doesn't exist"""
        update_data = {"rating": 5.0}
        response = await async_client.put(
            "/api/v1/reviews/99999",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 404
    
    # =========================================================================
    # Delete Review Tests
    # =========================================================================

    async def test_delete_review_requires_auth(
        self,
        async_client: AsyncClient,
        test_review: Review
    ):
        """Test that deleting a review requires authentication"""
        response = await async_client.delete(f"/api/v1/reviews/{test_review.id}")
        assert response.status_code in [401, 403]

    async def test_delete_review_owner(
        self,
        async_client: AsyncClient,
        test_review: Review,
        auth_headers: Dict[str, str]
    ):
        """Test deleting a review as the owner - DELETE /reviews/<id>"""
        response = await async_client.delete(
            f"/api/v1/reviews/{test_review.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        # Verify review is deleted
        response = await async_client.get(f"/api/v1/reviews/{test_review.id}")
        assert response.status_code == 404

    async def test_delete_review_admin(
        self,
        async_client: AsyncClient,
        test_review: Review,
        admin_auth_headers: Dict[str, str]
    ):
        """Test deleting any review as admin"""
        response = await async_client.delete(
            f"/api/v1/reviews/{test_review.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200

    async def test_delete_nonexistent_review(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test deleting a review that doesn't exist"""
        response = await async_client.delete(
            "/api/v1/reviews/99999",
            headers=auth_headers
        )
        assert response.status_code == 404
    
    # =========================================================================
    # Filter Tests (Public)
    # =========================================================================

    async def test_filter_reviews_by_book(self, async_client: AsyncClient, test_review: Review):
        """Test filtering reviews by book_id"""
        response = await async_client.get(f"/api/v1/reviews/?book_id={test_review.book_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1
        assert all(review["book_id"] == test_review.book_id for review in data)

    async def test_filter_reviews_by_user(self, async_client: AsyncClient, test_review: Review):
        """Test filtering reviews by user_id"""
        response = await async_client.get(f"/api/v1/reviews/?user_id={test_review.user_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1
        assert all(review["user_id"] == test_review.user_id for review in data)
    
    # =========================================================================
    # AI Summary Tests (Public)
    # =========================================================================

    async def test_get_book_review_summary(self, async_client: AsyncClient, test_review: Review):
        """Test getting AI-generated summary of reviews for a book (public)"""
        response = await async_client.get(f"/api/v1/reviews/book/{test_review.book_id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == test_review.book_id
        assert "summary" in data
    
    # =========================================================================
    # Pagination Tests (Public)
    # =========================================================================

    async def test_review_pagination(
        self,
        async_client: AsyncClient
    ):
        """Test review pagination"""
        response = await async_client.get("/api/v1/reviews/?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2
