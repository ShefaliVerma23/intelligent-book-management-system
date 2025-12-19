"""
Tests for book-related API endpoints
"""
import pytest
from httpx import AsyncClient

from app.models.books import Book


@pytest.mark.asyncio
class TestBooks:
    """Test all book CRUD operations and related endpoints"""
    
    async def test_create_book(self, async_client: AsyncClient):
        """Test creating a new book - POST /books"""
        book_data = {
            "title": "New Test Book",
            "author": "New Test Author",
            "genre": "Science Fiction",
            "year_published": 2024,
            "summary": "A new test book about science fiction adventures."
        }
        
        response = await async_client.post("/api/v1/books/", json=book_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == book_data["title"]
        assert data["author"] == book_data["author"]
        assert data["genre"] == book_data["genre"]
        assert data["year_published"] == book_data["year_published"]
        assert data["summary"] == book_data["summary"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_book_minimal(self, async_client: AsyncClient):
        """Test creating a book with only required fields"""
        book_data = {
            "title": "Minimal Book",
            "author": "Minimal Author"
        }
        
        response = await async_client.post("/api/v1/books/", json=book_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == book_data["title"]
        assert data["author"] == book_data["author"]

    async def test_create_book_invalid_data(self, async_client: AsyncClient):
        """Test creating a book with invalid data"""
        # Missing required fields
        book_data = {
            "genre": "Fiction"
        }
        
        response = await async_client.post("/api/v1/books/", json=book_data)
        assert response.status_code == 422  # Validation error

    async def test_get_books(self, async_client: AsyncClient, test_book: Book):
        """Test getting all books - GET /books"""
        response = await async_client.get("/api/v1/books/")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Find our test book
        book_found = any(book["id"] == test_book.id for book in data)
        assert book_found

    async def test_get_book_by_id(self, async_client: AsyncClient, test_book: Book):
        """Test getting a specific book by ID - GET /books/<id>"""
        response = await async_client.get(f"/api/v1/books/{test_book.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_book.id
        assert data["title"] == test_book.title
        assert data["author"] == test_book.author
        assert data["genre"] == test_book.genre
        assert data["year_published"] == test_book.year_published

    async def test_get_nonexistent_book(self, async_client: AsyncClient):
        """Test getting a book that doesn't exist"""
        response = await async_client.get("/api/v1/books/99999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_update_book(self, async_client: AsyncClient, test_book: Book):
        """Test updating a book - PUT /books/<id>"""
        update_data = {
            "title": "Updated Test Book",
            "summary": "Updated summary for testing."
        }
        
        response = await async_client.put(f"/api/v1/books/{test_book.id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["summary"] == update_data["summary"]
        # Unchanged fields should remain the same
        assert data["author"] == test_book.author
        assert data["genre"] == test_book.genre

    async def test_update_nonexistent_book(self, async_client: AsyncClient):
        """Test updating a book that doesn't exist"""
        update_data = {"title": "New Title"}
        response = await async_client.put("/api/v1/books/99999", json=update_data)
        assert response.status_code == 404

    async def test_delete_book(self, async_client: AsyncClient, test_book: Book):
        """Test deleting a book - DELETE /books/<id>"""
        response = await async_client.delete(f"/api/v1/books/{test_book.id}")
        assert response.status_code == 200
        
        # Verify book is deleted
        response = await async_client.get(f"/api/v1/books/{test_book.id}")
        assert response.status_code == 404

    async def test_delete_nonexistent_book(self, async_client: AsyncClient):
        """Test deleting a book that doesn't exist"""
        response = await async_client.delete("/api/v1/books/99999")
        assert response.status_code == 404

    async def test_filter_books_by_genre(self, async_client: AsyncClient, test_book: Book):
        """Test filtering books by genre"""
        response = await async_client.get(f"/api/v1/books/?genre={test_book.genre}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1
        # All returned books should match the genre filter
        for book in data:
            if book["genre"]:
                assert test_book.genre.lower() in book["genre"].lower()

    async def test_filter_books_by_author(self, async_client: AsyncClient, test_book: Book):
        """Test filtering books by author"""
        response = await async_client.get(f"/api/v1/books/?author={test_book.author}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1
        for book in data:
            assert test_book.author.lower() in book["author"].lower()

    async def test_search_books(self, async_client: AsyncClient, test_book: Book):
        """Test searching books by title/author/summary"""
        search_term = test_book.title.split()[0]  # Use first word of title
        response = await async_client.get(f"/api/v1/books/?search={search_term}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1

    async def test_pagination(self, async_client: AsyncClient):
        """Test book pagination"""
        # Create multiple books first
        for i in range(5):
            await async_client.post("/api/v1/books/", json={
                "title": f"Pagination Test Book {i}",
                "author": f"Author {i}",
                "genre": "Test"
            })
        
        # Test skip and limit
        response = await async_client.get("/api/v1/books/?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

    async def test_generate_book_summary(self, async_client: AsyncClient, test_book: Book):
        """Test generating AI summary for a book - POST /books/<id>/generate-summary"""
        response = await async_client.post(f"/api/v1/books/{test_book.id}/generate-summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data
        assert data["book_id"] == test_book.id
        assert len(data["summary"]) > 0

    async def test_get_book_summary_with_reviews(self, async_client: AsyncClient, test_book: Book):
        """Test getting book summary with aggregated reviews - GET /books/<id>/summary"""
        response = await async_client.get(f"/api/v1/books/{test_book.id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == test_book.id
        assert data["title"] == test_book.title
        assert data["author"] == test_book.author
        assert "summary" in data
        assert "review_summary" in data

    async def test_add_review_to_book(self, async_client: AsyncClient, test_book: Book, test_user):
        """Test adding a review for a book - POST /books/<id>/reviews"""
        review_data = {
            "user_id": test_user.id,
            "rating": 4.5,
            "review_text": "Great book! Really enjoyed it."
        }
        
        response = await async_client.post(f"/api/v1/books/{test_book.id}/reviews", json=review_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == test_book.id
        assert data["rating"] == review_data["rating"]
        assert data["review_text"] == review_data["review_text"]

    async def test_get_book_reviews(self, async_client: AsyncClient, test_book: Book, test_review):
        """Test getting all reviews for a book - GET /books/<id>/reviews"""
        response = await async_client.get(f"/api/v1/books/{test_book.id}/reviews")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(review["id"] == test_review.id for review in data)
