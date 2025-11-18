"""
Enhanced Homomorphic Encryption Implementation for Health Data Exchange
Provides real homomorphic encryption capabilities using Paillier cryptosystem
"""

import random
import math
from typing import List, Tuple, Union, Dict, Any
import json
import hashlib
import hmac
import secrets
try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.backends import default_backend
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    print("Warning: cryptography not available for enhanced homomorphic encryption")
import os


class PaillierKeyPair:
    """Paillier public-private key pair for homomorphic encryption."""
    
    def __init__(self, public_key: 'PaillierPublicKey', private_key: 'PaillierPrivateKey'):
        self.public_key = public_key
        self.private_key = private_key


class PaillierPublicKey:
    """Paillier public key for encryption and homomorphic operations."""
    
    def __init__(self, n: int, g: int = None):
        self.n = n
        self.n_squared = n * n
        self.g = g if g is not None else n + 1
        
    def encrypt(self, plaintext: int) -> 'PaillierCiphertext':
        """Encrypt a plaintext integer using Paillier encryption."""
        if plaintext < 0:
            # Handle negative numbers by adding n
            plaintext = plaintext % self.n
            
        # Generate random r
        r = self._generate_random_r()
        
        # Calculate ciphertext: c = g^m * r^n mod n^2
        gm = pow(self.g, plaintext, self.n_squared)
        rn = pow(r, self.n, self.n_squared)
        ciphertext = (gm * rn) % self.n_squared
        
        return PaillierCiphertext(ciphertext, self)
    
    def _generate_random_r(self) -> int:
        """Generate a random number r coprime to n."""
        while True:
            r = random.randrange(1, self.n)
            if math.gcd(r, self.n) == 1:
                return r
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert public key to dictionary for serialization."""
        return {
            'n': self.n,
            'g': self.g
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaillierPublicKey':
        """Create public key from dictionary."""
        return cls(data['n'], data['g'])


class PaillierPrivateKey:
    """Paillier private key for decryption."""
    
    def __init__(self, lambda_val: int, mu: int, public_key: PaillierPublicKey):
        self.lambda_val = lambda_val
        self.mu = mu
        self.public_key = public_key
    
    def decrypt(self, ciphertext: 'PaillierCiphertext') -> int:
        """Decrypt a Paillier ciphertext."""
        n = self.public_key.n
        n_squared = self.public_key.n_squared
        
        # Calculate u = (c^λ mod n^2 - 1) / n
        c_lambda = pow(ciphertext.value, self.lambda_val, n_squared)
        u = (c_lambda - 1) // n
        
        # Calculate plaintext = u * μ mod n
        plaintext = (u * self.mu) % n
        
        # Handle negative numbers
        if plaintext > n // 2:
            plaintext = plaintext - n
            
        return plaintext


class PaillierCiphertext:
    """Encrypted value using Paillier homomorphic encryption."""
    
    def __init__(self, value: int, public_key: PaillierPublicKey):
        self.value = value
        self.public_key = public_key
        self.integrity_tag = None  # HMAC tag for integrity verification
    
    def __add__(self, other: Union['PaillierCiphertext', int]) -> 'PaillierCiphertext':
        """Homomorphic addition of two ciphertexts or ciphertext and plaintext."""
        if isinstance(other, PaillierCiphertext):
            # Ciphertext + Ciphertext: c1 * c2 mod n^2
            result = (self.value * other.value) % self.public_key.n_squared
        else:
            # Ciphertext + Plaintext: c * g^m mod n^2
            gm = pow(self.public_key.g, other, self.public_key.n_squared)
            result = (self.value * gm) % self.public_key.n_squared
        
        return PaillierCiphertext(result, self.public_key)
    
    def __mul__(self, scalar: int) -> 'PaillierCiphertext':
        """Homomorphic multiplication by a scalar: c^k mod n^2."""
        result = pow(self.value, scalar, self.public_key.n_squared)
        return PaillierCiphertext(result, self.public_key)
    
    def __rmul__(self, scalar: int) -> 'PaillierCiphertext':
        """Right multiplication by scalar."""
        return self.__mul__(scalar)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ciphertext to dictionary for serialization."""
        return {
            'value': self.value,
            'public_key': self.public_key.to_dict()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PaillierCiphertext':
        """Create ciphertext from dictionary."""
        public_key = PaillierPublicKey.from_dict(data['public_key'])
        return cls(data['value'], public_key)


class EnhancedHomomorphicEncryption:
    """Enhanced homomorphic encryption service with real Paillier implementation."""
    
    def __init__(self, key_size: int = 3072):
        # Use minimum 3072-bit keys for production (NIST recommendation post-2030)
        if key_size < 3072:
            print(f"Warning: key_size {key_size} is below NIST recommendation. Using 3072 bits.")
            key_size = 3072
        self.key_size = key_size
        self._key_pair = None
        # Generate HMAC key for ciphertext integrity
        self.hmac_key = secrets.token_bytes(32)
    
    def generate_keypair(self) -> PaillierKeyPair:
        """Generate a new Paillier key pair."""
        # Generate two large primes p and q
        p = self._generate_prime(self.key_size // 2)
        q = self._generate_prime(self.key_size // 2)
        
        # Ensure p != q
        while p == q:
            q = self._generate_prime(self.key_size // 2)
        
        # Calculate n = p * q
        n = p * q
        
        # Calculate λ = lcm(p-1, q-1)
        lambda_val = self._lcm(p - 1, q - 1)
        
        # Create public key
        public_key = PaillierPublicKey(n)
        
        # Calculate μ = (L(g^λ mod n^2))^(-1) mod n
        # where L(x) = (x-1)/n
        g_lambda = pow(public_key.g, lambda_val, public_key.n_squared)
        l_value = (g_lambda - 1) // n
        mu = self._mod_inverse(l_value, n)
        
        # Create private key
        private_key = PaillierPrivateKey(lambda_val, mu, public_key)
        
        self._key_pair = PaillierKeyPair(public_key, private_key)
        return self._key_pair
    
    def get_public_key(self) -> PaillierPublicKey:
        """Get the current public key."""
        if self._key_pair is None:
            self.generate_keypair()
        return self._key_pair.public_key
    
    def get_private_key(self) -> PaillierPrivateKey:
        """Get the current private key."""
        if self._key_pair is None:
            self.generate_keypair()
        return self._key_pair.private_key
    
    def encrypt(self, plaintext: Union[int, float], public_key: PaillierPublicKey = None) -> PaillierCiphertext:
        """Encrypt a value using Paillier encryption with integrity check."""
        if public_key is None:
            public_key = self.get_public_key()
        
        # Convert float to integer by scaling
        if isinstance(plaintext, float):
            plaintext = int(plaintext * 1000)  # Scale by 1000 for precision
        
        ciphertext = public_key.encrypt(plaintext)
        # Add HMAC for ciphertext integrity verification
        ciphertext.integrity_tag = self._generate_integrity_tag(ciphertext.value)
        return ciphertext
    
    def decrypt(self, ciphertext: PaillierCiphertext, private_key: PaillierPrivateKey = None) -> float:
        """Decrypt a Paillier ciphertext with integrity verification."""
        if private_key is None:
            private_key = self.get_private_key()
        
        # Verify ciphertext integrity if tag exists
        if hasattr(ciphertext, 'integrity_tag') and ciphertext.integrity_tag:
            if not self._verify_integrity_tag(ciphertext.value, ciphertext.integrity_tag):
                raise ValueError("Ciphertext integrity check failed - possible tampering detected")
        
        plaintext = private_key.decrypt(ciphertext)
        
        # Convert back from scaled integer to float
        return plaintext / 1000.0
    
    def homomorphic_add(self, encrypted_a: PaillierCiphertext, encrypted_b: PaillierCiphertext) -> PaillierCiphertext:
        """Perform homomorphic addition of two encrypted values."""
        return encrypted_a + encrypted_b
    
    def homomorphic_multiply_const(self, encrypted_value: PaillierCiphertext, constant: Union[int, float]) -> PaillierCiphertext:
        """Multiply encrypted value by a constant."""
        if isinstance(constant, float):
            constant = int(constant * 1000)  # Scale for precision
        
        return encrypted_value * constant
    
    def secure_sum(self, encrypted_values: List[PaillierCiphertext]) -> PaillierCiphertext:
        """Calculate the sum of encrypted values homomorphically."""
        if not encrypted_values:
            raise ValueError("Cannot sum empty list")
        
        result = encrypted_values[0]
        for encrypted_val in encrypted_values[1:]:
            result = result + encrypted_val
        
        return result
    
    def secure_mean(self, encrypted_values: List[PaillierCiphertext]) -> PaillierCiphertext:
        """Calculate the mean of encrypted values homomorphically."""
        if not encrypted_values:
            raise ValueError("Cannot calculate mean of empty list")
        
        total = self.secure_sum(encrypted_values)
        count = len(encrypted_values)
        
        # Divide by count (multiply by 1/count)
        # Note: Division is not directly supported in Paillier, so we approximate
        return total * (1.0 / count)
    
    def _generate_prime(self, bits: int) -> int:
        """Generate a prime number with specified bit length."""
        while True:
            # Generate random odd number
            candidate = random.getrandbits(bits)
            candidate |= (1 << bits - 1) | 1  # Set MSB and LSB
            
            if self._is_prime(candidate):
                return candidate
    
    def _is_prime(self, n: int, k: int = 10) -> bool:
        """Miller-Rabin primality test."""
        if n < 2:
            return False
        if n == 2 or n == 3:
            return True
        if n % 2 == 0:
            return False
        
        # Write n-1 as d * 2^r
        r = 0
        d = n - 1
        while d % 2 == 0:
            r += 1
            d //= 2
        
        # Perform k rounds of testing
        for _ in range(k):
            a = random.randrange(2, n - 1)
            x = pow(a, d, n)
            
            if x == 1 or x == n - 1:
                continue
            
            for _ in range(r - 1):
                x = pow(x, 2, n)
                if x == n - 1:
                    break
            else:
                return False
        
        return True
    
    def _lcm(self, a: int, b: int) -> int:
        """Calculate least common multiple."""
        return abs(a * b) // math.gcd(a, b)
    
    def _mod_inverse(self, a: int, m: int) -> int:
        """Calculate modular multiplicative inverse using extended Euclidean algorithm."""
        if math.gcd(a, m) != 1:
            raise ValueError("Modular inverse does not exist")
        
        def extended_gcd(a, b):
            if a == 0:
                return b, 0, 1
            gcd, x1, y1 = extended_gcd(b % a, a)
            x = y1 - (b // a) * x1
            y = x1
            return gcd, x, y
        
        _, x, _ = extended_gcd(a, m)
        return (x % m + m) % m
    
    def _generate_integrity_tag(self, ciphertext_value: int) -> bytes:
        """Generate HMAC integrity tag for ciphertext."""
        message = str(ciphertext_value).encode('utf-8')
        return hmac.new(self.hmac_key, message, hashlib.sha256).digest()
    
    def _verify_integrity_tag(self, ciphertext_value: int, tag: bytes) -> bool:
        """Verify HMAC integrity tag for ciphertext."""
        expected_tag = self._generate_integrity_tag(ciphertext_value)
        return hmac.compare_digest(expected_tag, tag)


class SecureHealthMetrics:
    """Secure computation of health metrics using homomorphic encryption."""
    
    def __init__(self, encryption_service: EnhancedHomomorphicEncryption):
        self.encryption = encryption_service
    
    def encrypt_health_data(self, health_data: Dict[str, List[float]]) -> Dict[str, List[PaillierCiphertext]]:
        """Encrypt health data for secure computation."""
        encrypted_data = {}
        public_key = self.encryption.get_public_key()
        
        for metric, values in health_data.items():
            encrypted_values = []
            for value in values:
                encrypted_value = self.encryption.encrypt(value, public_key)
                encrypted_values.append(encrypted_value)
            encrypted_data[metric] = encrypted_values
        
        return encrypted_data
    
    def secure_statistics(self, encrypted_data: Dict[str, List[PaillierCiphertext]]) -> Dict[str, Dict[str, float]]:
        """Calculate statistics on encrypted health data."""
        results = {}
        private_key = self.encryption.get_private_key()
        
        for metric, encrypted_values in encrypted_data.items():
            if not encrypted_values:
                continue
            
            # Calculate secure sum
            encrypted_sum = self.encryption.secure_sum(encrypted_values)
            total = self.encryption.decrypt(encrypted_sum, private_key)
            
            # Calculate mean
            mean = total / len(encrypted_values)
            
            # For variance, we need to decrypt individual values (limitation of current implementation)
            decrypted_values = [self.encryption.decrypt(val, private_key) for val in encrypted_values]
            variance = sum((x - mean) ** 2 for x in decrypted_values) / len(decrypted_values)
            std_dev = math.sqrt(variance)
            
            results[metric] = {
                'count': len(encrypted_values),
                'sum': total,
                'mean': mean,
                'variance': variance,
                'std_dev': std_dev,
                'min': min(decrypted_values),
                'max': max(decrypted_values)
            }
        
        return results
    
    def secure_correlation(self, encrypted_x: List[PaillierCiphertext], 
                          encrypted_y: List[PaillierCiphertext]) -> float:
        """Calculate correlation between two encrypted datasets."""
        if len(encrypted_x) != len(encrypted_y):
            raise ValueError("Datasets must have the same length")
        
        private_key = self.encryption.get_private_key()
        
        # Decrypt values for correlation calculation
        # Note: In a real implementation, this would use secure multiparty computation
        x_values = [self.encryption.decrypt(val, private_key) for val in encrypted_x]
        y_values = [self.encryption.decrypt(val, private_key) for val in encrypted_y]
        
        n = len(x_values)
        mean_x = sum(x_values) / n
        mean_y = sum(y_values) / n
        
        numerator = sum((x_values[i] - mean_x) * (y_values[i] - mean_y) for i in range(n))
        denominator_x = sum((x - mean_x) ** 2 for x in x_values)
        denominator_y = sum((y - mean_y) ** 2 for y in y_values)
        
        if denominator_x == 0 or denominator_y == 0:
            return 0.0
        
        correlation = numerator / math.sqrt(denominator_x * denominator_y)
        return correlation


# Example usage and testing
if __name__ == "__main__":
    # Initialize enhanced homomorphic encryption
    he = EnhancedHomomorphicEncryption(key_size=1024)  # Smaller key for testing
    keypair = he.generate_keypair()
    
    # Test basic encryption/decryption
    plaintext = 42.5
    encrypted = he.encrypt(plaintext)
    decrypted = he.decrypt(encrypted)
    print(f"Original: {plaintext}, Decrypted: {decrypted}")
    
    # Test homomorphic operations
    a = he.encrypt(10.0)
    b = he.encrypt(20.0)
    
    # Homomorphic addition
    encrypted_sum = he.homomorphic_add(a, b)
    decrypted_sum = he.decrypt(encrypted_sum)
    print(f"Homomorphic sum: {decrypted_sum} (expected: 30.0)")
    
    # Test secure health metrics
    health_metrics = SecureHealthMetrics(he)
    
    sample_data = {
        'blood_pressure': [120.0, 130.0, 125.0, 135.0],
        'heart_rate': [70.0, 75.0, 72.0, 78.0]
    }
    
    encrypted_health_data = health_metrics.encrypt_health_data(sample_data)
    statistics = health_metrics.secure_statistics(encrypted_health_data)
    
    print("Secure Health Statistics:")
    for metric, stats in statistics.items():
        print(f"{metric}: mean={stats['mean']:.2f}, std_dev={stats['std_dev']:.2f}")
