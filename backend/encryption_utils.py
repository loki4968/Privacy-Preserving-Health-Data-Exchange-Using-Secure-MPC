import base64
import json
import os
import hashlib
from typing import Tuple, Any, Dict

# Try to import cryptography, fallback to simple encryption if not available
try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    print("Warning: cryptography library not available. Using fallback encryption.")
    CRYPTOGRAPHY_AVAILABLE = False


class EncryptionManager:
    """
    Improved encryption manager using Fernet (AES 128 in CBC mode with HMAC).
    Simple but secure implementation suitable for college projects.
    """

    def __init__(self, password: str = None):
        # Generate or derive encryption key
        if CRYPTOGRAPHY_AVAILABLE:
            if password:
                # Derive key from password for consistent encryption
                salt = b'college_project_salt'  # Fixed salt for simplicity
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=salt,
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
            else:
                # Generate random key
                key = Fernet.generate_key()
            
            self.cipher = Fernet(key)
            self.key = key
            self.use_fallback = False
        else:
            # Fallback to simple XOR encryption for demo purposes
            self.key = os.urandom(32) if not password else hashlib.sha256(password.encode()).digest()
            self.cipher = None
            self.use_fallback = True

    def encrypt(self, plaintext: str) -> str:
        """Encrypt data using Fernet (AES + HMAC) or fallback"""
        if not self.use_fallback and self.cipher:
            try:
                encrypted_data = self.cipher.encrypt(plaintext.encode('utf-8'))
                return base64.urlsafe_b64encode(encrypted_data).decode('utf-8')
            except Exception as e:
                print(f"Encryption error: {e}")
                # Fall through to fallback
        
        # Fallback XOR encryption for demo purposes
        data = plaintext.encode('utf-8')
        encrypted = bytes(b ^ (self.key[i % len(self.key)]) for i, b in enumerate(data))
        return base64.b64encode(encrypted).decode('utf-8')

    def decrypt(self, ciphertext: str) -> str:
        """Decrypt data using Fernet or fallback"""
        if not self.use_fallback and self.cipher:
            try:
                encrypted_data = base64.urlsafe_b64decode(ciphertext.encode('utf-8'))
                decrypted_data = self.cipher.decrypt(encrypted_data)
                return decrypted_data.decode('utf-8')
            except Exception as e:
                print(f"Decryption error: {e}")
                # Fall through to fallback
        
        # Fallback XOR decryption
        try:
            encrypted = base64.b64decode(ciphertext)
            decrypted = bytes(b ^ (self.key[i % len(self.key)]) for i, b in enumerate(encrypted))
            return decrypted.decode('utf-8')
        except Exception as e:
            print(f"Fallback decryption error: {e}")
            return ciphertext  # Return as-is if all fails

    def encrypt_data(self, obj: Any) -> Tuple[bytes, dict]:
        """Encrypt complex data objects"""
        serialized = json.dumps(obj, separators=(",", ":"))
        encrypted = self.encrypt(serialized)
        return encrypted.encode("utf-8"), {"alg": "fernet-aes", "ver": 2}

    def decrypt_data(self, data: bytes) -> Any:
        """Decrypt complex data objects"""
        decrypted_str = self.decrypt(data.decode("utf-8"))
        return json.loads(decrypted_str)

    def hash_data(self, data: str) -> str:
        """Create a secure hash of the data"""
        return hashlib.sha256(data.encode()).hexdigest()

    def verify_hash(self, data: str, hash_value: str) -> bool:
        """Verify if the data matches the hash"""
        return self.hash_data(data) == hash_value


# Medical data validation ranges (biologically plausible values)
MEDICAL_RANGES = {
    "blood_pressure_systolic": (60, 250),  # mmHg
    "blood_pressure_diastolic": (40, 150),  # mmHg
    "heart_rate": (30, 250),  # bpm
    "temperature": (32.0, 42.0),  # Celsius
    "temperature_f": (89.6, 107.6),  # Fahrenheit
    "weight": (2.0, 500.0),  # kg
    "height": (30.0, 300.0),  # cm
    "glucose_level": (20, 600),  # mg/dL
    "oxygen_saturation": (50, 100),  # %
    "respiratory_rate": (8, 60),  # breaths per minute
    "cholesterol_total": (100, 400),  # mg/dL
    "cholesterol_hdl": (20, 100),  # mg/dL
    "cholesterol_ldl": (50, 300),  # mg/dL
    "triglycerides": (30, 500),  # mg/dL
}


def validate_medical_value(metric: str, value: float) -> bool:
    """
    Validate that a health metric value is within biologically plausible range.
    
    Args:
        metric: The health metric name
        value: The numeric value to validate
        
    Returns:
        True if valid, raises ValueError if invalid
    """
    # Normalize metric name
    metric_lower = metric.lower().replace(" ", "_")
    
    if metric_lower in MEDICAL_RANGES:
        min_val, max_val = MEDICAL_RANGES[metric_lower]
        if not (min_val <= value <= max_val):
            raise ValueError(
                f"Invalid {metric}: {value}. "
                f"Expected range: {min_val}-{max_val}"
            )
    
    return True


def validate_health_data(data: dict) -> bool:
    """
    Enhanced validation for health data with biologically plausible range checks.
    """
    if not isinstance(data, dict):
        print("Data must be a dictionary")
        return False
    
    # Required fields for health data
    required_fields = ["patient_id", "data_type", "timestamp"]
    
    # Check required fields
    for field in required_fields:
        if field not in data:
            print(f"Missing required field: {field}")
            return False
    
    # Validate data types
    if not isinstance(data["patient_id"], str) or len(data["patient_id"]) < 3:
        print("patient_id must be a string with at least 3 characters")
        return False
        
    if not isinstance(data["data_type"], str):
        print("data_type must be a string")
        return False
        
    if not isinstance(data["timestamp"], str):
        print("timestamp must be a string")
        return False
    
    # Validate data field exists and is appropriate
    if "data" not in data:
        print("Missing 'data' field")
        return False
    
    # Check for common health data types
    valid_data_types = [
        "blood_pressure", "heart_rate", "temperature", "weight", 
        "height", "glucose_level", "medication", "diagnosis",
        "lab_result", "vital_signs", "medical_history"
    ]
    
    if data["data_type"] not in valid_data_types:
        print(f"Warning: data_type '{data['data_type']}' not in standard health types")
    
    # Validate numeric health values against medical ranges
    if isinstance(data.get("data"), dict):
        for metric, value in data["data"].items():
            if isinstance(value, (int, float)):
                try:
                    validate_medical_value(metric, value)
                except ValueError as e:
                    print(f"Medical range validation failed: {e}")
                    return False
    
    print("Health data validation passed")
    return True


def sanitize_health_data(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enhanced sanitization for health data.
    Removes sensitive information and validates content.
    """
    print(f"Sanitizing health data for type: {data.get('data_type', 'unknown')}")
    
    # Create a copy to avoid modifying original
    sanitized_data = data.copy()
    
    # Remove or mask highly sensitive fields
    sensitive_fields = [
        "ssn", "social_security_number", "insurance_number", 
        "phone_number", "address", "email", "full_name",
        "credit_card", "bank_account"
    ]
    
    for field in sensitive_fields:
        if field in sanitized_data:
            sanitized_data[field] = "***REDACTED***"
    
    # Sanitize nested data if it exists
    if "data" in sanitized_data and isinstance(sanitized_data["data"], dict):
        data_section = sanitized_data["data"]
        for field in sensitive_fields:
            if field in data_section:
                data_section[field] = "***REDACTED***"
    
    # Add sanitization timestamp
    sanitized_data["sanitized_at"] = str(hash(str(sanitized_data)))[:8]
    
    print(f"Sanitized data: removed {len([f for f in sensitive_fields if f in data])} sensitive fields")
    return sanitized_data

class SecureComputation:
    def __init__(self):
        self.encryption_manager = EncryptionManager()

    def secure_aggregate(self, values: list, operation: str) -> Dict[str, Any]:
        """Perform secure aggregation on encrypted values"""
        if not values:
            raise ValueError("No values to aggregate")

        # Decrypt values
        decrypted_values = [float(self.encryption_manager.decrypt(v)) for v in values]

        if operation == 'average':
            return {'value': sum(decrypted_values) / len(decrypted_values)}
        elif operation == 'sum':
            return {'value': sum(decrypted_values)}
        elif operation == 'min':
            return {'value': min(decrypted_values)}
        elif operation == 'max':
            return {'value': max(decrypted_values)}
        else:
            raise ValueError(f"Unsupported operation: {operation}")

    def secure_compare(self, value1: str, value2: str) -> bool:
        """Securely compare two encrypted values"""
        decrypted1 = float(self.encryption_manager.decrypt(value1))
        decrypted2 = float(self.encryption_manager.decrypt(value2))
        return decrypted1 > decrypted2

# Note: Enhanced validation and sanitization functions are defined above