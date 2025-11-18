# Quick Start: Security Improvements

## Installation (5 minutes)

```bash
# 1. Install new dependencies
cd backend
pip install pycryptodome slowapi

# 2. Run database migrations
python -c "from models import Base, engine; Base.metadata.create_all(bind=engine)"

# 3. Test implementation
python -m pytest tests/test_security.py  # (create tests)
```

## Usage Examples

### 1. SMPC with Secure Primes
```python
from smpc_protocols import ShamirSecretSharing

# Automatically uses secure random primes
shamir = ShamirSecretSharing()  # Generates 256-bit prime
shares = shamir.split_secret(42, n=5, k=3)
secret = shamir.reconstruct_secret(shares[:3])
```

### 2. Enhanced Homomorphic Encryption
```python
from homomorphic_encryption_enhanced import EnhancedHomomorphicEncryption

# Minimum 3072-bit keys with integrity checks
he = EnhancedHomomorphicEncryption()  # Auto-upgrades to 3072 bits
encrypted = he.encrypt(100.5)
decrypted = he.decrypt(encrypted)  # Verifies integrity automatically
```

### 3. Privacy Budget Enforcement
```python
from privacy_accountant import privacy_accountant, PrivacyBudgetExceededError

try:
    # Check and consume budget
    privacy_accountant.check_and_consume_budget(
        org_id="hospital_123",
        epsilon_cost=0.5
    )
    # Proceed with computation
except PrivacyBudgetExceededError:
    return {"error": "Privacy budget exceeded", "retry_after": "24h"}
```

### 4. Medical Data Validation
```python
from encryption_utils import validate_medical_value

# Validates against biologically plausible ranges
validate_medical_value("heart_rate", 75)  # ✓ Valid
validate_medical_value("heart_rate", 300)  # ✗ Raises ValueError
```

### 5. API Rate Limiting
```python
from fastapi import FastAPI, Request
from api_security import limiter, RateLimitMiddleware

app = FastAPI()
app.add_middleware(RateLimitMiddleware, requests_per_minute=60)

@app.post("/api/upload")
@limiter.limit("10/minute")
async def upload_data(request: Request, data: UploadData):
    # Automatically rate limited
    return {"status": "success"}
```

### 6. CSRF Protection
```python
from api_security import csrf_protection

# Generate token (backend)
csrf_token = csrf_protection.generate_token(session_id)

# Validate token (in endpoint)
if not csrf_protection.validate_token(csrf_token, session_id):
    raise HTTPException(403, "Invalid CSRF token")
```

### 7. Secure Frontend Storage
```javascript
// Replace localStorage with secureStorage
import secureStorage from '@/utils/secureStorage';

// Store token
secureStorage.setItem('auth_token', jwt);

// Retrieve token
const token = secureStorage.getItem('auth_token');

// Check expiration
if (secureStorage.isTokenExpired(token)) {
    // Refresh or logout
}
```

### 8. Tamper-Proof Audit Logging
```python
from models import TamperProofAuditLog

# Create audit entry
last_log = db.query(TamperProofAuditLog).order_by(
    TamperProofAuditLog.id.desc()
).first()

log = TamperProofAuditLog(
    user_id=user.id,
    action="data_access",
    resource_type="health_record",
    resource_id=record_id,
    previous_hash=last_log.current_hash if last_log else "0" * 64
)
log.current_hash = log.generate_hash()
db.add(log)

# Verify chain integrity
if not log.verify_chain(last_log):
    raise SecurityError("Audit log tampering detected!")
```

## Common Issues & Solutions

### Issue: "pycryptodome not found"
```bash
# Solution
pip install pycryptodome
# Or use fallback (automatic, uses Miller-Rabin)
```

### Issue: "Rate limit exceeded (429)"
```python
# Solution: Adjust rate limits in api_security.py
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
```

### Issue: "CSP blocking resources"
```javascript
// Solution: Add domain to next.config.js
"connect-src 'self' https://your-api-domain.com"
```

### Issue: "Privacy budget exceeded"
```python
# Solution: Check budget status
summary = privacy_accountant.get_budget_summary(org_id)
print(f"Remaining: {summary['remaining_budget']}")

# Or reset (admin only)
privacy_accountant.reset_budget(org_id)
```

## Testing Checklist

- [ ] SMPC generates different primes each session
- [ ] HE uses 3072-bit keys minimum
- [ ] Medical values validated (test invalid ranges)
- [ ] Rate limiting returns 429 when exceeded
- [ ] CSRF tokens validated on state changes
- [ ] Privacy budget blocks when exceeded
- [ ] Audit log chain verifies correctly
- [ ] CSP headers present in browser

## Performance Notes

| Feature | Impact | Mitigation |
|---------|--------|------------|
| Secure Prime Gen | +2-3s startup | Cache primes, generate async |
| 3072-bit HE | +30% slower | Use 2048 for dev, 3072 prod |
| Medical Validation | <1ms/value | Negligible |
| Rate Limiting | <1ms/request | In-memory, very fast |
| Audit Logging | +5-10ms/write | Acceptable for security |

## Next Steps

1. **Run Tests:** Verify all improvements work
2. **Update Frontend:** Replace localStorage calls
3. **Configure Limits:** Adjust rate limits for your scale
4. **Monitor:** Set up alerts for security events
5. **Document:** Update API docs with new security features

## Support

- **Documentation:** See `SECURITY_IMPROVEMENTS.md`
- **Issues:** GitHub Issues
- **Security:** Report privately via Security Advisories
