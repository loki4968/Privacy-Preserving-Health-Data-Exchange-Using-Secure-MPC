import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import validator
import secrets

class Settings(BaseSettings):
    """Application settings"""
    
    # Pydantic v2 settings configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",  # ignore extra env vars not declared as fields
    )

    # Application
    APP_NAME: str = "Health Data Exchange API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Security
    # Use a stable default in dev to avoid invalidating tokens on reloads
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Database
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./health_data.db")
    DATABASE_CONNECT_ARGS: dict = {"check_same_thread": False, "timeout": 30}
    
    # Environment
    ENVIRONMENT: str = os.environ.get("ENVIRONMENT", "development")  # development, production
    
    @validator("DATABASE_CONNECT_ARGS", pre=True, always=True)
    def set_database_args(cls, v, values):
        """Set appropriate database connection arguments based on database type"""
        database_url = values.get("DATABASE_URL", "sqlite:///./health_data.db")
        
        if database_url.startswith("postgresql"):
            # PostgreSQL connection args
            return {
                "pool_size": 20,
                "max_overflow": 0,
                "pool_pre_ping": True,
                "pool_recycle": 300
            }
        else:
            # SQLite connection args (default)
            return {"check_same_thread": False, "timeout": 30}
    
    @validator("DEBUG", pre=True, always=True)
    def set_debug_mode(cls, v, values):
        """Set debug mode based on environment"""
        environment = values.get("ENVIRONMENT", "development")
        if environment == "production":
            return False
        return os.environ.get("DEBUG", "True").lower() in ("true", "1", "yes")
    
    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS: str = ".csv,.xlsx,.json"
    VALID_CATEGORIES: str = "vital_signs,lab_results,medications,allergies,procedures,diagnoses"
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_HOUR: int = 1000
    
    # Email (for OTP)
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "app.log"
    
    # Security Headers
    SECURITY_HEADERS: dict = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    }
    
    # MPC Settings
    MPC_THRESHOLD: int = 2
    MPC_KEY_SIZE: int = 32
    
    # Audit
    AUDIT_LOG_ENABLED: bool = True
    AUDIT_LOG_RETENTION_DAYS: int = 90

    # LLM / Prompt Interpretation (optional)
    # Options: "groq", "openai", "huggingface", "ollama", "heuristic"
    # "groq" is FREE (14,400 requests/day) and recommended as default
    # "heuristic" is FREE and requires no API keys (fallback)
    LLM_PROVIDER: Optional[str] = os.environ.get("LLM_PROVIDER", "groq")
    OPENAI_API_KEY: Optional[str] = os.environ.get("OPENAI_API_KEY")
    OPENAI_MODEL: str = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    
    # Groq (FREE tier: 14,400 requests/day)
    GROQ_API_KEY: Optional[str] = os.environ.get("GROQ_API_KEY")
    GROQ_MODEL: str = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
    
    # Hugging Face (FREE tier: 1,000 requests/month)
    HUGGINGFACE_API_KEY: Optional[str] = os.environ.get("HUGGINGFACE_API_KEY")
    HF_MODEL: str = os.environ.get("HF_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
    
    # Ollama (FREE, local, no API key needed)
    OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "llama3.2")
    
    @validator("SECRET_KEY", pre=True, always=True)
    def generate_secret_key(cls, v):
        # If explicitly unset or placeholder, generate; otherwise keep stable
        if not v or v == "your-secret-key-here":
            return secrets.token_urlsafe(32)
        return v
    
    @validator("UPLOAD_DIR", pre=True, always=True)
    def create_upload_dir(cls, v):
        os.makedirs(v, exist_ok=True)
        return v
    
    # Note: Pydantic v2 uses model_config; legacy inner Config removed

# Create settings instance
settings = Settings()

# Database configuration
DATABASE_URL = settings.DATABASE_URL
DATABASE_CONNECT_ARGS = settings.DATABASE_CONNECT_ARGS

# Upload directory
UPLOAD_DIR = settings.UPLOAD_DIR

# Security settings
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = settings.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = settings.REFRESH_TOKEN_EXPIRE_DAYS

# File upload settings
MAX_FILE_SIZE = settings.MAX_FILE_SIZE
ALLOWED_EXTENSIONS = settings.ALLOWED_EXTENSIONS.split(",")
VALID_CATEGORIES = settings.VALID_CATEGORIES.split(",")

# CORS settings
ALLOWED_ORIGINS = settings.ALLOWED_ORIGINS.split(",")

# Rate limiting settings
RATE_LIMIT_PER_MINUTE = settings.RATE_LIMIT_PER_MINUTE
RATE_LIMIT_PER_HOUR = settings.RATE_LIMIT_PER_HOUR

# Email settings
SMTP_SERVER = settings.SMTP_SERVER
SMTP_PORT = settings.SMTP_PORT
SMTP_USERNAME = settings.SMTP_USERNAME
SMTP_PASSWORD = settings.SMTP_PASSWORD

# Logging settings
LOG_LEVEL = settings.LOG_LEVEL
LOG_FILE = settings.LOG_FILE

# Security headers
SECURITY_HEADERS = settings.SECURITY_HEADERS

# MPC settings
MPC_THRESHOLD = settings.MPC_THRESHOLD
MPC_KEY_SIZE = settings.MPC_KEY_SIZE

# Audit settings
AUDIT_LOG_ENABLED = settings.AUDIT_LOG_ENABLED
AUDIT_LOG_RETENTION_DAYS = settings.AUDIT_LOG_RETENTION_DAYS
