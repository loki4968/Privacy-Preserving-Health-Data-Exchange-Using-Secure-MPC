# Privacy-Preserving Health Data Exchange - Interview Preparation Guide (Part 1)

## 📋 Table of Contents
1. [Project Overview](#project-overview)
2. [Technology Stack Deep Dive](#technology-stack-deep-dive)
3. [Architecture & Design Patterns](#architecture--design-patterns)
4. [API Routes & Endpoints](#api-routes--endpoints)
5. [Database Design](#database-design)

---

## 1. PROJECT OVERVIEW

### What is this project?
A **Privacy-Preserving Health Data Exchange Platform** that enables multiple healthcare organizations (hospitals, clinics, labs) to collaborate on data analysis **without sharing raw patient data**. Uses advanced cryptographic techniques like **Secure Multi-Party Computation (SMPC)** and **Homomorphic Encryption**.

### Core Problem Solved
- Healthcare organizations need to collaborate on research and analytics
- Privacy regulations (HIPAA, GDPR) prevent sharing raw patient data
- Traditional approaches require data centralization (security risk)
- **Solution**: Compute on encrypted data without decryption

### Key Features
1. **18 Advanced Computation Types**: Correlation, regression, federated learning, GWAS, drug safety
2. **3 Security Methods**: Standard encryption, Homomorphic Encryption (HE), Hybrid (HE + SMPC)
3. **Real-time Collaboration**: WebSocket-based live updates
4. **Role-Based Access Control**: 6 user roles with granular permissions
5. **Complete Audit Trail**: Every action logged for compliance

---

## 2. TECHNOLOGY STACK DEEP DIVE

### 2.1 Backend: FastAPI (Python)

#### Why FastAPI?
```
✅ Automatic API documentation (Swagger/OpenAPI)
✅ Built-in data validation with Pydantic
✅ Async/await support for high performance
✅ Type hints for better code quality
✅ WebSocket support for real-time features
✅ Dependency injection system
```

#### FastAPI Core Concepts Used

**1. Dependency Injection**
```python
# File: backend/dependencies.py
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Extracts and validates user from JWT token"""
    payload = decode_access_token(token)
    user = db.query(Organization).filter_by(id=payload["user_id"]).first()
    return user

# Usage in routes
@router.post("/computations")
def create_computation(
    current_user: dict = Depends(get_current_user),  # Auto-injected
    db: Session = Depends(get_db)                    # Auto-injected
):
    pass
```

**2. Pydantic Models for Validation**
```python
# File: backend/routers/secure_computations.py
class ComputationCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    type: str = Field(..., pattern="^(secure_correlation|secure_sum|...)$")
    description: Optional[str] = Field(None, max_length=1000)
    invited_org_ids: List[int] = Field(..., min_items=1)
    security_method: str = Field(default="hybrid")
```

**3. APIRouter for Modular Routes**
```python
# File: backend/routers/secure_computations.py
router = APIRouter(prefix="/api/secure-computations", tags=["Secure Computations"])

# File: backend/main.py
app.include_router(auth.router)
app.include_router(secure_computations.router)
app.include_router(analytics.router)
app.include_router(machine_learning.router)
```

### 2.2 Database: SQLite (Dev) / PostgreSQL (Prod)

#### Why SQLite for Development?
```
✅ Zero configuration - file-based database
✅ Perfect for development and testing
✅ Easy to reset and backup
✅ No separate server process needed
```

#### Why PostgreSQL for Production?
```
✅ ACID compliance for data integrity
✅ Better concurrency handling
✅ Advanced indexing and query optimization
✅ JSON/JSONB support for flexible schemas
✅ Proven scalability for healthcare data
```

#### Database Configuration
```python
# File: backend/config.py
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./health_data.db")

# File: backend/models.py
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        pool_pre_ping=True
    )
else:
    # PostgreSQL configuration
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
```

#### SQLite Optimizations Applied
```python
# File: backend/models.py
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL;")      # Write-Ahead Logging
    cursor.execute("PRAGMA synchronous=NORMAL;")    # Faster writes
    cursor.execute("PRAGMA foreign_keys=ON;")       # Referential integrity
    cursor.execute("PRAGMA busy_timeout=5000;")     # Wait 5s on locks
```

### 2.3 ORM: SQLAlchemy

#### Why SQLAlchemy?
```
✅ Database-agnostic (works with SQLite, PostgreSQL, MySQL)
✅ Powerful query builder
✅ Relationship management
✅ Migration support
✅ Connection pooling
```

#### Key SQLAlchemy Patterns Used

**1. Declarative Models**
```python
# File: backend/models.py
class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True)
    
    # Relationships
    uploads = relationship("Upload", back_populates="organization", cascade="all, delete-orphan")
```

**2. Session Management**
```python
# File: backend/models.py
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**3. Query Patterns**
```python
# Simple query
org = db.query(Organization).filter_by(email=email).first()

# Join query
results = db.query(ComputationResult).join(
    SecureComputation
).filter(
    SecureComputation.id == computation_id
).all()

# Aggregate query
count = db.query(func.count(Upload.id)).filter_by(org_id=org_id).scalar()
```

### 2.4 Frontend: Next.js 14 + React

#### Why Next.js?
```
✅ Server-Side Rendering (SSR) for better SEO
✅ File-based routing
✅ API routes (backend-for-frontend pattern)
✅ Image optimization
✅ Built-in TypeScript support
✅ App Router for modern React patterns
```

#### Frontend Architecture
```
app/
├── (auth)/              # Authentication pages (login, register)
├── dashboard/           # Main dashboard
├── secure-computations/ # Computation management
│   ├── [id]/           # Dynamic routes for specific computation
│   │   └── results/    # Results visualization
├── components/          # Reusable React components
└── config/             # API configuration
```

---

## 3. ARCHITECTURE & DESIGN PATTERNS

### 3.1 Layered Architecture

```
┌─────────────────────────────────────────┐
│         Frontend (Next.js)              │
│  - React Components                     │
│  - State Management                     │
│  - WebSocket Clients                    │
└──────────────┬──────────────────────────┘
               │ HTTP/WebSocket
┌──────────────▼──────────────────────────┐
│         API Layer (FastAPI)             │
│  - Route Handlers                       │
│  - Request Validation                   │
│  - Authentication/Authorization         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       Service Layer                     │
│  - SecureComputationService             │
│  - AdvancedSMPCComputations             │
│  - HomomorphicEncryption                │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       Data Access Layer (ORM)           │
│  - SQLAlchemy Models                    │
│  - Database Sessions                    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│       Database (SQLite/PostgreSQL)      │
└─────────────────────────────────────────┘
```

### 3.2 Design Patterns Implemented

#### 1. Repository Pattern
```python
# File: backend/secure_computation.py
class SecureComputationService:
    def __init__(self, db: Session):
        self.db = db
        
    def create_computation(self, data: dict) -> SecureComputation:
        """Encapsulates database operations"""
        computation = SecureComputation(**data)
        self.db.add(computation)
        self.db.commit()
        return computation
```

#### 2. Factory Pattern
```python
# File: backend/secure_computation.py
def _determine_security_method(self, computation_type: str) -> str:
    """Factory method for security method selection"""
    advanced_smpc_types = [
        "secure_correlation", "secure_regression", ...
    ]
    
    if computation_type in advanced_smpc_types:
        return "hybrid (homomorphic encryption + SMPC)"
    elif computation_type in ["sum", "average"]:
        return "homomorphic encryption"
    else:
        return "standard encryption"
```

#### 3. Strategy Pattern
```python
# File: backend/secure_computation.py
def _perform_computation(self, computation_type: str, results: List):
    """Different strategies for different computation types"""
    if computation_type in advanced_smpc_types:
        return self._perform_secure_computation_hybrid(computation_type, results)
    else:
        return self._perform_secure_computation_homomorphic(computation_type, results)
```

#### 4. Observer Pattern (WebSocket)
```python
# File: backend/websocket.py
class SMPCWebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def notify_computation_status(self, computation_id: str, status: str):
        """Notify all observers (connected clients) of status change"""
        connections = self.active_connections.get(computation_id, [])
        for connection in connections:
            await connection.send_json({"type": "status_update", "status": status})
```

### 3.3 Security Architecture

```
┌─────────────────────────────────────────┐
│      User Request (Frontend)            │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Middleware Layer                   │
│  1. CORS Validation                     │
│  2. Rate Limiting                       │
│  3. Request Logging                     │
│  4. Security Headers                    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Authentication Layer               │
│  1. JWT Token Validation                │
│  2. User Extraction                     │
│  3. Permission Checking                 │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Business Logic Layer               │
│  1. Input Validation (Pydantic)         │
│  2. Data Processing                     │
│  3. Encryption/Decryption               │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│      Audit Layer                        │
│  1. Action Logging                      │
│  2. Error Tracking                      │
│  3. Compliance Recording                │
└─────────────────────────────────────────┘
```

---

## 4. API ROUTES & ENDPOINTS

### 4.1 Route Organization

```
backend/
├── main.py                    # Main FastAPI app + legacy routes
└── routers/
    ├── auth.py               # Authentication endpoints
    ├── secure_computations.py # Computation management
    ├── analytics.py          # Analytics endpoints
    ├── machine_learning.py   # ML endpoints
    └── report_requests.py    # Report generation
```

### 4.2 Complete API Endpoint List

#### Authentication Routes (`/api/auth`)
```python
# File: backend/routers/auth.py

POST   /api/auth/register          # Register new organization
POST   /api/auth/login             # Login with credentials
POST   /api/auth/refresh           # Refresh access token
POST   /api/auth/logout            # Logout user
POST   /api/auth/verify-email      # Verify email with OTP
POST   /api/auth/resend-otp        # Resend OTP
POST   /api/auth/forgot-password   # Request password reset
POST   /api/auth/reset-password    # Reset password with token
GET    /api/auth/me                # Get current user info
```

#### Secure Computation Routes (`/api/secure-computations`)
```python
# File: backend/routers/secure_computations.py

GET    /api/secure-computations/available-computations
       # Returns all 18 computation types with descriptions

POST   /api/secure-computations/computations
       # Create new secure computation
       Body: {
           "name": "Multi-Hospital Correlation Study",
           "type": "secure_correlation",
           "description": "Analyze BMI vs Cholesterol",
           "invited_org_ids": [1, 2, 3],
           "security_method": "hybrid"
       }

GET    /api/secure-computations/computations
       # List all computations for current user
       Query: ?status=waiting_for_participants&type=secure_correlation

GET    /api/secure-computations/computations/{id}
       # Get specific computation details

POST   /api/secure-computations/computations/{id}/submit-data
       # Submit data for computation (CSV upload)
       Form Data:
           - file: CSV file
           - columns: "bmi,cholesterol_total"

POST   /api/secure-computations/computations/{id}/accept
       # Accept invitation to participate

POST   /api/secure-computations/computations/{id}/decline
       # Decline invitation

DELETE /api/secure-computations/computations/{id}
       # Delete computation (only if not completed)

GET    /api/secure-computations/computations/{id}/results
       # Get computation results

POST   /api/secure-computations/computations/{id}/export
       # Export results (PDF/CSV/JSON)
```

#### Analytics Routes (`/api/analytics`)
```python
# File: backend/routers/analytics.py

GET    /api/analytics/dashboard-stats
       # Get dashboard statistics

GET    /api/analytics/computation-trends
       # Get computation trends over time

GET    /api/analytics/organization-activity
       # Get organization activity metrics
```

#### Machine Learning Routes (`/api/ml`)
```python
# File: backend/routers/machine_learning.py

POST   /api/ml/train-model
       # Train federated learning model

GET    /api/ml/models
       # List available models

POST   /api/ml/predict
       # Make predictions using trained model
```

### 4.3 Request/Response Flow Example

**Example: Creating a Secure Correlation Computation**

**1. Frontend Request**
```javascript
// File: app/components/SecureComputationWizard.jsx
const response = await fetch('/api/secure-computations/computations', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${accessToken}`
    },
    body: JSON.stringify({
        name: "BMI vs Cholesterol Analysis",
        type: "secure_correlation",
        description: "Analyze correlation across 4 hospitals",
        invited_org_ids: [1, 2, 3, 4],
        security_method: "hybrid"
    })
});
```

**2. Backend Route Handler**
```python
# File: backend/routers/secure_computations.py
@router.post("/computations")
async def create_computation(
    computation_data: ComputationCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 1. Validate input (automatic via Pydantic)
    # 2. Check permissions
    # 3. Create computation
    service = SecureComputationService(db)
    computation = service.create_computation_with_invitations(
        creator_org_id=current_user["id"],
        name=computation_data.name,
        computation_type=computation_data.type,
        invited_org_ids=computation_data.invited_org_ids
    )
    
    # 4. Send WebSocket notifications
    await smpc_manager.notify_new_computation(computation.id)
    
    # 5. Return response
    return {
        "id": computation.id,
        "status": "waiting_for_participants",
        "created_at": computation.created_at.isoformat()
    }
```

**3. Service Layer**
```python
# File: backend/secure_computation.py
def create_computation_with_invitations(self, creator_org_id, name, computation_type, invited_org_ids):
    # Create computation record
    computation = SecureComputation(
        id=str(uuid.uuid4()),
        name=name,
        type=computation_type,
        status="waiting_for_participants",
        created_by=creator_org_id
    )
    self.db.add(computation)
    
    # Create invitations
    for org_id in invited_org_ids:
        invitation = ComputationInvitation(
            computation_id=computation.id,
            invited_org_id=org_id,
            inviter_org_id=creator_org_id,
            status="pending"
        )
        self.db.add(invitation)
    
    self.db.commit()
    return computation
```

**4. Database Operations**
```sql
-- SQLAlchemy generates these queries:

INSERT INTO secure_computations (id, name, type, status, created_by, created_at)
VALUES ('uuid-here', 'BMI vs Cholesterol Analysis', 'secure_correlation', 
        'waiting_for_participants', 1, '2025-10-25 12:00:00');

INSERT INTO computation_invitations (computation_id, invited_org_id, inviter_org_id, status)
VALUES ('uuid-here', 2, 1, 'pending'),
       ('uuid-here', 3, 1, 'pending'),
       ('uuid-here', 4, 1, 'pending');
```

**5. WebSocket Notification**
```python
# File: backend/websocket.py
async def notify_new_computation(self, computation_id: str):
    # Notify all connected organizations
    message = {
        "type": "new_computation",
        "computation_id": computation_id,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    for org_id, connections in self.active_connections.items():
        for websocket in connections:
            await websocket.send_json(message)
```

**6. Frontend Receives Response**
```javascript
// Update UI with new computation
setComputations(prev => [...prev, response.data]);
showNotification("Computation created successfully!");
```

---

## 5. DATABASE DESIGN

### 5.1 Database Schema Overview

```
┌─────────────────┐
│  organizations  │ (Users/Organizations)
│  - id           │
│  - email        │
│  - password_hash│
│  - role         │
│  - type         │
└────────┬────────┘
         │ 1:N
         │
┌────────▼────────────────┐
│  secure_computations    │ (Computation requests)
│  - id                   │
│  - name                 │
│  - type                 │
│  - status               │
│  - created_by           │
│  - result (JSON)        │
└────────┬────────────────┘
         │ 1:N
         │
┌────────▼─────────────────┐
│  computation_invitations │ (Who's invited)
│  - computation_id        │
│  - invited_org_id        │
│  - inviter_org_id        │
│  - status                │
└──────────────────────────┘

┌─────────────────────────┐
│  computation_participants│ (Who accepted)
│  - computation_id        │
│  - org_id                │
│  - joined_at             │
│  - status                │
└────────┬────────────────┘
         │ 1:N
         │
┌────────▼────────────────┐
│  computation_results    │ (Data submissions)
│  - id                   │
│  - computation_id       │
│  - org_id               │
│  - data_points (JSON)   │
│  - encryption_type      │
└─────────────────────────┘
```

### 5.2 Key Database Tables

#### 1. Organizations Table
```python
# File: backend/models.py
class Organization(Base):
    __tablename__ = "organizations"
    
    # Primary Key
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic Info
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    contact = Column(String(50), nullable=False)
    type = Column(Enum(OrgType), nullable=False)  # HOSPITAL, CLINIC, LAB, etc.
    location = Column(String(200), nullable=False)
    
    # Authentication
    password_hash = Column(String(200), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.PATIENT)
    
    # Security
    email_verified = Column(Boolean, default=False)
    two_factor_enabled = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    account_locked_until = Column(DateTime)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
```

**Why these fields?**
- `email` is unique and indexed for fast login lookups
- `type` enum ensures data integrity (only valid org types)
- `failed_login_attempts` prevents brute force attacks
- `email_verified` ensures valid email addresses
- `role` enables RBAC (Role-Based Access Control)

#### 2. Secure Computations Table
```python
class SecureComputation(Base):
    __tablename__ = "secure_computations"
    
    id = Column(String(36), primary_key=True)  # UUID
    name = Column(String(200), nullable=False)
    type = Column(String(50), nullable=False)  # secure_correlation, etc.
    description = Column(String(1000))
    
    # Status tracking
    status = Column(String(50), default="waiting_for_participants")
    # Possible values: waiting_for_participants, waiting_for_data, 
    #                  computing, completed, error
    
    # Results
    result = Column(JSON)  # Stores computation results as JSON
    
    # Error handling
    error_message = Column(String(500))
    error_code = Column(String(50))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Foreign Keys
    created_by = Column(Integer, ForeignKey("organizations.id"))
```

**Why JSON for results?**
- Different computation types return different result structures
- Flexible schema for correlation (coefficient, p-value) vs regression (coefficients, R²)
- No need for separate tables for each computation type
- Easy to query and display in frontend

#### 3. Computation Results Table
```python
class ComputationResult(Base):
    __tablename__ = "computation_results"
    
    id = Column(Integer, primary_key=True)
    computation_id = Column(String(36), ForeignKey("secure_computations.id"))
    org_id = Column(Integer, ForeignKey("organizations.id"))
    
    # Encrypted data storage
    data_points = Column(JSON)  # Stores encrypted data
    encryption_type = Column(String(50))  # "homomorphic", "smpc", "hybrid"
    
    # Metadata
    data_points_count = Column(Integer)
    submitted_at = Column(DateTime, default=datetime.utcnow)
```

**Data Points Structure Example:**
```json
{
    "homomorphic": [
        {"type": "paillier", "ciphertext": {"value": "12345...", "public_key": {...}}},
        {"type": "paillier", "ciphertext": {"value": "67890...", "public_key": {...}}}
    ],
    "smpc_shares": [
        {"shares": [{"party_id": 1, "value": 123}, {"party_id": 2, "value": 456}]},
        {"shares": [{"party_id": 1, "value": 789}, {"party_id": 2, "value": 012}]}
    ]
}
```

### 5.3 Database Indexes

```python
# Automatically created by SQLAlchemy based on index=True
CREATE INDEX ix_organizations_email ON organizations(email);
CREATE INDEX ix_organizations_id ON organizations(id);
CREATE INDEX ix_uploads_org_id ON uploads(org_id);
CREATE INDEX ix_secure_computations_created_by ON secure_computations(created_by);
CREATE INDEX ix_computation_results_computation_id ON computation_results(computation_id);
CREATE INDEX ix_computation_results_org_id ON computation_results(org_id);
```

**Why these indexes?**
- `organizations.email`: Fast login queries
- `uploads.org_id`: Quick lookup of user's uploads
- `computation_results.computation_id`: Fast aggregation of all submissions for a computation
- `computation_results.org_id`: Check if organization already submitted data

### 5.4 Database Relationships

```python
# One-to-Many: Organization -> Uploads
class Organization(Base):
    uploads = relationship("Upload", back_populates="organization", cascade="all, delete-orphan")

class Upload(Base):
    org_id = Column(Integer, ForeignKey("organizations.id"))
    organization = relationship("Organization", back_populates="uploads")
```

**Cascade Delete:**
- When organization is deleted, all their uploads are automatically deleted
- Maintains referential integrity
- Prevents orphaned records

---

**Continue to INTERVIEW_PART2.md for:**
- File Handling Deep Dive
- Request/Response Lifecycle
- Security Implementation
- Cryptography Details
- WebSocket Real-time Features
- Testing & Deployment
