"""
Tests for user-related API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.users import User


@pytest.mark.asyncio
class TestUsers:
    async def test_create_user(self, client: TestClient):
        """Test creating a new user"""
        user_data = {
            "username": "createduser",
            "email": "created@example.com",
            "password": "password123",
            "full_name": "Created User"
        }
        
        response = client.post("/api/v1/users/", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]

    async def test_get_users(self, client: TestClient, test_user: User):
        """Test getting all users"""
        response = client.get("/api/v1/users/")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) >= 1
        assert any(user["id"] == test_user.id for user in data)

    async def test_get_user_by_id(self, client: TestClient, test_user: User):
        """Test getting a specific user by ID"""
        response = client.get(f"/api/v1/users/{test_user.id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email

    async def test_get_nonexistent_user(self, client: TestClient):
        """Test getting a user that doesn't exist"""
        response = client.get("/api/v1/users/99999")
        assert response.status_code == 404

    async def test_update_user(self, client: TestClient, test_user: User):
        """Test updating a user"""
        update_data = {
            "full_name": "Updated Test User",
            "bio": "Updated bio"
        }
        
        response = client.put(f"/api/v1/users/{test_user.id}", json=update_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["bio"] == update_data["bio"]
        assert data["username"] == test_user.username  # Unchanged

    async def test_delete_user(self, client: TestClient, test_user: User):
        """Test deleting a user"""
        response = client.delete(f"/api/v1/users/{test_user.id}")
        assert response.status_code == 200
        
        # Verify user is deleted
        response = client.get(f"/api/v1/users/{test_user.id}")
        assert response.status_code == 404

    async def test_create_user_duplicate_email(self, client: TestClient, test_user: User):
        """Test creating user with duplicate email"""
        user_data = {
            "username": "anotheruser2",
            "email": test_user.email,  # Duplicate email
            "password": "password123",
            "full_name": "Another User"
        }
        
        response = client.post("/api/v1/users/", json=user_data)
        assert response.status_code == 400

    async def test_create_user_duplicate_username(self, client: TestClient, test_user: User):
        """Test creating user with duplicate username"""
        user_data = {
            "username": test_user.username,  # Duplicate username
            "email": "different2@example.com",
            "password": "password123",
            "full_name": "Another User"
        }
        
        response = client.post("/api/v1/users/", json=user_data)
        assert response.status_code == 400

    async def test_user_pagination(self, client: TestClient):
        """Test user pagination"""
        response = client.get("/api/v1/users/?skip=0&limit=10")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) <= 10
