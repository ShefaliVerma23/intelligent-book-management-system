"""
Tests for book-related API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.books import Book
from app.models.users import User


@pytest.mark.asyncio
class TestBooks:
    async def test_create_book(self, client: TestClient):
        """Test creating a new book"""
        book_data = {
            "title": "New Test Book",
            "author": "New Test Author",
            "isbn": "9876543210987",
            "genre": "Science Fiction",
            "publication_year": 2024,
            "description": "A new test book",
            "pages": 250
        }
        
        response = client.post("/api/v1/books/", json=book_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == book_data["title"]
        assert data["author"] == book_data["author"]
        assert data["isbn"] == book_data["isbn"]

    async def test_get_books(self, client: TestClient, test_book: Book):
        """Test getting all books"""
        response = client.get("/api/v1/books/")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1
        assert any(book["id"] == test_book.id for book in data)

    async def test_get_book_by_id(self, client: TestClient, test_book: Book):
        """Test getting a specific book by ID"""
        response = client.get(f"/api/v1/books/{test_book.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_book.id
        assert data["title"] == test_book.title
        assert data["author"] == test_book.author

    async def test_get_nonexistent_book(self, client: TestClient):
        """Test getting a book that doesn't exist"""
        response = client.get("/api/v1/books/99999")
        assert response.status_code == 404

    async def test_update_book(self, client: TestClient, test_book: Book):
        """Test updating a book"""
        update_data = {
            "title": "Updated Test Book",
            "description": "Updated description"
        }
        
        response = client.put(f"/api/v1/books/{test_book.id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["title"] == update_data["title"]
        assert data["description"] == update_data["description"]
        assert data["author"] == test_book.author  # Unchanged

    async def test_delete_book(self, client: TestClient, test_book: Book):
        """Test deleting a book"""
        response = client.delete(f"/api/v1/books/{test_book.id}")
        assert response.status_code == 200
        
        # Verify book is deleted
        response = client.get(f"/api/v1/books/{test_book.id}")
        assert response.status_code == 404

    async def test_filter_books_by_genre(self, client: TestClient, test_book: Book):
        """Test filtering books by genre"""
        response = client.get(f"/api/v1/books/?genre={test_book.genre}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1
        assert all(book["genre"] == test_book.genre for book in data if book["genre"])

    async def test_filter_books_by_author(self, client: TestClient, test_book: Book):
        """Test filtering books by author"""
        response = client.get(f"/api/v1/books/?author={test_book.author}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1
        assert all(book["author"] == test_book.author for book in data)

    async def test_search_books(self, client: TestClient, test_book: Book):
        """Test searching books"""
        search_term = test_book.title.split()[0]  # Use first word of title
        response = client.get(f"/api/v1/books/?search={search_term}")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1

    async def test_generate_book_summary(self, client: TestClient, test_book: Book):
        """Test generating AI summary for a book"""
        response = client.post(f"/api/v1/books/{test_book.id}/generate-summary")
        assert response.status_code == 200
        
        data = response.json()
        assert "summary" in data
        assert data["book_id"] == test_book.id

    async def test_get_book_summary(self, client: TestClient, test_book: Book):
        """Test getting book summary with reviews"""
        response = client.get(f"/api/v1/books/{test_book.id}/summary")
        assert response.status_code == 200
        
        data = response.json()
        assert data["book_id"] == test_book.id
        assert data["title"] == test_book.title
        assert "average_rating" in data
        assert "total_reviews" in data
