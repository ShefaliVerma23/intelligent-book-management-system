"""
Application Configuration

Reliability Features:
- All settings have sensible defaults where possible
- Clear error messages for missing required settings
- Validation runs at startup to catch issues early
- Settings are immutable after loading

Required Environment Variables:
- DATABASE_URL: PostgreSQL connection string
- SECRET_KEY: JWT signing key (min 32 chars)

Recommended Environment Variables:
- OPENROUTER_API_KEY: For AI features (without this, AI uses fallback mode)
- REDIS_URL: For caching (without this, caching is disabled)
"""
import sys
import warnings
from typing import List, Optional
from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator


class Settings(BaseSettings):
    """
    Application settings with validation.
    
    Uses environment variables with optional .env file support.
    """
    
    # =========================================================================
    # REQUIRED SETTINGS (no defaults - must be provided)
    # =========================================================================
    
    DATABASE_URL: str
    SECRET_KEY: str
    
    # =========================================================================
    # API SETTINGS
    # =========================================================================
    
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Intelligent Book Management System"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "AI-powered book management with recommendations"
    
    # =========================================================================
    # SECURITY
    # =========================================================================
    
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # =========================================================================
    # CORS
    # =========================================================================
    
    ALLOWED_HOSTS: str = "*"
    
    # =========================================================================
    # AI / LLM SETTINGS (OpenRouter recommended)
    # =========================================================================
    
    # OpenRouter API (recommended for production)
    OPENROUTER_API_KEY: str = ""  # Empty = fallback mode
    OPENROUTER_API_URL: str = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_MODEL: str = "meta-llama/llama-3-8b-instruct:free"
    
    # LLM Generation Parameters
    LLM_TEMPERATURE: float = 0.7
    LLM_TOP_P: float = 0.9
    LLM_REQUEST_TIMEOUT: int = 30  # seconds
    LLM_RETRY_ATTEMPTS: int = 2
    
    # Token Limits
    LLM_MAX_TOKENS_SUMMARY: int = 150
    LLM_MAX_TOKENS_RECOMMENDATION: int = 200
    LLM_MAX_INPUT_CHARS: int = 4000
    
    # Local model settings (only if not using OpenRouter)
    LLAMA_MODEL_PATH: str = "microsoft/DialoGPT-medium"
    LLAMA_MAX_LENGTH: int = 512
    
    # Legacy settings (kept for backwards compatibility)
    LLM_FREQUENCY_PENALTY: float = 0.0
    LLM_PRESENCE_PENALTY: float = 0.0
    LLM_MAX_TOKENS_DEFAULT: int = 256
    
    # =========================================================================
    # CACHING (Redis)
    # =========================================================================
    
    REDIS_URL: Optional[str] = None  # None = caching disabled
    CACHE_ENABLED: bool = True  # Only effective if REDIS_URL is set
    
    # =========================================================================
    # RECOMMENDATIONS
    # =========================================================================
    
    RECOMMENDATION_COUNT: int = 5
    
    # =========================================================================
    # LOGGING
    # =========================================================================
    
    LOG_LEVEL: str = "INFO"
    
    # =========================================================================
    # PYDANTIC CONFIG
    # =========================================================================
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # Ignore extra env vars
    
    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @field_validator('DATABASE_URL')
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        """Validate DATABASE_URL is set and looks valid"""
        if not v:
            raise ValueError(
                "DATABASE_URL is required. "
                "Example: postgresql://user:password@localhost:5432/dbname"
            )
        
        v = v.strip()
        
        # Check for placeholder values
        if v.startswith("your_") or "your_" in v:
            raise ValueError(
                "DATABASE_URL contains placeholder values. "
                "Please set a real database connection string."
            )
        
        # Basic format validation
        if not (v.startswith("postgresql://") or 
                v.startswith("postgresql+asyncpg://") or
                v.startswith("sqlite")):
            raise ValueError(
                "DATABASE_URL must start with postgresql:// or sqlite://. "
                f"Got: {v[:50]}..."
            )
        
        return v
    
    @field_validator('SECRET_KEY')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate SECRET_KEY is secure"""
        if not v:
            raise ValueError(
                "SECRET_KEY is required. Generate one with: "
                "python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        
        v = v.strip()
        
        # Check for placeholder values
        if "your_" in v.lower() or v == "changeme" or v == "secret":
            raise ValueError(
                "SECRET_KEY contains a placeholder value. "
                "Please generate a secure random key."
            )
        
        # Minimum length for security
        if len(v) < 32:
            raise ValueError(
                f"SECRET_KEY must be at least 32 characters (got {len(v)}). "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        
        return v
    
    @field_validator('LOG_LEVEL')
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        v = v.upper().strip()
        if v not in valid_levels:
            raise ValueError(f"LOG_LEVEL must be one of: {', '.join(valid_levels)}")
        return v
    
    @field_validator('LLM_TEMPERATURE')
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        """Validate temperature is in valid range"""
        if not 0.0 <= v <= 2.0:
            raise ValueError("LLM_TEMPERATURE must be between 0.0 and 2.0")
        return v
    
    @field_validator('LLM_REQUEST_TIMEOUT')
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Ensure timeout is reasonable"""
        if v < 5:
            warnings.warn("LLM_REQUEST_TIMEOUT < 5s may cause frequent timeouts")
        if v > 120:
            warnings.warn("LLM_REQUEST_TIMEOUT > 120s may cause request hangs")
            v = 120  # Cap at 2 minutes
        return v
    
    @model_validator(mode='after')
    def validate_config(self) -> 'Settings':
        """Cross-field validation"""
        
        # Warn if no AI API key
        if not self.OPENROUTER_API_KEY:
            warnings.warn(
                "OPENROUTER_API_KEY not set - AI features will use fallback mode. "
                "Get an API key from https://openrouter.ai/ for full AI functionality.",
                UserWarning
            )
        
        # Warn if cache enabled but no Redis URL
        if self.CACHE_ENABLED and not self.REDIS_URL:
            warnings.warn(
                "CACHE_ENABLED=True but REDIS_URL not set - caching will be disabled. "
                "Set REDIS_URL or CACHE_ENABLED=False to suppress this warning.",
                UserWarning
            )
        
        return self
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def get_allowed_hosts_list(self) -> List[str]:
        """Convert ALLOWED_HOSTS string to list"""
        if self.ALLOWED_HOSTS == "*":
            return ["*"]
        return [h.strip() for h in self.ALLOWED_HOSTS.split(",") if h.strip()]
    
    def is_cache_available(self) -> bool:
        """Check if caching is actually available"""
        return self.CACHE_ENABLED and bool(self.REDIS_URL)
    
    def is_ai_available(self) -> bool:
        """Check if AI features are available (not fallback mode)"""
        return bool(self.OPENROUTER_API_KEY)


# =============================================================================
# LOAD SETTINGS WITH ERROR HANDLING
# =============================================================================

def load_settings() -> Settings:
    """
    Load and validate settings.
    
    Provides clear error messages if configuration is invalid.
    """
    try:
        return Settings()
    except Exception as e:
        error_msg = str(e)
        
        print("\n" + "=" * 60, file=sys.stderr)
        print("CONFIGURATION ERROR", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        print(f"\n{error_msg}\n", file=sys.stderr)
        print("Please check your environment variables or .env file.", file=sys.stderr)
        print("See sample.env for required configuration.", file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)
        
        raise SystemExit(1)


# Global settings instance
settings = load_settings()
