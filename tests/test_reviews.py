"""
Tests for review-related API endpoints
"""
import pytest
from httpx import AsyncClient

from app.models.reviews import Review
from app.models.books import Book
from app.models.users import User


@pytest.mark.asyncio
class TestReviews:
    """Test all review CRUD operations and related endpoints"""

    async def test_create_review(self, async_client: AsyncClient, test_book: Book, test_user: User):
        """Test creating a new review - POST /reviews"""
        review_data = {
            "book_id": test_book.id,
            "user_id": test_user.id,
            "rating": 4.0,
            "review_text": "This is a good book that I enjoyed reading."
        }
        
        response = await async_client.post("/api/v1/reviews/", json=review_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == review_data["book_id"]
        assert data["rating"] == review_data["rating"]
        assert data["review_text"] == review_data["review_text"]
        assert "id" in data
        assert "created_at" in data

    async def test_create_review_rating_validation(self, async_client: AsyncClient, test_book: Book):
        """Test that rating must be between 1 and 5"""
        # Rating too low
        review_data = {
            "book_id": test_book.id,
            "rating": 0.5,
            "review_text": "Bad rating"
        }
        response = await async_client.post("/api/v1/reviews/", json=review_data)
        assert response.status_code == 422
        
        # Rating too high
        review_data["rating"] = 6.0
        response = await async_client.post("/api/v1/reviews/", json=review_data)
        assert response.status_code == 422

    async def test_get_reviews(self, async_client: AsyncClient, test_review: Review):
        """Test getting all reviews - GET /reviews"""
        response = await async_client.get("/api/v1/reviews/")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(review["id"] == test_review.id for review in data)

    async def test_get_review_by_id(self, async_client: AsyncClient, test_review: Review):
        """Test getting a specific review by ID - GET /reviews/<id>"""
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

    async def test_update_review(self, async_client: AsyncClient, test_review: Review):
        """Test updating a review - PUT /reviews/<id>"""
        update_data = {
            "rating": 5.0,
            "review_text": "Updated: This book is absolutely fantastic!"
        }
        
        response = await async_client.put(f"/api/v1/reviews/{test_review.id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["rating"] == update_data["rating"]
        assert data["review_text"] == update_data["review_text"]

    async def test_update_nonexistent_review(self, async_client: AsyncClient):
        """Test updating a review that doesn't exist"""
        update_data = {"rating": 5.0}
        response = await async_client.put("/api/v1/reviews/99999", json=update_data)
        assert response.status_code == 404

    async def test_delete_review(self, async_client: AsyncClient, test_review: Review):
        """Test deleting a review - DELETE /reviews/<id>"""
        response = await async_client.delete(f"/api/v1/reviews/{test_review.id}")
        assert response.status_code == 200
        
        # Verify review is deleted
        response = await async_client.get(f"/api/v1/reviews/{test_review.id}")
        assert response.status_code == 404

    async def test_delete_nonexistent_review(self, async_client: AsyncClient):
        """Test deleting a review that doesn't exist"""
        response = await async_client.delete("/api/v1/reviews/99999")
        assert response.status_code == 404

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

    async def test_get_book_review_summary(self, async_client: AsyncClient, test_review: Review):
        """Test getting AI-generated summary of reviews for a book"""
        response = await async_client.get(f"/api/v1/reviews/book/{test_review.book_id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == test_review.book_id
        assert "summary" in data

    async def test_review_pagination(self, async_client: AsyncClient, test_book: Book, test_user: User):
        """Test review pagination"""
        # Create multiple reviews
        for i in range(5):
            await async_client.post("/api/v1/reviews/", json={
                "book_id": test_book.id,
                "user_id": test_user.id,
                "rating": 3.0 + (i * 0.5),
                "review_text": f"Review number {i}"
            })
        
        response = await async_client.get("/api/v1/reviews/?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2
