"""
Application configuration and settings
"""
import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database configuration
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql://username:password@localhost:5432/book_management"
    )
    
    # API configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Intelligent Book Management System"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-powered book management with recommendations and summaries"
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # Llama3 Model Configuration
    LLAMA_MODEL_PATH: str = os.getenv("LLAMA_MODEL_PATH", "meta-llama/Llama-2-7b-chat-hf")
    LLAMA_MAX_LENGTH: int = 512
    LLAMA_TEMPERATURE: float = 0.7
    
    # OpenRouter API Configuration
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3-8b-instruct:free")
    
    # Recommendation settings
    RECOMMENDATION_COUNT: int = 5
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    class Config:
        env_file = ".env"


settings = Settings()
