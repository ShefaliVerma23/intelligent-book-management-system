"""
Tests for recommendation and AI summary endpoints
"""
import pytest
from httpx import AsyncClient

from app.models.books import Book
from app.models.users import User
from app.models.reviews import Review


@pytest.mark.asyncio
class TestRecommendations:
    """Test recommendation endpoints"""

    async def test_get_popular_books(self, async_client: AsyncClient, test_book: Book, test_review: Review):
        """Test getting popular books - GET /recommendations/popular"""
        response = await async_client.get("/api/v1/recommendations/popular")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

    async def test_get_popular_books_with_limit(self, async_client: AsyncClient, test_book: Book, test_review: Review):
        """Test getting popular books with limit"""
        response = await async_client.get("/api/v1/recommendations/popular?limit=5")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) <= 5

    async def test_get_popular_books_by_genre(self, async_client: AsyncClient, test_book: Book, test_review: Review):
        """Test getting popular books filtered by genre"""
        response = await async_client.get(f"/api/v1/recommendations/popular?genre={test_book.genre}")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)

    async def test_get_similar_books(self, async_client: AsyncClient, test_book: Book, test_book2: Book):
        """Test getting similar books - GET /recommendations/similar/<id>"""
        response = await async_client.get(f"/api/v1/recommendations/similar/{test_book.id}")
        # May return 404 if no similar books or 200 with list
        assert response.status_code in [200, 404]
        
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, list)
            # Should not include the same book
            assert all(book["id"] != test_book.id for book in data)

    async def test_get_similar_books_nonexistent(self, async_client: AsyncClient):
        """Test getting similar books for nonexistent book"""
        response = await async_client.get("/api/v1/recommendations/similar/99999")
        assert response.status_code == 404


@pytest.mark.asyncio
class TestGenerateSummary:
    """Test the POST /generate-summary endpoint"""

    async def test_generate_summary(self, async_client: AsyncClient):
        """Test generating summary for content - POST /generate-summary"""
        request_data = {
            "content": "This is a test book about a young wizard who discovers magical powers. "
                       "He attends a school for wizards and makes friends along the way. "
                       "Together they face challenges and defeat evil forces."
        }
        
        response = await async_client.post("/api/v1/generate-summary", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data
        assert "content_length" in data
        assert "generated_at" in data
        assert data["content_length"] == len(request_data["content"])
        assert len(data["summary"]) > 0

    async def test_generate_summary_empty_content(self, async_client: AsyncClient):
        """Test generating summary with empty content"""
        request_data = {
            "content": ""
        }
        
        response = await async_client.post("/api/v1/generate-summary", json=request_data)
        assert response.status_code == 400

    async def test_generate_summary_whitespace_content(self, async_client: AsyncClient):
        """Test generating summary with whitespace-only content"""
        request_data = {
            "content": "   "
        }
        
        response = await async_client.post("/api/v1/generate-summary", json=request_data)
        assert response.status_code == 400

    async def test_generate_summary_long_content(self, async_client: AsyncClient):
        """Test generating summary for long content"""
        long_content = "This is a test sentence. " * 100
        request_data = {
            "content": long_content
        }
        
        response = await async_client.post("/api/v1/generate-summary", json=request_data)
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["summary"]) > 0
        # Summary should be shorter than original content
        assert len(data["summary"]) < len(long_content)


@pytest.mark.asyncio
class TestBookSummaryGeneration:
    """Test AI summary generation for books"""

    async def test_generate_book_summary(self, async_client: AsyncClient, test_book: Book):
        """Test generating AI summary for existing book"""
        response = await async_client.post(f"/api/v1/books/{test_book.id}/generate-summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == test_book.id
        assert "summary" in data
        assert len(data["summary"]) > 0

    async def test_generate_summary_nonexistent_book(self, async_client: AsyncClient):
        """Test generating summary for nonexistent book"""
        response = await async_client.post("/api/v1/books/99999/generate-summary")
        assert response.status_code == 404

    async def test_get_book_summary_endpoint(self, async_client: AsyncClient, test_book: Book):
        """Test getting book summary with review aggregation"""
        response = await async_client.get(f"/api/v1/books/{test_book.id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == test_book.id
        assert data["title"] == test_book.title
        assert data["author"] == test_book.author
        assert "summary" in data
        assert "review_summary" in data


@pytest.mark.asyncio
class TestReviewSummary:
    """Test AI summary generation for reviews"""

    async def test_get_review_summary(self, async_client: AsyncClient, test_review: Review):
        """Test getting AI summary of reviews for a book"""
        response = await async_client.get(f"/api/v1/reviews/book/{test_review.book_id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == test_review.book_id
        assert "summary" in data

    async def test_review_summary_no_reviews(self, async_client: AsyncClient, test_book: Book):
        """Test review summary for book with no reviews"""
        # Create a new book with no reviews
        response = await async_client.post("/api/v1/books/", json={
            "title": "Book Without Reviews",
            "author": "Unknown Author",
            "genre": "Mystery"
        })
        new_book_id = response.json()["id"]
        
        response = await async_client.get(f"/api/v1/reviews/book/{new_book_id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data

