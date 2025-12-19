"""
Application configuration and settings
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database configuration
    DATABASE_URL: str = "postgresql://username:password@localhost:5432/book_management"
    
    # API configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Intelligent Book Management System"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-powered book management with recommendations and summaries"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS - using string to avoid JSON parsing issues in .env
    ALLOWED_HOSTS: str = "*"
    
    # Llama3 Model Configuration
    LLAMA_MODEL_PATH: str = "meta-llama/Llama-2-7b-chat-hf"
    LLAMA_MAX_LENGTH: int = 512
    LLAMA_TEMPERATURE: float = 0.7
    
    # OpenRouter API Configuration
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "meta-llama/llama-3-8b-instruct:free"
    
    # Recommendation settings
    RECOMMENDATION_COUNT: int = 5
    
    # Redis Cache Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_ENABLED: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
    
    def get_allowed_hosts_list(self) -> List[str]:
        """Convert ALLOWED_HOSTS string to list"""
        if self.ALLOWED_HOSTS == "*":
            return ["*"]
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",")]


settings = Settings()
