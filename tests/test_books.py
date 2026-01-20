"""
Tests for book-related API endpoints

Tests cover:
- CRUD operations (Create, Read, Update, Delete)
- Filtering and search
- Pagination
- AI summary generation
- Review management via books
- Authentication requirements

Note: 
- Protected endpoints require authentication headers
- POST operations return 201 Created
- Successful operations return 200 OK
"""
import pytest
from httpx import AsyncClient
from typing import Dict

from app.models.books import Book
from app.models.users import User


@pytest.mark.asyncio
class TestBooks:
    """Test all book CRUD operations and related endpoints"""
    
    # =========================================================================
    # Create Book Tests (Admin only) - Returns 201 Created
    # =========================================================================
    
    async def test_create_book_requires_auth(self, async_client: AsyncClient):
        """Test that creating a book requires authentication"""
        book_data = {
            "title": "New Test Book",
            "author": "New Test Author"
        }
        
        response = await async_client.post("/api/v1/books/", json=book_data)
        assert response.status_code in [401, 403]
    
    async def test_create_book_requires_admin(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test that creating a book requires admin privileges"""
        book_data = {
            "title": "New Test Book",
            "author": "New Test Author"
        }
        
        response = await async_client.post(
            "/api/v1/books/",
            json=book_data,
            headers=auth_headers  # Regular user, not admin
        )
        assert response.status_code == 403
    
    async def test_create_book_admin(
        self,
        async_client: AsyncClient,
        admin_auth_headers: Dict[str, str]
    ):
        """Test creating a new book - POST /books (admin) - returns 201"""
        book_data = {
            "title": "New Test Book",
            "author": "New Test Author",
            "genre": "Science Fiction",
            "year_published": 2024,
            "summary": "A new test book about science fiction adventures."
        }
        
        response = await async_client.post(
            "/api/v1/books/",
            json=book_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 201  # Created
        
        data = response.json()
        assert data["title"] == book_data["title"]
        assert data["author"] == book_data["author"]
        assert data["genre"] == book_data["genre"]
        assert data["year_published"] == book_data["year_published"]
        assert data["summary"] == book_data["summary"]
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_book_minimal_admin(
        self,
        async_client: AsyncClient,
        admin_auth_headers: Dict[str, str]
    ):
        """Test creating a book with only required fields (admin)"""
        book_data = {
            "title": "Minimal Book",
            "author": "Minimal Author"
        }
        
        response = await async_client.post(
            "/api/v1/books/",
            json=book_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 201  # Created
        
        data = response.json()
        assert data["title"] == book_data["title"]
        assert data["author"] == book_data["author"]

    async def test_create_book_invalid_data(
        self,
        async_client: AsyncClient,
        admin_auth_headers: Dict[str, str]
    ):
        """Test creating a book with invalid data"""
        # Missing required fields
        book_data = {
            "genre": "Fiction"
        }
        
        response = await async_client.post(
            "/api/v1/books/",
            json=book_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 422  # Validation error
    
    # =========================================================================
    # Read Book Tests (Public)
    # =========================================================================

    async def test_get_books(self, async_client: AsyncClient, test_book: Book):
        """Test getting all books - GET /books (public)"""
        response = await async_client.get("/api/v1/books/")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Find our test book
        book_found = any(book["id"] == test_book.id for book in data)
        assert book_found

    async def test_get_book_by_id(self, async_client: AsyncClient, test_book: Book):
        """Test getting a specific book by ID - GET /books/<id> (public)"""
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
    
    # =========================================================================
    # Update Book Tests (Admin only)
    # =========================================================================

    async def test_update_book_requires_auth(
        self,
        async_client: AsyncClient,
        test_book: Book
    ):
        """Test that updating a book requires authentication"""
        update_data = {"title": "Updated Title"}
        
        response = await async_client.put(
            f"/api/v1/books/{test_book.id}",
            json=update_data
        )
        assert response.status_code in [401, 403]
    
    async def test_update_book_requires_admin(
        self,
        async_client: AsyncClient,
        test_book: Book,
        auth_headers: Dict[str, str]
    ):
        """Test that updating a book requires admin privileges"""
        update_data = {"title": "Updated Title"}
        
        response = await async_client.put(
            f"/api/v1/books/{test_book.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 403

    async def test_update_book_admin(
        self,
        async_client: AsyncClient,
        test_book: Book,
        admin_auth_headers: Dict[str, str]
    ):
        """Test updating a book - PUT /books/<id> (admin)"""
        update_data = {
            "title": "Updated Test Book",
            "summary": "Updated summary for testing."
        }
        
        response = await async_client.put(
            f"/api/v1/books/{test_book.id}",
            json=update_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["summary"] == update_data["summary"]
        # Unchanged fields should remain the same
        assert data["author"] == test_book.author
        assert data["genre"] == test_book.genre

    async def test_update_nonexistent_book(
        self,
        async_client: AsyncClient,
        admin_auth_headers: Dict[str, str]
    ):
        """Test updating a book that doesn't exist"""
        update_data = {"title": "New Title"}
        response = await async_client.put(
            "/api/v1/books/99999",
            json=update_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 404
    
    # =========================================================================
    # Delete Book Tests (Admin only)
    # =========================================================================

    async def test_delete_book_requires_auth(
        self,
        async_client: AsyncClient,
        test_book: Book
    ):
        """Test that deleting a book requires authentication"""
        response = await async_client.delete(f"/api/v1/books/{test_book.id}")
        assert response.status_code in [401, 403]
    
    async def test_delete_book_requires_admin(
        self,
        async_client: AsyncClient,
        test_book: Book,
        auth_headers: Dict[str, str]
    ):
        """Test that deleting a book requires admin privileges"""
        response = await async_client.delete(
            f"/api/v1/books/{test_book.id}",
            headers=auth_headers
        )
        assert response.status_code == 403

    async def test_delete_book_admin(
        self,
        async_client: AsyncClient,
        test_book: Book,
        admin_auth_headers: Dict[str, str]
    ):
        """Test deleting a book - DELETE /books/<id> (admin)"""
        response = await async_client.delete(
            f"/api/v1/books/{test_book.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        # Verify book is deleted
        response = await async_client.get(f"/api/v1/books/{test_book.id}")
        assert response.status_code == 404

    async def test_delete_nonexistent_book(
        self,
        async_client: AsyncClient,
        admin_auth_headers: Dict[str, str]
    ):
        """Test deleting a book that doesn't exist"""
        response = await async_client.delete(
            "/api/v1/books/99999",
            headers=admin_auth_headers
        )
        assert response.status_code == 404
    
    # =========================================================================
    # Filter and Search Tests (Public)
    # =========================================================================

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

    async def test_pagination(
        self,
        async_client: AsyncClient,
        admin_auth_headers: Dict[str, str]
    ):
        """Test book pagination"""
        # Create multiple books first
        for i in range(5):
            await async_client.post(
                "/api/v1/books/",
                json={
                    "title": f"Pagination Test Book {i}",
                    "author": f"Author {i}",
                    "genre": "Test"
                },
                headers=admin_auth_headers
            )
        
        # Test skip and limit
        response = await async_client.get("/api/v1/books/?skip=0&limit=2")
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2
    
    # =========================================================================
    # AI Summary Tests (Admin only)
    # =========================================================================

    async def test_generate_book_summary_requires_admin(
        self,
        async_client: AsyncClient,
        test_book: Book,
        auth_headers: Dict[str, str]
    ):
        """Test that generating AI summary requires admin"""
        response = await async_client.post(
            f"/api/v1/books/{test_book.id}/generate-summary",
            headers=auth_headers
        )
        assert response.status_code == 403

    async def test_generate_book_summary_admin(
        self,
        async_client: AsyncClient,
        test_book: Book,
        admin_auth_headers: Dict[str, str]
    ):
        """Test generating AI summary for a book - POST /books/<id>/generate-summary (admin)"""
        response = await async_client.post(
            f"/api/v1/books/{test_book.id}/generate-summary",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data
        assert data["book_id"] == test_book.id
        assert len(data["summary"]) > 0

    async def test_get_book_summary_with_reviews(
        self,
        async_client: AsyncClient,
        test_book: Book
    ):
        """Test getting book summary with aggregated reviews - GET /books/<id>/summary (public)"""
        response = await async_client.get(f"/api/v1/books/{test_book.id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == test_book.id
        assert data["title"] == test_book.title
        assert data["author"] == test_book.author
        assert "summary" in data
        assert "review_summary" in data
    
    # =========================================================================
    # Book Reviews Tests - Returns 201 for create
    # =========================================================================

    async def test_add_review_to_book_requires_auth(
        self,
        async_client: AsyncClient,
        test_book: Book
    ):
        """Test that adding a review requires authentication"""
        review_data = {
            "rating": 4.5,
            "review_text": "Great book! Really enjoyed it very much."
        }
        
        response = await async_client.post(
            f"/api/v1/books/{test_book.id}/reviews",
            json=review_data
        )
        assert response.status_code in [401, 403]

    async def test_add_review_to_book(
        self,
        async_client: AsyncClient,
        test_book: Book,
        test_user: User,
        auth_headers: Dict[str, str]
    ):
        """Test adding a review for a book - POST /books/<id>/reviews"""
        review_data = {
            "rating": 4.5,
            "review_text": "Great book! Really enjoyed it very much."
        }
        
        response = await async_client.post(
            f"/api/v1/books/{test_book.id}/reviews",
            json=review_data,
            headers=auth_headers
        )
        # Note: This endpoint uses ReviewResponse which returns via BookService
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == test_book.id
        assert data["rating"] == review_data["rating"]
        assert data["review_text"] == review_data["review_text"]
        assert data["user_id"] == test_user.id  # Should be set from auth

    async def test_get_book_reviews(self, async_client: AsyncClient, test_book: Book, test_review):
        """Test getting all reviews for a book - GET /books/<id>/reviews (public)"""
        response = await async_client.get(f"/api/v1/books/{test_book.id}/reviews")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(review["id"] == test_review.id for review in data)
