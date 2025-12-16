"""
Tests for authentication-related API endpoints
"""
import pytest
from fastapi.testclient import TestClient

from app.models.users import User


@pytest.mark.asyncio
class TestAuthentication:
    async def test_register_user(self, client: TestClient):
        """Test user registration"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword123",
            "full_name": "New User"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert "password" not in data  # Password should not be returned

    async def test_register_duplicate_email(self, client: TestClient, test_user: User):
        """Test registering with duplicate email"""
        user_data = {
            "username": "anotheruser",
            "email": test_user.email,  # Duplicate email
            "password": "password123",
            "full_name": "Another User"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        assert "Email already registered" in response.json()["detail"]

    async def test_register_duplicate_username(self, client: TestClient, test_user: User):
        """Test registering with duplicate username"""
        user_data = {
            "username": test_user.username,  # Duplicate username
            "email": "different@example.com",
            "password": "password123",
            "full_name": "Another User"
        }
        
        response = client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        assert "Username already taken" in response.json()["detail"]

    async def test_login_success(self, client: TestClient, test_user: User):
        """Test successful login"""
        form_data = {
            "username": test_user.username,
            "password": "testpassword123"
        }
        
        response = client.post("/api/v1/auth/login", data=form_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, client: TestClient, test_user: User):
        """Test login with wrong password"""
        form_data = {
            "username": test_user.username,
            "password": "wrongpassword"
        }
        
        response = client.post("/api/v1/auth/login", data=form_data)
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, client: TestClient):
        """Test login with non-existent user"""
        form_data = {
            "username": "nonexistentuser",
            "password": "password123"
        }
        
        response = client.post("/api/v1/auth/login", data=form_data)
        assert response.status_code == 401

    def get_auth_header(self, client: TestClient, test_user: User) -> dict:
        """Helper method to get authentication header"""
        form_data = {
            "username": test_user.username,
            "password": "testpassword123"
        }
        
        response = client.post("/api/v1/auth/login", data=form_data)
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    async def test_get_current_user(self, client: TestClient, test_user: User):
        """Test getting current user profile"""
        headers = self.get_auth_header(client, test_user)
        
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email

    async def test_get_current_user_without_token(self, client: TestClient):
        """Test getting current user without token"""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401

    async def test_get_current_user_invalid_token(self, client: TestClient):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalidtoken"}
        
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401

    async def test_logout(self, client: TestClient):
        """Test logout endpoint"""
        response = client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
