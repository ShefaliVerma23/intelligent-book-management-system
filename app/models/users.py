"""
User model for the database
"""
import bcrypt
from sqlalchemy import Column, String, Boolean, Text
from sqlalchemy.orm import relationship
from .base import BaseModel


class User(BaseModel):
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
    
    # User status
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    
    # Relationships
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    
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
