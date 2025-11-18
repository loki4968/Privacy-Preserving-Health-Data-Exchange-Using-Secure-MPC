# Interview Guide Part 2: File Handling & Request Processing

## 6. FILE HANDLING DEEP DIVE

### 6.1 File Upload Architecture

**Upload Flow:**
```
User selects CSV → Frontend validates → Sends to backend → 
Backend validates → Encrypts data → Stores in database → Returns success
```

### 6.2 Frontend File Upload

```javascript
// File: app/components/SecureComputationWizard.jsx
const handleFileUpload = async (file, columns) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('columns', columns);
    
    const response = await fetch(
        `/api/secure-computations/computations/${computationId}/submit-data`,
        {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`
                // Note: NO Content-Type header for FormData
            },
            body: formData
        }
    );
};
```

**Why FormData?**
- Handles multipart/form-data encoding automatically
- Supports file uploads with metadata
- Browser sets correct Content-Type with boundary

### 6.3 Backend File Handling

```python
# File: backend/routers/secure_computations.py
@router.post("/computations/{computation_id}/submit-data")
async def submit_computation_data(
    computation_id: str,
    file: UploadFile = File(...),  # File upload
    columns: Optional[str] = Form(None),  # Form field
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Validate file type
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "Only CSV files allowed")
    
    # 2. Read file content
    content = await file.read()
    
    # 3. Parse CSV
    csv_data = io.StringIO(content.decode('utf-8'))
    reader = csv.DictReader(csv_data)
    
    # 4. Extract numeric columns
    if columns:
        column_list = [c.strip() for c in columns.split(',')]
    else:
        column_list = None  # Use all numeric columns
    
    # 5. Process and encrypt data
    service = SecureComputationService(db)
    result = service.submit_data(
        computation_id=computation_id,
        org_id=current_user["id"],
        csv_reader=reader,
        columns=column_list
    )
    
    return result
```

### 6.4 CSV Processing

```python
# File: backend/secure_computation.py
def submit_data(self, computation_id, org_id, csv_reader, columns):
    # 1. Extract numeric values
    numeric_values = []
    for row in csv_reader:
        if columns:
            # Use specified columns
            for col in columns:
                try:
                    value = float(row[col])
                    numeric_values.append(value)
                except (ValueError, KeyError):
                    continue
        else:
            # Auto-detect numeric columns
            for value in row.values():
                try:
                    numeric_values.append(float(value))
                except ValueError:
                    continue
    
    # 2. Validate minimum data
    if len(numeric_values) < 1:
        raise ValueError("No valid numeric data found")
    
    # 3. Encrypt data based on computation type
    computation = self.db.query(SecureComputation).get(computation_id)
    
    if computation.type in ["secure_correlation", "secure_sum", ...]:
        # Use hybrid encryption (HE + SMPC)
        encrypted_data = self._encrypt_hybrid(numeric_values)
    else:
        # Use homomorphic encryption only
        encrypted_data = self._encrypt_homomorphic(numeric_values)
    
    # 4. Store in database
    result = ComputationResult(
        computation_id=computation_id,
        org_id=org_id,
        data_points=encrypted_data,
        data_points_count=len(numeric_values)
    )
    self.db.add(result)
    self.db.commit()
    
    return {"success": True, "data_points_count": len(numeric_values)}
```

### 6.5 File Validation

```python
# File: backend/utils.py
def allowed_file_extension(filename: str) -> bool:
    """Check if file extension is allowed"""
    ALLOWED_EXTENSIONS = {'.csv', '.pdf', '.jpg', '.png'}
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS

def validate_file_size(file_size: int, max_size_mb: int = 10) -> bool:
    """Validate file size"""
    max_bytes = max_size_mb * 1024 * 1024
    return file_size <= max_bytes

# Usage in route
if not allowed_file_extension(file.filename):
    raise HTTPException(400, "File type not allowed")

if not validate_file_size(len(content)):
    raise HTTPException(400, "File too large (max 10MB)")
```

### 6.6 File Storage Strategy

**For CSV uploads (computation data):**
- ✅ Store encrypted data in database (JSON column)
- ✅ No file system storage needed
- ✅ Easier to query and aggregate

**For document uploads (reports, images):**
```python
# File: backend/main.py
UPLOAD_DIR = "uploads/"

@app.post("/upload-document")
async def upload_document(file: UploadFile, current_user: dict):
    # Create organization-specific directory
    org_dir = os.path.join(UPLOAD_DIR, str(current_user["id"]))
    os.makedirs(org_dir, exist_ok=True)
    
    # Generate unique filename
    filename = f"{uuid.uuid4()}_{file.filename}"
    filepath = os.path.join(org_dir, filename)
    
    # Save file
    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Store metadata in database
    upload = Upload(
        filename=filename,
        original_filename=file.filename,
        org_id=current_user["id"],
        file_size=len(content),
        mime_type=file.content_type
    )
    db.add(upload)
    db.commit()
```

---

## 7. REQUEST/RESPONSE LIFECYCLE

### 7.1 Complete Request Flow

```
┌─────────────────────────────────────────────────────────┐
│ 1. USER ACTION (Frontend)                              │
│    - Click "Submit Data" button                        │
│    - Trigger handleSubmit() function                   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 2. FRONTEND VALIDATION                                  │
│    - Check file type (.csv)                            │
│    - Check file size (< 10MB)                          │
│    - Validate required fields                          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 3. HTTP REQUEST                                         │
│    POST /api/secure-computations/computations/{id}/... │
│    Headers:                                             │
│      - Authorization: Bearer <JWT>                      │
│      - Content-Type: multipart/form-data               │
│    Body: FormData with file + columns                  │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 4. MIDDLEWARE PROCESSING                                │
│    a) CORS Middleware - Check origin                   │
│    b) Rate Limit - Check request count                 │
│    c) Request Logging - Log request details            │
│    d) Security Headers - Add security headers          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 5. AUTHENTICATION                                       │
│    a) Extract JWT from Authorization header            │
│    b) Verify JWT signature                             │
│    c) Decode payload (user_id, role, exp)              │
│    d) Check token expiration                           │
│    e) Query database for user                          │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 6. AUTHORIZATION                                        │
│    a) Check user role (HOSPITAL, CLINIC, etc.)         │
│    b) Verify permissions for this action               │
│    c) Check if user is participant in computation      │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 7. INPUT VALIDATION (Pydantic)                         │
│    a) Validate file parameter                          │
│    b) Validate columns parameter                       │
│    c) Check computation_id format (UUID)               │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 8. BUSINESS LOGIC                                       │
│    a) Read file content                                │
│    b) Parse CSV data                                   │
│    c) Extract numeric values                           │
│    d) Encrypt data (HE + SMPC)                         │
│    e) Store in database                                │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 9. DATABASE TRANSACTION                                 │
│    BEGIN TRANSACTION                                    │
│      INSERT INTO computation_results (...)             │
│      UPDATE secure_computations SET status=...         │
│    COMMIT                                               │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 10. WEBSOCKET NOTIFICATION                              │
│     Notify all participants:                           │
│     "Organization X submitted data"                    │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 11. HTTP RESPONSE                                       │
│     Status: 200 OK                                      │
│     Body: {                                             │
│       "success": true,                                  │
│       "data_points_count": 80,                         │
│       "encryption_type": "hybrid"                      │
│     }                                                   │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│ 12. FRONTEND UPDATE                                     │
│     - Update UI state                                   │
│     - Show success notification                        │
│     - Refresh computation status                       │
└─────────────────────────────────────────────────────────┘
```

### 7.2 Error Handling at Each Layer

```python
# File: backend/error_handlers.py
from fastapi import Request, status
from fastapi.responses import JSONResponse

def setup_error_handlers(app):
    
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "path": request.url.path
            }
        )
    
    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=400,
            content={
                "error": str(exc),
                "error_type": "validation_error"
            }
        )
    
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "error_type": "server_error"
            }
        )
```

### 7.3 Middleware Implementation

```python
# File: backend/middleware.py

class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, requests_per_minute=60, requests_per_hour=1000):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.request_counts = {}  # {ip: [(timestamp, count), ...]}
    
    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host
        now = datetime.utcnow()
        
        # Check rate limits
        if self._is_rate_limited(client_ip, now):
            return JSONResponse(
                status_code=429,
                content={"error": "Too many requests"}
            )
        
        # Record request
        self._record_request(client_ip, now)
        
        response = await call_next(request)
        return response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
        
        return response

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"{request.method} {request.url.path}")
        
        response = await call_next(request)
        
        # Log response time
        duration = time.time() - start_time
        logger.info(f"Completed in {duration:.2f}s - Status: {response.status_code}")
        
        return response
```

---

## 8. AUTHENTICATION & AUTHORIZATION

### 8.1 JWT Token System

**Token Structure:**
```json
{
  "header": {
    "alg": "HS256",
    "typ": "JWT"
  },
  "payload": {
    "user_id": 1,
    "email": "hospital@example.com",
    "role": "HOSPITAL_ADMIN",
    "exp": 1698765432,
    "iat": 1698761832
  },
  "signature": "..."
}
```

**Token Generation:**
```python
# File: backend/auth_utils.py
import jwt
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")
```

### 8.2 Login Flow

```python
# File: backend/routers/auth.py
@router.post("/login")
def login(
    credentials: LoginRequest,
    db: Session = Depends(get_db)
):
    # 1. Find user
    user = db.query(Organization).filter_by(email=credentials.email).first()
    if not user:
        raise HTTPException(401, "Invalid credentials")
    
    # 2. Check account status
    if user.account_locked_until and user.account_locked_until > datetime.utcnow():
        raise HTTPException(403, "Account locked")
    
    # 3. Verify password
    if not verify_password(credentials.password, user.password_hash):
        # Increment failed attempts
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.account_locked_until = datetime.utcnow() + timedelta(hours=1)
        db.commit()
        raise HTTPException(401, "Invalid credentials")
    
    # 4. Reset failed attempts
    user.failed_login_attempts = 0
    user.last_login = datetime.utcnow()
    db.commit()
    
    # 5. Generate tokens
    access_token = create_access_token({
        "user_id": user.id,
        "email": user.email,
        "role": user.role.value
    })
    refresh_token = create_refresh_token({"user_id": user.id})
    
    # 6. Store refresh token
    if not user.session_tokens:
        user.session_tokens = []
    user.session_tokens.append(refresh_token)
    db.commit()
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role.value
        }
    }
```

### 8.3 Permission System

```python
# File: backend/auth_utils.py
class Permission(str, Enum):
    CREATE_COMPUTATION = "create_computation"
    VIEW_COMPUTATION = "view_computation"
    SUBMIT_DATA = "submit_data"
    VIEW_RESULTS = "view_results"
    DELETE_COMPUTATION = "delete_computation"
    MANAGE_USERS = "manage_users"
    VIEW_AUDIT_LOGS = "view_audit_logs"

ROLE_PERMISSIONS = {
    UserRole.ADMIN: [
        Permission.CREATE_COMPUTATION,
        Permission.VIEW_COMPUTATION,
        Permission.SUBMIT_DATA,
        Permission.VIEW_RESULTS,
        Permission.DELETE_COMPUTATION,
        Permission.MANAGE_USERS,
        Permission.VIEW_AUDIT_LOGS
    ],
    UserRole.HOSPITAL_ADMIN: [
        Permission.CREATE_COMPUTATION,
        Permission.VIEW_COMPUTATION,
        Permission.SUBMIT_DATA,
        Permission.VIEW_RESULTS,
        Permission.DELETE_COMPUTATION
    ],
    UserRole.RESEARCHER: [
        Permission.VIEW_COMPUTATION,
        Permission.VIEW_RESULTS
    ],
    UserRole.PATIENT: [
        Permission.VIEW_COMPUTATION
    ]
}

def get_user_permissions(role: UserRole) -> List[Permission]:
    return ROLE_PERMISSIONS.get(role, [])

def has_permission(user_role: UserRole, required_permission: Permission) -> bool:
    user_permissions = get_user_permissions(user_role)
    return required_permission in user_permissions
```

**Usage in Routes:**
```python
# File: backend/dependencies.py
def require_permissions(*required_permissions: Permission):
    def permission_checker(current_user: dict = Depends(get_current_user)):
        user_role = UserRole(current_user["role"])
        user_permissions = get_user_permissions(user_role)
        
        for perm in required_permissions:
            if perm not in user_permissions:
                raise HTTPException(403, f"Missing permission: {perm}")
        
        return current_user
    
    return permission_checker

# Usage
@router.delete("/computations/{id}")
def delete_computation(
    id: str,
    current_user: dict = Depends(require_permissions(Permission.DELETE_COMPUTATION))
):
    # Only users with DELETE_COMPUTATION permission can access
    pass
```

---

Continue to INTERVIEW_PART3 for Cryptography, WebSocket, and Advanced Topics.
