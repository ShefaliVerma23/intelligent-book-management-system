"""
User model for the database
"""
import bcrypt
from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.orm import relationship
from .base import BaseModel


class User(BaseModel):
    """
    Users table with authentication and profile fields.
    
    Fields:
    - id: Primary key (inherited from BaseModel)
    - username: Unique username for login
    - email: Unique email address
    - hashed_password: Bcrypt-hashed password
    - full_name: Display name
    - bio: User biography
    - preferred_genres: JSON string of preferred book genres
    - reading_history: JSON string of reading patterns
    - is_active: Whether the account is active
    - is_admin: Whether the user has admin privileges
    
    Relationships:
    - reviews: One-to-many with Review (cascade delete)
    """
    __tablename__ = "users"
    
    # User credentials
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(128), nullable=False)
    
    # User profile
    full_name = Column(String(255))
    bio = Column(Text)
    
    # User preferences for recommendations
    preferred_genres = Column(Text)  # JSON string of preferred genres
    reading_history = Column(Text)   # JSON string of reading patterns
    
    # User status (indexed for filtering active/admin users)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_admin = Column(Boolean, default=False, nullable=False, index=True)
    
    # Relationships with proper configuration for async and cascade
    # - cascade="all, delete-orphan": SQLAlchemy handles cascades in session
    # - passive_deletes=True: Trust database ON DELETE CASCADE, don't load children
    # - lazy="selectin": Efficient async-compatible loading strategy
    reviews = relationship(
        "Review", 
        back_populates="user", 
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin"
    )
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}')>"
    
    def verify_password(self, password: str) -> bool:
        """Verify user password using bcrypt"""
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'), 
                self.hashed_password.encode('utf-8')
            )
        except Exception:
            return False
    
    @staticmethod
    def get_password_hash(password: str) -> str:
        """Hash a password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def set_password(self, password: str):
        """Set user password"""
        self.hashed_password = self.get_password_hash(password)
