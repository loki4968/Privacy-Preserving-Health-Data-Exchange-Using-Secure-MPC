from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, LargeBinary, Enum, Boolean, create_engine, event, Date, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime, date
from encryption_utils import EncryptionManager, validate_health_data, sanitize_health_data
from auth_utils import UserRole
from config import DATABASE_URL, DATABASE_CONNECT_ARGS
import enum
import json
import os
import uuid

# Database setup
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args=DATABASE_CONNECT_ARGS,
        pool_pre_ping=True,
    )
else:
    # For PostgreSQL and other databases, don't pass connect_args as they contain pool parameters
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )

# SQLite pragmas to reduce locking and improve concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA synchronous=NORMAL;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.close()
    except Exception:
        # If not SQLite or pragma fails, ignore
        pass
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class OrgType(str, enum.Enum):
    HOSPITAL = "HOSPITAL"
    CLINIC = "CLINIC"
    LABORATORY = "LABORATORY"
    PHARMACY = "PHARMACY"
    PATIENT = "PATIENT"

class Organization(Base):
    __tablename__ = "organizations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    contact = Column(String(50), nullable=False)
    type = Column(Enum(OrgType), nullable=False)
    location = Column(String(200), nullable=False)
    privacy_accepted = Column(Boolean, nullable=False, default=False)
    password_hash = Column(String(200), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.PATIENT)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True, nullable=False)
    email_verified = Column(Boolean, default=False, nullable=False)
    two_factor_enabled = Column(Boolean, default=False, nullable=False)
    two_factor_secret = Column(String(32))
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    last_failed_login = Column(DateTime)
    account_locked_until = Column(DateTime)
    password_changed_at = Column(DateTime)
    last_password_reset = Column(DateTime)
    session_tokens = Column(JSON, default=list)  # Store refresh tokens

    uploads = relationship("Upload", back_populates="organization", cascade="all, delete-orphan")
    health_records = relationship("SecureHealthRecord", back_populates="organization", cascade="all, delete-orphan")
    computation_results = relationship("SecureComputationResult", back_populates="organization", cascade="all, delete-orphan")

class Upload(Base):
    __tablename__ = "uploads"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    category = Column(String(50), nullable=False)
    org_id = Column(Integer, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    file_size = Column(Integer, nullable=False)  # in bytes
    mime_type = Column(String(100), nullable=False)
    result = Column(JSON)
    status = Column(String(20), default="pending", nullable=False)  # pending, processing, completed, error
    error_message = Column(String(500))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime)

    organization = relationship("Organization", back_populates="uploads")

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "category": self.category,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "has_error": bool(self.error_message),
            "error_message": self.error_message,
            "file_size": self.file_size,
            "result": self.result,
            "org_id": self.org_id
        }

    def get_file_path(self):
        """Get the absolute path to the uploaded file."""
        return os.path.join(UPLOAD_DIR, str(self.org_id), self.filename)

    def verify_file(self):
        """Verify the uploaded file exists and matches the stored checksum."""
        file_path = self.get_file_path()
        if not file_path or not os.path.exists(file_path):
            return False
        if not self.checksum:
            return True  # Skip verification if no checksum stored
        current_hash = hash_file_content(file_path)
        return current_hash == self.checksum

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"))
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String(45))
    user_agent = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("Organization")


class TamperProofAuditLog(Base):
    """Tamper-evident audit log with chain integrity"""
    __tablename__ = "audit_logs_secured"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("organizations.id", ondelete="SET NULL"))
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100))  # Support UUID strings
    log_entry = Column(LargeBinary, nullable=False)  # Encrypted log data
    previous_hash = Column(String(64), index=True)  # Chain integrity
    current_hash = Column(String(64), unique=True, nullable=False, index=True)  # Entry hash
    signature = Column(LargeBinary)  # Digital signature for non-repudiation
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    data_access_pattern = Column(JSON)  # Track who accessed what, when
    
    user = relationship("Organization")
    
    def generate_hash(self) -> str:
        """Generate SHA-256 hash for this log entry"""
        data = f"{self.user_id}:{self.action}:{self.resource_type}:{self.resource_id}:{self.created_at.isoformat()}:{self.previous_hash}".encode()
        return hashlib.sha256(data).hexdigest()
    
    def verify_chain(self, previous_log: 'TamperProofAuditLog' = None) -> bool:
        """Verify the integrity of the log chain"""
        if previous_log:
            return self.previous_hash == previous_log.current_hash
        # First log entry should have None or genesis hash
        return self.previous_hash is None or self.previous_hash == "0" * 64

class SecureHealthRecord(Base):
    __tablename__ = "secure_health_records"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"))
    data_type = Column(String)
    encrypted_value = Column(LargeBinary, nullable=False)  # Binary storage for efficiency
    encryption_metadata = Column(JSON)  # Store IV, salt, version info
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="health_records")
    
    def encrypt_value(self, value: str):
        """Encrypt the health record value"""
        encryption_manager = EncryptionManager()
        self.encrypted_value = encryption_manager.encrypt(value)

    def decrypt_value(self) -> str:
        """Decrypt the health record value"""
        encryption_manager = EncryptionManager()
        return encryption_manager.decrypt(self.encrypted_value)

    def set_data(self, data: dict):
        """Set and encrypt the health record data with enhanced validation"""
        # Validate the data structure
        if not validate_health_data(data):
            raise ValueError("Invalid health data format")
        
        # Additional validation for health records
        if not isinstance(data.get("patient_id"), str) or len(data["patient_id"]) < 3:
            raise ValueError("Patient ID must be at least 3 characters long")
        
        # Validate data type is appropriate for health records
        valid_health_types = [
            "blood_pressure", "heart_rate", "temperature", "weight", 
            "height", "glucose_level", "medication", "diagnosis",
            "lab_result", "vital_signs", "medical_history", "allergy",
            "vaccination", "procedure", "imaging", "consultation"
        ]
        
        if data.get("data_type") not in valid_health_types:
            print(f"Warning: Unusual health data type: {data.get('data_type')}")
        
        # Sanitize the data
        sanitized_data = sanitize_health_data(data)
        
        # Add validation timestamp
        sanitized_data["validated_at"] = datetime.utcnow().isoformat()
        
        # Convert to string for encryption
        data_str = json.dumps(sanitized_data, sort_keys=True)
        
        # Encrypt the data
        self.encrypt_value(data_str)

    def get_data(self) -> dict:
        """Get and decrypt the health record data"""
        if not self.encrypted_value:
            return None
        
        # Decrypt the data
        decrypted_str = self.decrypt_value()
        
        # Parse JSON string back to dictionary
        try:
            return json.loads(decrypted_str)
        except json.JSONDecodeError:
            raise ValueError("Failed to decode health record data")

class SecureComputation(Base):
    __tablename__ = 'secure_computations'

    id = Column(Integer, primary_key=True)
    computation_id = Column(String, unique=True, nullable=False)
    org_id = Column(Integer, nullable=False)
    type = Column(String, nullable=False)
    security_method = Column(String, default="homomorphic")  # standard, homomorphic, hybrid
    status = Column(String, nullable=False)
    result = Column(JSON)
    error_message = Column(String)
    error_code = Column(String)
    parameters = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)

    participants = relationship("ComputationParticipant", back_populates="computation")
    results = relationship("ComputationResult", back_populates="computation")

class ComputationParticipant(Base):
    __tablename__ = 'computation_participants'

    id = Column(Integer, primary_key=True)
    computation_id = Column(String, ForeignKey('secure_computations.computation_id'), nullable=False)
    org_id = Column(Integer, nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)

    computation = relationship("SecureComputation", back_populates="participants")

class ComputationInvitation(Base):
    __tablename__ = 'computation_invitations'

    id = Column(Integer, primary_key=True)
    computation_id = Column(String, ForeignKey('secure_computations.computation_id'), nullable=False)
    invited_org_id = Column(Integer, ForeignKey('organizations.id'), nullable=False)
    inviter_org_id = Column(Integer, ForeignKey('organizations.id'), nullable=False)
    status = Column(String, default='pending', nullable=False)  # pending, accepted, declined
    invited_at = Column(DateTime, default=datetime.utcnow)
    responded_at = Column(DateTime)

    computation = relationship("SecureComputation")
    invited_org = relationship("Organization", foreign_keys=[invited_org_id])
    inviter_org = relationship("Organization", foreign_keys=[inviter_org_id])

class ComputationResult(Base):
    __tablename__ = 'computation_results'

    id = Column(Integer, primary_key=True)
    computation_id = Column(String, ForeignKey('secure_computations.computation_id'), nullable=False)
    org_id = Column(Integer, nullable=False)
    data_points = Column(JSON, nullable=False)
    encryption_type = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    computation = relationship("SecureComputation", back_populates="results")


class ComputationPatientRecord(Base):
    __tablename__ = "computation_patient_records"

    id = Column(Integer, primary_key=True)
    computation_id = Column(String, ForeignKey('secure_computations.computation_id'), nullable=False)
    org_id = Column(Integer, nullable=False)
    patient_id = Column(String, nullable=False)
    metric_name = Column(String)
    value = Column(Float, nullable=False)

class SecureComputationResult(Base):
    __tablename__ = "secure_computation_results"

    id = Column(Integer, primary_key=True, index=True)
    computation_id = Column(String, index=True)
    org_id = Column(Integer, ForeignKey("organizations.id"))
    computation_type = Column(String)
    encrypted_result = Column(LargeBinary)
    result_metadata = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    organization = relationship("Organization", back_populates="computation_results")
    
    def __init__(self, **kwargs):
        self.encryption_manager = EncryptionManager()
        super().__init__(**kwargs)
    
    def set_result(self, result: dict):
        """Encrypt and store computation result."""
        self.encrypted_result, _ = self.encryption_manager.encrypt_data(result)
    
    def get_result(self) -> dict:
        """Decrypt and retrieve computation result."""
        if not self.encrypted_result:
            return None
        return self.encryption_manager.decrypt_data(self.encrypted_result)


class ReportRequestStatus(enum.Enum):
    """Status of a report request."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ReportRequest(Base):
    """Model for patient report requests."""
    __tablename__ = "report_requests"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    patient_id = Column(Integer, ForeignKey("organizations.id"))
    organization_id = Column(Integer, ForeignKey("organizations.id"))
    visit_date = Column(Date, nullable=False)
    description = Column(String, nullable=True)
    status = Column(Enum(ReportRequestStatus), default=ReportRequestStatus.PENDING)
    request_date = Column(DateTime, default=datetime.utcnow)
    response_date = Column(DateTime, nullable=True)
    rejection_reason = Column(String, nullable=True)
    report_file_path = Column(String, nullable=True)
    secret_code = Column(String(8), nullable=True, index=True)
    
    # Relationships
    patient = relationship("Organization", foreign_keys=[patient_id])
    organization = relationship("Organization", foreign_keys=[organization_id])
    
    def generate_secret_code(self):
        """Generate a random 8-character alphanumeric secret code."""
        import random
        import string
        chars = string.ascii_uppercase + string.digits
        self.secret_code = ''.join(random.choice(chars) for _ in range(8))
        return self.secret_code