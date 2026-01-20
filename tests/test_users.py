"""
Tests for user-related API endpoints

Tests cover:
- User CRUD operations
- Self-registration via /auth/register (public)
- Admin user creation via /users/ (admin only)
- Profile viewing and updating
- Authorization requirements

Security:
- POST /users/ - Admin only
- GET /users/ - Admin only  
- GET /users/{id} - User can view self, admin can view all
- PUT /users/{id} - User can update self, admin can update all
- DELETE /users/{id} - Admin only
"""
import pytest
from httpx import AsyncClient
from typing import Dict

from app.models.users import User


@pytest.mark.asyncio
class TestUsers:
    """Test user CRUD operations"""
    
    # =========================================================================
    # Create User Tests (Admin only via /users/)
    # =========================================================================

    async def test_create_user_requires_auth(self, async_client: AsyncClient):
        """Test that creating a user via /users/ requires authentication"""
        user_data = {
            "username": "createduser",
            "email": "created@example.com",
            "password": "password123",
            "full_name": "Created User"
        }
        
        response = await async_client.post("/api/v1/users/", json=user_data)
        assert response.status_code in [401, 403]
    
    async def test_create_user_requires_admin(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test that creating a user via /users/ requires admin privileges"""
        user_data = {
            "username": "createduser",
            "email": "created@example.com",
            "password": "password123",
            "full_name": "Created User"
        }
        
        response = await async_client.post(
            "/api/v1/users/",
            json=user_data,
            headers=auth_headers  # Regular user, not admin
        )
        assert response.status_code == 403

    async def test_create_user_admin(
        self,
        async_client: AsyncClient,
        admin_auth_headers: Dict[str, str]
    ):
        """Test creating a new user - POST /users/ (admin only)"""
        user_data = {
            "username": "createduser",
            "email": "created@example.com",
            "password": "password123",
            "full_name": "Created User",
            "is_active": True,
            "is_admin": False
        }
        
        response = await async_client.post(
            "/api/v1/users/",
            json=user_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["username"] == user_data["username"].lower()  # Username is normalized
        assert data["email"] == user_data["email"].lower()  # Email is normalized
        assert data["full_name"] == user_data["full_name"]
    
    async def test_create_user_duplicate_email(
        self,
        async_client: AsyncClient,
        admin_auth_headers: Dict[str, str],
        test_user: User
    ):
        """Test creating user with duplicate email (admin)"""
        user_data = {
            "username": "anotheruser2",
            "email": test_user.email,  # Duplicate email
            "password": "password123",
            "full_name": "Another User"
        }
        
        response = await async_client.post(
            "/api/v1/users/",
            json=user_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 400

    async def test_create_user_duplicate_username(
        self,
        async_client: AsyncClient,
        admin_auth_headers: Dict[str, str],
        test_user: User
    ):
        """Test creating user with duplicate username (admin)"""
        user_data = {
            "username": test_user.username,  # Duplicate username
            "email": "different2@example.com",
            "password": "password123",
            "full_name": "Another User"
        }
        
        response = await async_client.post(
            "/api/v1/users/",
            json=user_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 400
    
    # =========================================================================
    # Get Users Tests (Admin only)
    # =========================================================================

    async def test_get_users_requires_auth(self, async_client: AsyncClient):
        """Test that listing users requires authentication"""
        response = await async_client.get("/api/v1/users/")
        assert response.status_code in [401, 403]
    
    async def test_get_users_requires_admin(
        self,
        async_client: AsyncClient,
        auth_headers: Dict[str, str]
    ):
        """Test that listing users requires admin privileges"""
        response = await async_client.get(
            "/api/v1/users/",
            headers=auth_headers  # Regular user
        )
        assert response.status_code == 403

    async def test_get_users_admin(
        self,
        async_client: AsyncClient,
        admin_auth_headers: Dict[str, str],
        test_user: User
    ):
        """Test getting all users - GET /users/ (admin only)"""
        response = await async_client.get(
            "/api/v1/users/",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        # Check that admin user is in the list
        assert any(user["is_admin"] for user in data)

    async def test_user_pagination(
        self,
        async_client: AsyncClient,
        admin_auth_headers: Dict[str, str]
    ):
        """Test user pagination (admin)"""
        response = await async_client.get(
            "/api/v1/users/?skip=0&limit=10",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert len(data) <= 10
    
    # =========================================================================
    # Get User by ID Tests
    # =========================================================================

    async def test_get_user_by_id_requires_auth(self, async_client: AsyncClient, test_user: User):
        """Test that getting a user by ID requires authentication"""
        response = await async_client.get(f"/api/v1/users/{test_user.id}")
        assert response.status_code in [401, 403]

    async def test_get_user_self(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: Dict[str, str]
    ):
        """Test getting own user profile - GET /users/<id>"""
        response = await async_client.get(
            f"/api/v1/users/{test_user.id}",
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == test_user.username
        assert data["email"] == test_user.email
    
    async def test_get_other_user_forbidden(
        self,
        async_client: AsyncClient,
        test_admin_user: User,
        auth_headers: Dict[str, str]
    ):
        """Test that regular users cannot view other users' profiles"""
        response = await async_client.get(
            f"/api/v1/users/{test_admin_user.id}",  # Try to view admin user
            headers=auth_headers  # As regular user
        )
        assert response.status_code == 403
    
    async def test_get_any_user_as_admin(
        self,
        async_client: AsyncClient,
        test_user: User,
        admin_auth_headers: Dict[str, str]
    ):
        """Test that admins can view any user's profile"""
        response = await async_client.get(
            f"/api/v1/users/{test_user.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["id"] == test_user.id

    async def test_get_nonexistent_user(
        self,
        async_client: AsyncClient,
        admin_auth_headers: Dict[str, str]
    ):
        """Test getting a user that doesn't exist"""
        response = await async_client.get(
            "/api/v1/users/99999",
            headers=admin_auth_headers
        )
        assert response.status_code == 404
    
    # =========================================================================
    # Update User Tests
    # =========================================================================

    async def test_update_user_requires_auth(self, async_client: AsyncClient, test_user: User):
        """Test that updating a user requires authentication"""
        update_data = {"full_name": "Updated Name"}
        
        response = await async_client.put(
            f"/api/v1/users/{test_user.id}",
            json=update_data
        )
        assert response.status_code in [401, 403]

    async def test_update_user_self(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: Dict[str, str]
    ):
        """Test updating own user profile - PUT /users/<id>"""
        update_data = {
            "full_name": "Updated Test User",
            "bio": "Updated bio for testing"
        }
        
        response = await async_client.put(
            f"/api/v1/users/{test_user.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["full_name"] == update_data["full_name"]
        assert data["bio"] == update_data["bio"]
        assert data["username"] == test_user.username  # Unchanged
    
    async def test_update_other_user_forbidden(
        self,
        async_client: AsyncClient,
        test_admin_user: User,
        auth_headers: Dict[str, str]
    ):
        """Test that regular users cannot update other users' profiles"""
        update_data = {"full_name": "Hacked Name"}
        
        response = await async_client.put(
            f"/api/v1/users/{test_admin_user.id}",  # Try to update admin
            json=update_data,
            headers=auth_headers  # As regular user
        )
        assert response.status_code == 403

    async def test_update_any_user_as_admin(
        self,
        async_client: AsyncClient,
        test_user: User,
        admin_auth_headers: Dict[str, str]
    ):
        """Test that admins can update any user's profile"""
        update_data = {"full_name": "Admin Updated Name"}
        
        response = await async_client.put(
            f"/api/v1/users/{test_user.id}",
            json=update_data,
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["full_name"] == update_data["full_name"]

    async def test_update_user_preferences(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: Dict[str, str]
    ):
        """Test updating user genre preferences"""
        update_data = {
            "preferred_genres": '["Science Fiction", "Fantasy", "Mystery"]'
        }
        
        response = await async_client.put(
            f"/api/v1/users/{test_user.id}",
            json=update_data,
            headers=auth_headers
        )
        assert response.status_code == 200
        
        data = response.json()
        assert "Science Fiction" in data["preferred_genres"]
    
    # =========================================================================
    # Delete User Tests (Admin only)
    # =========================================================================

    async def test_delete_user_requires_auth(self, async_client: AsyncClient, test_user: User):
        """Test that deleting a user requires authentication"""
        response = await async_client.delete(f"/api/v1/users/{test_user.id}")
        assert response.status_code in [401, 403]
    
    async def test_delete_user_requires_admin(
        self,
        async_client: AsyncClient,
        test_user: User,
        auth_headers: Dict[str, str]
    ):
        """Test that deleting a user requires admin privileges"""
        response = await async_client.delete(
            f"/api/v1/users/{test_user.id}",
            headers=auth_headers  # Regular user
        )
        assert response.status_code == 403

    async def test_delete_user_admin(
        self,
        async_client: AsyncClient,
        test_user: User,
        admin_auth_headers: Dict[str, str]
    ):
        """Test deleting a user - DELETE /users/<id> (admin only)"""
        response = await async_client.delete(
            f"/api/v1/users/{test_user.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 200
        
        # Verify user is deleted
        response = await async_client.get(
            f"/api/v1/users/{test_user.id}",
            headers=admin_auth_headers
        )
        assert response.status_code == 404
    
    async def test_delete_nonexistent_user(
        self,
        async_client: AsyncClient,
        admin_auth_headers: Dict[str, str]
    ):
        """Test deleting a user that doesn't exist"""
        response = await async_client.delete(
            "/api/v1/users/99999",
            headers=admin_auth_headers
        )
        assert response.status_code == 404
