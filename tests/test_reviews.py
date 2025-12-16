"""
Tests for review-related API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.reviews import Review
from app.models.books import Book
from app.models.users import User


@pytest.mark.asyncio
class TestReviews:
    async def test_create_review(self, client: TestClient, test_book: Book, test_user: User):
        """Test creating a new review"""
        review_data = {
            "book_id": test_book.id,
            "rating": 4.0,
            "title": "Good Book",
            "content": "This is a good book that I enjoyed reading."
        }
        
        response = client.post("/api/v1/reviews/", json=review_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == review_data["book_id"]
        assert data["rating"] == review_data["rating"]
        assert data["title"] == review_data["title"]
        assert data["content"] == review_data["content"]

    async def test_get_reviews(self, client: TestClient, test_review: Review):
        """Test getting all reviews"""
        response = client.get("/api/v1/reviews/")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1
        assert any(review["id"] == test_review.id for review in data)

    async def test_get_review_by_id(self, client: TestClient, test_review: Review):
        """Test getting a specific review by ID"""
        response = client.get(f"/api/v1/reviews/{test_review.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_review.id
        assert data["rating"] == test_review.rating
        assert data["title"] == test_review.title

    async def test_get_nonexistent_review(self, client: TestClient):
        """Test getting a review that doesn't exist"""
        response = client.get("/api/v1/reviews/99999")
        assert response.status_code == 404

    async def test_update_review(self, client: TestClient, test_review: Review):
        """Test updating a review"""
        update_data = {
            "rating": 5.0,
            "title": "Excellent Book!",
            "content": "Updated: This book is absolutely fantastic!"
        }
        
        response = client.put(f"/api/v1/reviews/{test_review.id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["rating"] == update_data["rating"]
        assert data["title"] == update_data["title"]
        assert data["content"] == update_data["content"]

    async def test_delete_review(self, client: TestClient, test_review: Review):
        """Test deleting a review"""
        response = client.delete(f"/api/v1/reviews/{test_review.id}")
        assert response.status_code == 200
        
        # Verify review is deleted
        response = client.get(f"/api/v1/reviews/{test_review.id}")
        assert response.status_code == 404

    async def test_filter_reviews_by_book(self, client: TestClient, test_review: Review):
        """Test filtering reviews by book"""
        response = client.get(f"/api/v1/reviews/?book_id={test_review.book_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1
        assert all(review["book_id"] == test_review.book_id for review in data)

    async def test_filter_reviews_by_user(self, client: TestClient, test_review: Review):
        """Test filtering reviews by user"""
        response = client.get(f"/api/v1/reviews/?user_id={test_review.user_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1
        assert all(review["user_id"] == test_review.user_id for review in data)

    async def test_get_book_review_summary(self, client: TestClient, test_review: Review):
        """Test getting AI-generated summary of reviews for a book"""
        response = client.get(f"/api/v1/reviews/book/{test_review.book_id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == test_review.book_id
        assert "summary" in data

    async def test_create_review_for_book_endpoint(self, client: TestClient, test_book: Book):
        """Test creating review through book endpoint"""
        review_data = {
            "user_id": 1,  # This would normally come from JWT token
            "rating": 3.5,
            "title": "Decent Book",
            "content": "It was okay, not bad but not great either."
        }
        
        response = client.post(f"/api/v1/books/{test_book.id}/reviews", json=review_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == test_book.id
        assert data["rating"] == review_data["rating"]

    async def test_get_book_reviews_endpoint(self, client: TestClient, test_book: Book):
        """Test getting all reviews for a book through book endpoint"""
        response = client.get(f"/api/v1/books/{test_book.id}/reviews")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

    async def test_review_pagination(self, client: TestClient):
        """Test review pagination"""
        response = client.get("/api/v1/reviews/?skip=0&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) <= 10
