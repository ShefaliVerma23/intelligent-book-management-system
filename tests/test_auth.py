"""
Tests for authentication-related API endpoints
"""
import pytest
from httpx import AsyncClient

from app.models.users import User


@pytest.mark.asyncio
class TestAuthentication:
    """Test authentication endpoints"""

    async def test_register_user(self, async_client: AsyncClient):
        """Test user registration - POST /auth/register"""
        user_data = {
            "username": "newuser",
            "email": "newuser@example.com",
            "password": "newpassword123",
            "full_name": "New User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert "password" not in data  # Password should not be returned

    async def test_register_duplicate_email(self, async_client: AsyncClient, test_user: User):
        """Test registering with duplicate email"""
        user_data = {
            "username": "anotheruser",
            "email": test_user.email,  # Duplicate email
            "password": "password123",
            "full_name": "Another User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()

    async def test_register_duplicate_username(self, async_client: AsyncClient, test_user: User):
        """Test registering with duplicate username"""
        user_data = {
            "username": test_user.username,  # Duplicate username
            "email": "different@example.com",
            "password": "password123",
            "full_name": "Another User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        assert "already" in response.json()["detail"].lower()

    async def test_login_success(self, async_client: AsyncClient, test_user: User):
        """Test successful login - POST /auth/login"""
        form_data = {
            "username": test_user.username,
            "password": "testpassword123"
        }
        
        response = await async_client.post("/api/v1/auth/login", data=form_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    async def test_login_wrong_password(self, async_client: AsyncClient, test_user: User):
        """Test login with wrong password"""
        form_data = {
            "username": test_user.username,
            "password": "wrongpassword"
        }
        
        response = await async_client.post("/api/v1/auth/login", data=form_data)
        assert response.status_code == 401

    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with non-existent user"""
        form_data = {
            "username": "nonexistentuser",
            "password": "password123"
        }
        
        response = await async_client.post("/api/v1/auth/login", data=form_data)
        assert response.status_code == 401

    async def get_auth_header(self, async_client: AsyncClient, username: str, password: str) -> dict:
        """Helper method to get authentication header"""
        form_data = {
            "username": username,
            "password": password
        }
        
        response = await async_client.post("/api/v1/auth/login", data=form_data)
        if response.status_code == 200:
            token = response.json()["access_token"]
            return {"Authorization": f"Bearer {token}"}
        return {}

    async def test_get_current_user(self, async_client: AsyncClient, test_user: User):
        """Test getting current user profile - GET /auth/me"""
        headers = await self.get_auth_header(async_client, test_user.username, "testpassword123")
        
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email

    async def test_get_current_user_without_token(self, async_client: AsyncClient):
        """Test getting current user without token"""
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code in [401, 403]

    async def test_get_current_user_invalid_token(self, async_client: AsyncClient):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalidtoken"}
        
        response = await async_client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401

    async def test_logout(self, async_client: AsyncClient):
        """Test logout endpoint - POST /auth/logout"""
        response = await async_client.post("/api/v1/auth/logout")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data

    async def test_password_validation(self, async_client: AsyncClient):
        """Test password must be at least 8 characters"""
        user_data = {
            "username": "shortpwduser",
            "email": "shortpwd@example.com",
            "password": "short",  # Too short
            "full_name": "Short Password User"
        }
        
        response = await async_client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 422  # Validation error
