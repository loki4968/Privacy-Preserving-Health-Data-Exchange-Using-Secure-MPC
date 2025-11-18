"""
API Security Module
Implements rate limiting, CSRF protection, and input validation
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware
import secrets
import time
from typing import Dict, Optional
from datetime import datetime, timedelta
import hashlib
import hmac


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting on API endpoints"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, list] = {}
        
    async def dispatch(self, request: Request, call_next):
        # Get client identifier
        client_id = request.client.host if request.client else "unknown"
        
        # Clean old requests
        self._cleanup_old_requests(client_id)
        
        # Check rate limit
        if self._is_rate_limited(client_id):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "detail": "Rate limit exceeded. Please try again later.",
                    "retry_after": 60
                }
            )
        
        # Record request
        self._record_request(client_id)
        
        response = await call_next(request)
        return response
    
    def _is_rate_limited(self, client_id: str) -> bool:
        """Check if client has exceeded rate limit"""
        if client_id not in self.requests:
            return False
        return len(self.requests[client_id]) >= self.requests_per_minute
    
    def _record_request(self, client_id: str):
        """Record a request from client"""
        if client_id not in self.requests:
            self.requests[client_id] = []
        self.requests[client_id].append(time.time())
    
    def _cleanup_old_requests(self, client_id: str):
        """Remove requests older than 1 minute"""
        if client_id not in self.requests:
            return
        
        cutoff = time.time() - 60
        self.requests[client_id] = [
            req_time for req_time in self.requests[client_id]
            if req_time > cutoff
        ]


class CSRFProtection:
    """CSRF token generation and validation"""
    
    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or secrets.token_hex(32)
        self.tokens: Dict[str, datetime] = {}
        self.token_lifetime = timedelta(hours=1)
    
    def generate_token(self, session_id: str) -> str:
        """Generate CSRF token for a session"""
        # Create token from session_id and timestamp
        timestamp = str(int(time.time()))
        message = f"{session_id}:{timestamp}"
        signature = hmac.new(
            self.secret_key.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        token = f"{message}:{signature}"
        
        # Store token with expiry
        self.tokens[token] = datetime.utcnow() + self.token_lifetime
        
        return token
    
    def validate_token(self, token: str, session_id: str) -> bool:
        """Validate CSRF token"""
        try:
            # Check if token exists and not expired
            if token not in self.tokens:
                return False
            
            if datetime.utcnow() > self.tokens[token]:
                del self.tokens[token]
                return False
            
            # Parse token
            parts = token.split(":")
            if len(parts) != 3:
                return False
            
            token_session_id, timestamp, signature = parts
            
            # Verify session matches
            if token_session_id != session_id:
                return False
            
            # Verify signature
            message = f"{token_session_id}:{timestamp}"
            expected_signature = hmac.new(
                self.secret_key.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception:
            return False
    
    def cleanup_expired_tokens(self):
        """Remove expired tokens"""
        now = datetime.utcnow()
        expired = [
            token for token, expiry in self.tokens.items()
            if now > expiry
        ]
        for token in expired:
            del self.tokens[token]


# Global CSRF protection instance
csrf_protection = CSRFProtection()


class InputValidator:
    """Enhanced input validation for medical data"""
    
    @staticmethod
    def validate_patient_id(patient_id: str) -> bool:
        """Validate patient ID format"""
        if not isinstance(patient_id, str):
            raise ValueError("Patient ID must be a string")
        
        if len(patient_id) < 3 or len(patient_id) > 100:
            raise ValueError("Patient ID must be between 3 and 100 characters")
        
        # Check for SQL injection patterns
        dangerous_patterns = ["'", '"', ";", "--", "/*", "*/", "xp_", "sp_"]
        if any(pattern in patient_id.lower() for pattern in dangerous_patterns):
            raise ValueError("Patient ID contains invalid characters")
        
        return True
    
    @staticmethod
    def validate_computation_type(comp_type: str) -> bool:
        """Validate computation type"""
        valid_types = [
            "average", "sum", "count", "variance", "stddev",
            "secure_average", "secure_sum", "secure_variance",
            "secure_correlation", "secure_regression", "secure_survival",
            "federated_logistic", "federated_random_forest",
            "anomaly_detection", "cohort_analysis", "drug_safety",
            "epidemiological", "secure_gwas", "pharmacogenomics"
        ]
        
        if comp_type not in valid_types:
            raise ValueError(f"Invalid computation type: {comp_type}")
        
        return True
    
    @staticmethod
    def sanitize_sql_input(input_str: str) -> str:
        """Sanitize input to prevent SQL injection"""
        if not isinstance(input_str, str):
            return str(input_str)
        
        # Remove dangerous characters
        dangerous_chars = ["'", '"', ";", "--", "/*", "*/"]
        sanitized = input_str
        for char in dangerous_chars:
            sanitized = sanitized.replace(char, "")
        
        return sanitized.strip()
    
    @staticmethod
    def validate_file_upload(filename: str, max_size_mb: int = 10) -> bool:
        """Validate file upload"""
        allowed_extensions = [".csv", ".json", ".txt"]
        
        # Check extension
        if not any(filename.lower().endswith(ext) for ext in allowed_extensions):
            raise ValueError(f"File type not allowed. Allowed: {allowed_extensions}")
        
        # Check for path traversal
        if ".." in filename or "/" in filename or "\\" in filename:
            raise ValueError("Invalid filename - path traversal detected")
        
        return True


# Rate limiting decorator
def rate_limit(calls: int = 10, period: int = 60):
    """
    Decorator for rate limiting endpoints
    
    Args:
        calls: Number of calls allowed
        period: Period in seconds
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # This is a placeholder - actual implementation would use slowapi
            return await func(*args, **kwargs)
        return wrapper
    return decorator


# CSRF protection decorator
def require_csrf_token(func):
    """Decorator to require CSRF token validation"""
    async def wrapper(request: Request, *args, **kwargs):
        # Get CSRF token from header
        csrf_token = request.headers.get("X-CSRF-Token")
        
        if not csrf_token:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="CSRF token missing"
            )
        
        # Get session ID (from JWT or session)
        session_id = request.headers.get("Authorization", "").split(" ")[-1]
        
        if not csrf_protection.validate_token(csrf_token, session_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid CSRF token"
            )
        
        return await func(request, *args, **kwargs)
    
    return wrapper


# Input validation decorator
def validate_input(func):
    """Decorator for input validation"""
    async def wrapper(*args, **kwargs):
        # Input validation logic would go here
        return await func(*args, **kwargs)
    return wrapper
