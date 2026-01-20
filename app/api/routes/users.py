"""
User-related API endpoints

Note: User self-registration is handled at /auth/register (public endpoint).
The /users/ POST endpoint here is for admin-only user creation.

Security:
- GET /users/ (list all) - Admin only
- GET /users/{id} - User can view themselves, admin can view all
- PUT /users/{id} - User can update themselves, admin can update all
- DELETE /users/{id} - Admin only
- POST /users/ - Admin only (create user with specific roles)
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import get_db
from app.api.schemas import AdminUserCreate, UserUpdate, UserResponse
from app.services.user_service import UserService
from app.services.auth_service import AuthService, security

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/", response_model=UserResponse)
async def create_user(
    user: AdminUserCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user (Admin only).
    
    Admins can create users with specific is_active and is_admin settings.
    For self-registration, use POST /auth/register instead.
    """
    # Require admin privileges
    auth_service = AuthService(db)
    await auth_service.require_admin(credentials)
    
    user_service = UserService(db)
    existing_user = await user_service.get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    existing_username = await user_service.get_user_by_username(user.username)
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken")
    
    return await user_service.create_user(user, is_admin_creation=True)


@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get users with pagination (Admin only).
    
    Lists all users in the system. Requires admin privileges.
    """
    auth_service = AuthService(db)
    await auth_service.require_admin(credentials)
    
    user_service = UserService(db)
    return await user_service.get_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific user by ID.
    
    Users can view their own profile. Admins can view any user.
    """
    auth_service = AuthService(db)
    current_user = await auth_service.get_current_active_user(credentials)
    
    # Users can only view themselves unless they're admin
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own profile"
        )
    
    user_service = UserService(db)
    user = await user_service.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdate,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Update a specific user.
    
    Users can update their own profile (full_name, bio, preferred_genres).
    Admins can update any user.
    """
    auth_service = AuthService(db)
    current_user = await auth_service.get_current_active_user(credentials)
    
    # Users can only update themselves unless they're admin
    if user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile"
        )
    
    user_service = UserService(db)
    user = await user_service.update_user(user_id, user_update)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def delete_user(
    user_id: int,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
):
    """Delete a specific user (Admin only).
    
    Only admins can delete user accounts.
    """
    auth_service = AuthService(db)
    await auth_service.require_admin(credentials)
    
    user_service = UserService(db)
    success = await user_service.delete_user(user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"message": "User deleted successfully"}
