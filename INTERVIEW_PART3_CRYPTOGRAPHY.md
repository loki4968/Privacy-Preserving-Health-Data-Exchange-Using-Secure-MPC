# Interview Guide Part 3: Cryptography & Security

## 9. CRYPTOGRAPHY IMPLEMENTATION

### 9.1 Three Security Methods

**1. Standard Encryption (Basic)**
- Used for: Non-sensitive metadata, file storage
- Algorithm: AES-256-CBC
- Key management: Environment variables

**2. Homomorphic Encryption (Advanced)**
- Used for: Computations on encrypted data
- Algorithm: Paillier Cryptosystem
- Allows: Addition and scalar multiplication on ciphertexts

**3. Hybrid (HE + SMPC) (Maximum Security)**
- Used for: Advanced computations (correlation, regression)
- Combines: Homomorphic Encryption + Secret Sharing
- Provides: Maximum privacy with distributed trust

### 9.2 Homomorphic Encryption (Paillier)

**Mathematical Foundation:**
```
Public Key: (n, g) where n = p × q (large primes)
Private Key: (λ, μ) where λ = lcm(p-1, q-1)

Encryption: E(m) = g^m × r^n mod n²
Decryption: D(c) = L(c^λ mod n²) × μ mod n

Properties:
  E(m1) × E(m2) = E(m1 + m2)  [Additive homomorphism]
  E(m)^k = E(k × m)            [Scalar multiplication]
```

**Implementation:**
```python
# File: backend/homomorphic_encryption_enhanced.py
class EnhancedHomomorphicEncryption:
    def __init__(self, key_size=2048):
        self.key_size = key_size
        self.public_key, self.private_key = self._generate_keypair()
    
    def _generate_keypair(self):
        """Generate Paillier keypair"""
        # Generate two large primes
        p = self._generate_prime(self.key_size // 2)
        q = self._generate_prime(self.key_size // 2)
        
        n = p * q
        g = n + 1  # Simplified generator
        λ = (p - 1) * (q - 1)  # Carmichael function
        μ = self._mod_inverse(λ, n)
        
        public_key = PublicKey(n, g)
        private_key = PrivateKey(λ, μ, n)
        
        return public_key, private_key
    
    def encrypt(self, plaintext: int) -> PaillierCiphertext:
        """Encrypt a plaintext integer"""
        n = self.public_key.n
        g = self.public_key.g
        
        # Generate random r
        r = random.randint(1, n - 1)
        
        # c = g^m × r^n mod n²
        n_squared = n * n
        ciphertext = (pow(g, plaintext, n_squared) * pow(r, n, n_squared)) % n_squared
        
        return PaillierCiphertext(ciphertext, self.public_key)
    
    def decrypt(self, ciphertext: PaillierCiphertext) -> int:
        """Decrypt a ciphertext"""
        λ = self.private_key.λ
        μ = self.private_key.μ
        n = self.private_key.n
        n_squared = n * n
        
        # m = L(c^λ mod n²) × μ mod n
        c_lambda = pow(ciphertext.value, λ, n_squared)
        L_value = (c_lambda - 1) // n
        plaintext = (L_value * μ) % n
        
        return plaintext
    
    def add_encrypted(self, c1: PaillierCiphertext, c2: PaillierCiphertext):
        """Add two encrypted values: E(m1 + m2) = E(m1) × E(m2)"""
        n_squared = self.public_key.n * self.public_key.n
        result = (c1.value * c2.value) % n_squared
        return PaillierCiphertext(result, self.public_key)
    
    def multiply_encrypted_by_scalar(self, ciphertext: PaillierCiphertext, scalar: int):
        """Multiply encrypted value by scalar: E(k × m) = E(m)^k"""
        n_squared = self.public_key.n * self.public_key.n
        result = pow(ciphertext.value, scalar, n_squared)
        return PaillierCiphertext(result, self.public_key)
```

**Usage Example:**
```python
# Encrypt two values
he = EnhancedHomomorphicEncryption()
enc1 = he.encrypt(10)  # E(10)
enc2 = he.encrypt(20)  # E(20)

# Add encrypted values
enc_sum = he.add_encrypted(enc1, enc2)  # E(10 + 20) = E(30)

# Decrypt result
result = he.decrypt(enc_sum)  # 30
```

### 9.3 Secure Multi-Party Computation (SMPC)

**Shamir's Secret Sharing:**
```
Goal: Split secret S into n shares, require t shares to reconstruct

Algorithm:
1. Choose random polynomial: f(x) = S + a₁x + a₂x² + ... + aₜ₋₁x^(t-1)
2. Generate shares: (1, f(1)), (2, f(2)), ..., (n, f(n))
3. Reconstruct: Use Lagrange interpolation with t shares

Example (t=2, n=3):
  Secret: S = 42
  Polynomial: f(x) = 42 + 5x
  Shares: (1, 47), (2, 52), (3, 57)
  
  Reconstruct with shares 1 and 2:
    L₁(0) = (0-2)/(1-2) = 2
    L₂(0) = (0-1)/(2-1) = -1
    S = 47×2 + 52×(-1) = 94 - 52 = 42 ✓
```

**Implementation:**
```python
# File: backend/smpc_protocols.py
class ShamirSecretSharing:
    def __init__(self, threshold: int, num_parties: int, prime: int = None):
        self.threshold = threshold
        self.num_parties = num_parties
        self.prime = prime or self._generate_large_prime()
    
    def split_secret(self, secret: int) -> List[Tuple[int, int]]:
        """Split secret into shares"""
        # Generate random polynomial coefficients
        coefficients = [secret] + [
            random.randint(0, self.prime - 1) 
            for _ in range(self.threshold - 1)
        ]
        
        # Evaluate polynomial at points 1, 2, ..., n
        shares = []
        for x in range(1, self.num_parties + 1):
            y = self._evaluate_polynomial(coefficients, x)
            shares.append((x, y))
        
        return shares
    
    def _evaluate_polynomial(self, coefficients: List[int], x: int) -> int:
        """Evaluate polynomial at point x"""
        result = 0
        for i, coeff in enumerate(coefficients):
            result += coeff * pow(x, i, self.prime)
            result %= self.prime
        return result
    
    def reconstruct_secret(self, shares: List[Tuple[int, int]]) -> int:
        """Reconstruct secret from shares using Lagrange interpolation"""
        if len(shares) < self.threshold:
            raise ValueError(f"Need at least {self.threshold} shares")
        
        # Use first threshold shares
        shares = shares[:self.threshold]
        
        # Lagrange interpolation at x=0
        secret = 0
        for i, (xi, yi) in enumerate(shares):
            # Calculate Lagrange basis polynomial L_i(0)
            numerator = 1
            denominator = 1
            
            for j, (xj, _) in enumerate(shares):
                if i != j:
                    numerator = (numerator * (-xj)) % self.prime
                    denominator = (denominator * (xi - xj)) % self.prime
            
            # Modular inverse
            denominator_inv = pow(denominator, -1, self.prime)
            lagrange_coeff = (numerator * denominator_inv) % self.prime
            
            secret += yi * lagrange_coeff
            secret %= self.prime
        
        return secret
```

### 9.4 Hybrid Encryption (HE + SMPC)

**Why Combine Both?**
```
Homomorphic Encryption:
  ✅ Allows computation on encrypted data
  ✅ Single party can perform operations
  ❌ Requires trust in key holder
  ❌ Computationally expensive

SMPC (Secret Sharing):
  ✅ Distributed trust (no single point of failure)
  ✅ Efficient for certain operations
  ❌ Requires multiple parties to collaborate
  ❌ Communication overhead

Hybrid (HE + SMPC):
  ✅ Best of both worlds
  ✅ Maximum security
  ✅ Flexible computation models
```

**Implementation:**
```python
# File: backend/secure_computation.py
def submit_data(self, computation_id, org_id, numeric_values):
    computation = self.db.query(SecureComputation).get(computation_id)
    
    # Determine if hybrid encryption is needed
    if computation.type in ["secure_correlation", "secure_sum", ...]:
        # Use hybrid encryption
        encrypted_data = {
            "homomorphic": [],
            "smpc_shares": []
        }
        
        for value in numeric_values:
            # 1. Homomorphic encryption
            enc_value = self.homomorphic_encryption.encrypt(value)
            encrypted_data["homomorphic"].append(enc_value.to_dict())
            
            # 2. SMPC shares
            shares = self.smpc_protocol.split_secret(int(value * 1000))
            encrypted_data["smpc_shares"].append({
                "shares": [{"party_id": i, "value": share} 
                          for i, share in shares]
            })
        
        encryption_type = "hybrid"
    else:
        # Use homomorphic encryption only
        encrypted_data = {
            "homomorphic": [
                self.homomorphic_encryption.encrypt(v).to_dict() 
                for v in numeric_values
            ]
        }
        encryption_type = "homomorphic"
    
    # Store encrypted data
    result = ComputationResult(
        computation_id=computation_id,
        org_id=org_id,
        data_points=encrypted_data,
        encryption_type=encryption_type
    )
    self.db.add(result)
    self.db.commit()
```

### 9.5 Secure Computation Execution

**Correlation Computation Flow:**
```
┌─────────────────────────────────────────────────────┐
│ Organization 1: [10, 20, 30] → Encrypt → Submit    │
│ Organization 2: [15, 25, 35] → Encrypt → Submit    │
│ Organization 3: [12, 22, 32] → Encrypt → Submit    │
│ Organization 4: [18, 28, 38] → Encrypt → Submit    │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│ Server: All data submitted, trigger computation     │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│ Extract SMPC shares from all submissions            │
│ all_shares = [shares_org1, shares_org2, ...]        │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│ Reconstruct values from shares                      │
│ x_values = [10, 20, 30, 15, 25, ...]               │
│ y_values = [15, 25, 35, 12, 22, ...]               │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│ Compute correlation coefficient                     │
│ r = Σ((x-x̄)(y-ȳ)) / √(Σ(x-x̄)² × Σ(y-ȳ)²)        │
└────────────────────┬────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────┐
│ Return results: {                                    │
│   "correlation_coefficient": 0.85,                  │
│   "p_value": 0.001,                                 │
│   "confidence_interval": {"lower": 0.78, ...}       │
│ }                                                    │
└─────────────────────────────────────────────────────┘
```

**Code Implementation:**
```python
# File: backend/advanced_smpc_computations.py
def secure_correlation_analysis(self, all_shares: List) -> Dict[str, Any]:
    # 1. Extract paired values from SMPC shares
    x_values, y_values = self._extract_paired_values(all_shares)
    
    # 2. Compute correlation
    correlation = self._secure_correlation(x_values, y_values)
    
    # 3. Statistical significance
    p_value = self._compute_p_value(correlation, len(x_values))
    
    # 4. Confidence interval
    ci = self._correlation_confidence_interval(correlation, len(x_values))
    
    return {
        "correlation_coefficient": float(correlation),
        "sample_size": len(x_values),
        "interpretation": self._interpret_correlation(correlation),
        "p_value": float(p_value),
        "confidence_interval": ci,
        "security_method": "Hybrid (Homomorphic Encryption + SMPC)"
    }

def _secure_correlation(self, x_values: List, y_values: List) -> float:
    """Pearson correlation coefficient"""
    n = len(x_values)
    mean_x = sum(x_values) / n
    mean_y = sum(y_values) / n
    
    numerator = sum((x_values[i] - mean_x) * (y_values[i] - mean_y) 
                    for i in range(n))
    
    sum_sq_x = sum((x - mean_x) ** 2 for x in x_values)
    sum_sq_y = sum((y - mean_y) ** 2 for y in y_values)
    
    denominator = (sum_sq_x * sum_sq_y) ** 0.5
    
    return numerator / denominator if denominator > 0 else 0.0
```

---

## 10. WEBSOCKET REAL-TIME FEATURES

### 10.1 WebSocket Architecture

```
┌─────────────────────────────────────────────────────┐
│ Frontend (React)                                    │
│  - WebSocket Client                                 │
│  - Auto-reconnect logic                             │
│  - Message handlers                                 │
└────────────────────┬────────────────────────────────┘
                     │ ws://localhost:8000/ws
┌────────────────────▼────────────────────────────────┐
│ Backend (FastAPI)                                   │
│  - WebSocket Manager                                │
│  - Connection pool                                  │
│  - Broadcast system                                 │
└─────────────────────────────────────────────────────┘
```

### 10.2 WebSocket Manager Implementation

```python
# File: backend/websocket.py
class SMPCWebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.user_connections: Dict[int, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: int):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.user_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket")
    
    def disconnect(self, user_id: int):
        """Remove WebSocket connection"""
        if user_id in self.user_connections:
            del self.user_connections[user_id]
            logger.info(f"User {user_id} disconnected")
    
    async def join_computation_room(self, websocket: WebSocket, computation_id: str, org_id: int):
        """Join a computation room for real-time updates"""
        if computation_id not in self.active_connections:
            self.active_connections[computation_id] = []
        
        self.active_connections[computation_id].append(websocket)
        
        # Notify others
        await self.broadcast_to_computation(
            computation_id,
            {
                "type": "participant_joined",
                "org_id": org_id,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def broadcast_to_computation(self, computation_id: str, message: dict):
        """Send message to all participants in a computation"""
        if computation_id in self.active_connections:
            connections = self.active_connections[computation_id]
            
            # Remove dead connections
            alive_connections = []
            for connection in connections:
                try:
                    await connection.send_json(message)
                    alive_connections.append(connection)
                except:
                    pass
            
            self.active_connections[computation_id] = alive_connections
    
    async def notify_computation_status(self, computation_id: str, status: str):
        """Notify status change"""
        await self.broadcast_to_computation(
            computation_id,
            {
                "type": "status_update",
                "status": status,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def notify_data_submitted(self, computation_id: str, org_id: int, data_count: int):
        """Notify when organization submits data"""
        await self.broadcast_to_computation(
            computation_id,
            {
                "type": "data_submitted",
                "org_id": org_id,
                "data_points_count": data_count,
                "timestamp": datetime.utcnow().isoformat()
            }
        )
    
    async def notify_computation_completed(self, computation_id: str, result: dict):
        """Notify when computation completes"""
        await self.broadcast_to_computation(
            computation_id,
            {
                "type": "computation_completed",
                "result": result,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

# Global instance
smpc_manager = SMPCWebSocketManager()
```

### 10.3 WebSocket Endpoint

```python
# File: backend/main.py
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await smpc_manager.connect(websocket, user_id)
    
    try:
        while True:
            # Receive messages from client
            data = await websocket.receive_json()
            
            message_type = data.get("type")
            
            if message_type == "join_computation":
                computation_id = data.get("computation_id")
                await smpc_manager.join_computation_room(
                    websocket, computation_id, user_id
                )
            
            elif message_type == "leave_computation":
                computation_id = data.get("computation_id")
                await smpc_manager.leave_computation_room(
                    websocket, computation_id, user_id
                )
            
            elif message_type == "ping":
                await websocket.send_json({"type": "pong"})
    
    except WebSocketDisconnect:
        smpc_manager.disconnect(user_id)
```

### 10.4 Frontend WebSocket Client

```javascript
// File: app/hooks/useWebSocket.js
export function useWebSocket(userId) {
    const [ws, setWs] = useState(null);
    const [messages, setMessages] = useState([]);
    
    useEffect(() => {
        // Connect to WebSocket
        const websocket = new WebSocket(`ws://localhost:8000/ws/${userId}`);
        
        websocket.onopen = () => {
            console.log('WebSocket connected');
            setWs(websocket);
        };
        
        websocket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            setMessages(prev => [...prev, message]);
            
            // Handle different message types
            switch(message.type) {
                case 'status_update':
                    handleStatusUpdate(message);
                    break;
                case 'data_submitted':
                    handleDataSubmitted(message);
                    break;
                case 'computation_completed':
                    handleComputationCompleted(message);
                    break;
            }
        };
        
        websocket.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
        
        websocket.onclose = () => {
            console.log('WebSocket disconnected');
            // Auto-reconnect after 3 seconds
            setTimeout(() => {
                setWs(null);
            }, 3000);
        };
        
        return () => {
            websocket.close();
        };
    }, [userId]);
    
    const joinComputation = (computationId) => {
        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: 'join_computation',
                computation_id: computationId
            }));
        }
    };
    
    return { ws, messages, joinComputation };
}
```

---

Continue to INTERVIEW_PART4 for Testing, Deployment, and Interview Q&A.
