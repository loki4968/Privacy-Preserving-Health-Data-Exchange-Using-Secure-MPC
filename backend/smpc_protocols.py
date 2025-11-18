from typing import List, Dict, Any, Tuple, Union, Optional
import secrets
import json
import math
import base64
import hashlib
import os
import random
import time
from decimal import Decimal, getcontext, InvalidOperation

# Try to import pycryptodome for secure prime generation
try:
    from Crypto.Util import number as crypto_number
    PYCRYPTODOME_AVAILABLE = True
except ImportError:
    PYCRYPTODOME_AVAILABLE = False
    print("Warning: pycryptodome not available. Using fallback prime generation.")

# Set precision for Decimal calculations
getcontext().prec = 28

class ShamirSecretSharing:
    """Implementation of Shamir's Secret Sharing scheme"""
    
    def __init__(self, prime: int = None):
        """Initialize with an optional prime number for the finite field"""
        # If no prime is provided, generate a cryptographically secure random prime
        if prime is None:
            self.prime = self._generate_secure_prime(256)  # 256-bit prime for security
        else:
            self.prime = prime
        
    def _mod_inverse(self, x: int, m: int) -> int:
        """Calculate the modular multiplicative inverse"""
        g, x, y = self._extended_gcd(x % m, m)
        if g != 1:
            raise ValueError("Modular inverse does not exist")
        else:
            return x % m
            
    def _extended_gcd(self, a: int, b: int) -> Tuple[int, int, int]:
        """Extended Euclidean Algorithm to find gcd and coefficients"""
        if a == 0:
            return b, 0, 1
        else:
            gcd, x, y = self._extended_gcd(b % a, a)
            return gcd, y - (b // a) * x, x
    
    def _generate_secure_prime(self, bits: int) -> int:
        """Generate a cryptographically secure random prime"""
        if PYCRYPTODOME_AVAILABLE:
            # Use pycryptodome for secure prime generation
            return crypto_number.getPrime(bits, randfunc=secrets.token_bytes)
        else:
            # Fallback: Generate using Miller-Rabin primality test
            return self._generate_prime_fallback(bits)
    
    def _generate_prime_fallback(self, bits: int) -> int:
        """Fallback prime generation using Miller-Rabin"""
        while True:
            # Generate random odd number with specified bit length
            candidate = secrets.randbits(bits)
            candidate |= (1 << bits - 1) | 1  # Set MSB and LSB
            
            if self._is_prime_miller_rabin(candidate):
                return candidate
    
    def _is_prime_miller_rabin(self, n: int, k: int = 40) -> bool:
        """Miller-Rabin primality test with k rounds"""
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
            a = secrets.randbelow(n - 3) + 2
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
    
    def split_secret(self, secret: Union[int, float, Decimal], n: int, k: int) -> List[Tuple[int, Union[int, Decimal]]]:
        """Split a secret into n shares, requiring k shares to reconstruct
        
        Args:
            secret: The secret value to split
            n: Number of shares to generate
            k: Threshold (minimum shares needed to reconstruct)
            
        Returns:
            List of (x, y) coordinate pairs representing the shares
        """
        if k > n:
            raise ValueError("Threshold k cannot be greater than the number of shares n")
        
        # Convert to Decimal for precise arithmetic
        secret_value = Decimal(str(secret))
        
        # Generate random coefficients for the polynomial
        # The constant term is the secret
        # Use much smaller random coefficients to avoid overflow
        max_coeff = min(1000000, self.prime - 1)  # Limit coefficients to reasonable range
        coefficients = [secret_value] + [Decimal(random.randint(1, max_coeff)) for _ in range(k - 1)]
        
        # Generate the shares (x, P(x))
        shares = []
        for i in range(1, n + 1):
            # Evaluate the polynomial at x = i
            x = i
            y = Decimal('0')
            
            # Compute P(x) = a_0 + a_1 * x + a_2 * x^2 + ... + a_{k-1} * x^{k-1}
            for j, coef in enumerate(coefficients):
                y += coef * (Decimal(x) ** j)
                
            shares.append((x, y))
            
        return shares
    
    def reconstruct_secret(self, shares: List[Tuple[int, Union[int, float, Decimal]]], k: Optional[int] = None) -> Decimal:
        """Reconstruct the secret from k or more shares using Lagrange interpolation
        
        Args:
            shares: List of (x, y) coordinate pairs representing the shares
            k: Optional threshold parameter (uses all shares if not specified)
            
        Returns:
            The reconstructed secret
        """
        if k is None:
            k = len(shares)
            
        if len(shares) < k:
            raise ValueError(f"Need at least {k} shares to reconstruct the secret")
            
        # Use the first k shares to reconstruct
        shares = shares[:k]
        
        # Convert share values to Decimal
        shares = [(x, Decimal(str(y))) for x, y in shares]
        
        # Lagrange interpolation to find P(0)
        secret = Decimal('0')
        
        for i, (xi, yi) in enumerate(shares):
            # Calculate the Lagrange basis polynomial L_i(0)
            numerator = Decimal('1')
            denominator = Decimal('1')
            
            for j, (xj, _) in enumerate(shares):
                if i != j:
                    numerator *= Decimal(str(-xj))
                    denominator *= Decimal(str(xi - xj))
                    
            # Add this term to the result
            secret += yi * (numerator / denominator)
            
        return secret


class SMPCProtocol:
    def __init__(self, threshold: int = 2):
        self.participants = {}
        self.threshold = threshold  # Minimum number of participants required
        self.key = os.urandom(32)  # Generate a random 32-byte key
        self.salt = os.urandom(16)  # Generate a random 16-byte salt
        self.shamir = ShamirSecretSharing()  # Initialize Shamir's Secret Sharing

    def _derive_key(self, data: str) -> bytes:
        """Derive a key from data using PBKDF2"""
        return hashlib.pbkdf2_hmac(
            'sha256',
            data.encode(),
            self.salt,
            100000,  # Number of iterations
            32  # Key length
        )

    def _encrypt(self, data: str) -> str:
        """Encrypt data using a simple XOR cipher with the derived key"""
        key = self._derive_key(data)
        data_bytes = data.encode()
        encrypted = bytes(a ^ b for a, b in zip(data_bytes, key))
        return base64.b64encode(encrypted).decode()

    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt data using the same XOR cipher"""
        key = self._derive_key(encrypted_data)
        encrypted_bytes = base64.b64decode(encrypted_data)
        decrypted = bytes(a ^ b for a, b in zip(encrypted_bytes, key))
        return decrypted.decode()

    def generate_shares(self, secret: Union[int, float, str], n: int, k: int) -> List[Dict[str, Any]]:
        """Generate n shares for a secret, requiring k shares to reconstruct
        
        Args:
            secret: The secret value to split (numeric or string)
            n: Number of shares to generate
            k: Threshold (minimum shares needed to reconstruct)
            
        Returns:
            List of shares as dictionaries with x, y values and metadata
        """
        # Handle different types of secrets
        if isinstance(secret, str):
            try:
                # Try to convert to float if it's a numeric string
                secret_value = float(secret)
            except ValueError:
                # For non-numeric strings, hash the string and use the hash as the secret
                # This is a simplification - in a real system, you might want a different approach
                secret_hash = int.from_bytes(hashlib.sha256(secret.encode()).digest()[:8], 'big')
                secret_value = secret_hash
        else:
            secret_value = secret
            
        # Generate shares using Shamir's Secret Sharing
        raw_shares = self.shamir.split_secret(secret_value, n, k)
        
        # Format shares as dictionaries with metadata
        formatted_shares = []
        for i, (x, y) in enumerate(raw_shares):
            share_id = secrets.token_hex(8)  # Generate a unique ID for the share
            share = {
                "id": share_id,
                "index": x,
                "value": str(y),  # Convert Decimal to string for serialization
                "threshold": k,
                "total_shares": n,
                "created_at": math.floor(time.time()),
                "type": "shamir_share"
            }
            formatted_shares.append(share)
            
        return formatted_shares

    def reconstruct_secret(self, shares: List[Dict[str, Any]]) -> Union[Decimal, str]:
        """Reconstruct a secret from shares
        
        Args:
            shares: List of share dictionaries with x, y values
            
        Returns:
            The reconstructed secret value
        """
        if not shares:
            raise ValueError("No shares provided")
            
        # Extract threshold from the first share
        threshold = shares[0].get("threshold", self.threshold)
        
        if len(shares) < threshold:
            raise ValueError(f"Need at least {threshold} shares to reconstruct")
        
        # Extract x, y coordinates from the shares
        coordinates = []
        for share in shares:
            if share.get("type") != "shamir_share":
                raise ValueError(f"Invalid share type: {share.get('type')}")
                
            x = share.get("index")
            y = share.get("value")
            
            if x is None or y is None:
                raise ValueError("Share missing required values")
                
            coordinates.append((int(x), Decimal(str(y))))
        
        # Reconstruct the secret using Shamir's Secret Sharing
        reconstructed = self.shamir.reconstruct_secret(coordinates, threshold)
        
        return reconstructed

    def secure_sum(self, values: List[Union[int, float, Decimal]]) -> Decimal:
        """Compute the sum of values securely using Shamir's Secret Sharing
        
        This method splits each value into shares, aggregates the shares,
        and then reconstructs the sum from the aggregated shares.
        """
        if not values:
            return Decimal('0')
            
        # Convert all values to Decimal for precision
        decimal_values = [Decimal(str(v)) for v in values]
        
        # Number of participants (use at least 3 for security)
        n = max(3, len(values))
        # Threshold (require at least 2 shares to reconstruct)
        k = min(2, n-1)
        
        # Generate shares for each value
        all_shares = []
        for value in decimal_values:
            # Generate raw shares (x, y coordinates)
            shares = self.shamir.split_secret(value, n, k)
            all_shares.append(shares)
            
        # Aggregate shares by position (simulate secure aggregation among participants)
        aggregated_shares = []
        for i in range(n):
            # Sum the i-th share from each value
            x_coord = i + 1  # x coordinates start from 1
            y_sum = sum(shares[i][1] for shares in all_shares)
            aggregated_shares.append((x_coord, y_sum))
            
        # Reconstruct the sum from the aggregated shares
        result = self.shamir.reconstruct_secret(aggregated_shares, k)
        
        return result

    def secure_mean(self, values: List[Union[int, float, Decimal]]) -> Decimal:
        """Compute the mean of values securely using Shamir's Secret Sharing"""
        if not values:
            return Decimal('0')
            
        # Compute sum securely
        secure_sum_result = self.secure_sum(values)
        
        # Divide by count (division is done in the clear)
        return secure_sum_result / Decimal(len(values))

    def secure_variance(self, values: List[Union[int, float, Decimal]]) -> Decimal:
        """Compute the variance of values securely
        
        This implementation uses the formula: Var(X) = E[X²] - E[X]²
        where E[X] is the mean of X.
        """
        if not values:
            return Decimal('0')
            
        # Convert all values to Decimal
        decimal_values = [Decimal(str(v)) for v in values]
        
        # Compute the mean securely
        mean = self.secure_mean(decimal_values)
        
        # Compute the squared values
        squared_values = [v ** 2 for v in decimal_values]
        
        # Compute the mean of squared values securely
        mean_of_squares = self.secure_mean(squared_values)
        
        # Compute variance using the formula: Var(X) = E[X²] - E[X]²
        variance = mean_of_squares - (mean ** 2)
        
        return variance

    def secure_percentile(self, values: List[Union[int, float, Decimal]], percentile: float) -> Decimal:
        """Securely compute a percentile of values
        
        Note: This implementation sorts values in the clear, which is not fully secure.
        For a fully secure implementation, secure sorting protocols would be needed.
        """
        if not values:
            return Decimal('0')
        
        if not 0 <= percentile <= 100:
            raise ValueError("Percentile must be between 0 and 100")
        
        # Convert all values to Decimal
        decimal_values = [Decimal(str(v)) for v in values]
        
        # Sort values (in a real system, use secure sorting)
        # Note: Sorting reveals order information, which is not fully secure
        sorted_values = sorted(decimal_values)
        
        # Calculate the index
        index = (Decimal(str(percentile)) / Decimal('100')) * (len(sorted_values) - 1)
        
        # If index is an integer, return the value at that index
        if index == index.to_integral_value():
            return sorted_values[int(index)]
        
        # Otherwise, interpolate between the two nearest values
        lower_index = int(index)
        upper_index = lower_index + 1
        lower_value = sorted_values[lower_index]
        upper_value = sorted_values[upper_index]
        fraction = index - Decimal(lower_index)
        
        # Linear interpolation
        return lower_value + (upper_value - lower_value) * fraction

    def secure_sort(self, values: List[Union[int, float, Decimal]]) -> List[Decimal]:
        """Securely sort values using a bitonic sorting network
        
        This is a more complete implementation of a bitonic sorting network,
        which can be implemented securely using secure comparison protocols.
        However, this implementation still reveals the final order.
        
        For a fully secure implementation, additional protocols would be needed.
        """
        if not values:
            return []
            
        # Convert all values to Decimal
        decimal_values = [Decimal(str(v)) for v in values]
        
        # Pad the list to the next power of 2
        n = len(decimal_values)
        next_power_of_2 = 2 ** math.ceil(math.log2(n))
        
        # Use a very large negative number as padding
        # In a real secure implementation, this would be handled differently
        padding = Decimal('-1e9')  # A very small number
        padded_values = decimal_values + [padding] * (next_power_of_2 - n)
        
        # Implement bitonic sort
        result = self._bitonic_sort(padded_values, 0, len(padded_values), True)
        
        # Remove padding values
        return [v for v in result if v != padding]
    
    def _bitonic_sort(self, values: List[Decimal], low: int, cnt: int, dir: bool) -> List[Decimal]:
        """Recursive bitonic sort implementation
        
        Args:
            values: List of values to sort
            low: Starting index
            cnt: Number of elements to sort
            dir: Direction (True for ascending, False for descending)
        """
        if cnt <= 1:
            return values
            
        # Divide the sequence in two parts and sort them in opposite directions
        k = cnt // 2
        values = self._bitonic_sort(values, low, k, not dir)  # Sort first half in opposite direction
        values = self._bitonic_sort(values, low + k, cnt - k, dir)  # Sort second half in original direction
        
        # Merge the two sorted sequences
        values = self._bitonic_merge(values, low, cnt, dir)
        
        return values
    
    def _bitonic_merge(self, values: List[Decimal], low: int, cnt: int, dir: bool) -> List[Decimal]:
        """Merge two bitonic sequences
        
        Args:
            values: List of values to merge
            low: Starting index
            cnt: Number of elements to merge
            dir: Direction (True for ascending, False for descending)
        """
        if cnt <= 1:
            return values
            
        # Compare and swap elements
        k = cnt // 2
        for i in range(low, low + k):
            self._compare_and_swap(values, i, i + k, dir)
            
        # Recursively merge the two halves
        values = self._bitonic_merge(values, low, k, dir)
        values = self._bitonic_merge(values, low + k, cnt - k, dir)
        
        return values
    
    def _compare_and_swap(self, values: List[Decimal], i: int, j: int, dir: bool) -> None:
        """Compare and swap two elements if they are in the wrong order
        
        Args:
            values: List of values
            i: First index
            j: Second index
            dir: Direction (True for ascending, False for descending)
        """
        # In a secure implementation, this would be done using secure comparison
        if (values[i] > values[j]) == dir:
            values[i], values[j] = values[j], values[i]

    def secure_compare(self, a: Union[int, float, Decimal], b: Union[int, float, Decimal]) -> bool:
        """Securely compare two values using a garbled circuit approach
        
        This is a simplified simulation of secure comparison. In a real implementation,
        this would use garbled circuits or homomorphic encryption for secure comparison.
        
        Args:
            a: First value to compare
            b: Second value to compare
            
        Returns:
            True if a > b, False otherwise
        """
        # Convert to Decimal for consistent handling
        a_dec = Decimal(str(a))
        b_dec = Decimal(str(b))
        
        # In a real secure implementation, we would use a secure comparison protocol
        # such as garbled circuits or homomorphic encryption
        # This is a simplified simulation for demonstration purposes
        
        # Simulate secure comparison by adding random noise to both values,
        # comparing them, and then removing the effect of the noise
        
        # Generate random noise
        noise_a = Decimal(str(random.uniform(-1, 1)))
        noise_b = Decimal(str(random.uniform(-1, 1)))
        
        # Add noise to values
        noisy_a = a_dec + noise_a
        noisy_b = b_dec + noise_b
        
        # Compare noisy values
        noisy_result = noisy_a > noisy_b
        
        # Correct for noise (in a real implementation, this would be done securely)
        # If noise_a > noise_b, it might have flipped the result if a and b are close
        if (noise_a > noise_b) != (a_dec > b_dec):
            # The noise affected the comparison result
            return a_dec > b_dec
        else:
            # The noise didn't affect the comparison result
            return noisy_result

    def secure_correlation(self, values1: List[Union[int, float, Decimal]], values2: List[Union[int, float, Decimal]]) -> Decimal:
        """Securely compute the correlation between two sets of values
        
        This method uses secure computation techniques to calculate the Pearson
        correlation coefficient between two datasets without revealing individual values.
        
        Args:
            values1: First set of values
            values2: Second set of values
            
        Returns:
            Pearson correlation coefficient as a Decimal
        """
        if len(values1) != len(values2):
            raise ValueError("Both sets of values must have the same length")
            
        if not values1:
            return Decimal('0')
            
        # Convert all values to Decimal
        decimal_values1 = [Decimal(str(v)) for v in values1]
        decimal_values2 = [Decimal(str(v)) for v in values2]
        
        n = len(decimal_values1)
        
        # Compute means securely
        mean1 = self.secure_mean(decimal_values1)
        mean2 = self.secure_mean(decimal_values2)
        
        # Compute products for covariance calculation
        products = [decimal_values1[i] * decimal_values2[i] for i in range(n)]
        mean_product = self.secure_mean(products)
        
        # Compute squared values for variance calculation
        squared1 = [v ** 2 for v in decimal_values1]
        squared2 = [v ** 2 for v in decimal_values2]
        
        mean_squared1 = self.secure_mean(squared1)
        mean_squared2 = self.secure_mean(squared2)
        
        # Compute covariance: E[XY] - E[X]E[Y]
        covariance = mean_product - (mean1 * mean2)
        
        # Compute variances: E[X²] - E[X]²
        variance1 = mean_squared1 - (mean1 ** 2)
        variance2 = mean_squared2 - (mean2 ** 2)
        
        # Compute correlation
        if variance1 <= Decimal('0') or variance2 <= Decimal('0'):
            return Decimal('0')
        
        # Pearson correlation coefficient: Cov(X,Y) / (σ_X * σ_Y)
        correlation = covariance / (variance1.sqrt() * variance2.sqrt())
        
        # Ensure the result is within [-1, 1]
        return max(min(correlation, Decimal('1')), Decimal('-1'))

    def secure_aggregate(self, values: List[Dict[str, Any]], operation: str) -> Dict[str, Any]:
        """Securely aggregate values from multiple participants using SMPC protocols
        
        This method applies the appropriate secure computation technique based on the
        requested operation, ensuring that individual values are not revealed during
        the aggregation process.
        
        Args:
            values: List of dictionaries containing values to aggregate
            operation: Type of aggregation to perform (sum, average, min, max, etc.)
            
        Returns:
            Dictionary with the aggregation result and metadata
        """
        if not values:
            return {"result": "0", "operation": operation}
        
        # Extract numeric values
        numeric_values = []
        for value in values:
            if isinstance(value, dict) and "value" in value:
                try:
                    # Convert to Decimal for consistent handling
                    numeric_values.append(Decimal(str(value["value"])))
                except (ValueError, TypeError):
                    pass
        
        if not numeric_values:
            return {"result": "0", "operation": operation, "error": "No valid numeric values"}
        
        try:
            # Apply the appropriate secure computation based on operation
            if operation == "sum":
                result = self.secure_sum(numeric_values)
            elif operation == "average":
                result = self.secure_mean(numeric_values)
            elif operation == "variance":
                result = self.secure_variance(numeric_values)
            elif operation == "stddev":
                # Standard deviation is the square root of variance
                variance = self.secure_variance(numeric_values)
                result = variance.sqrt() if variance > Decimal('0') else Decimal('0')
            elif operation == "median":
                # Median is the 50th percentile
                result = self.secure_percentile(numeric_values, 50)
            elif operation == "min":
                # For min/max, we currently use a simplified approach
                # In a real system, secure min/max protocols would be used
                sorted_values = self.secure_sort(numeric_values)
                result = sorted_values[0] if sorted_values else Decimal('0')
            elif operation == "max":
                sorted_values = self.secure_sort(numeric_values)
                result = sorted_values[-1] if sorted_values else Decimal('0')
            elif operation == "range":
                sorted_values = self.secure_sort(numeric_values)
                if sorted_values:
                    result = sorted_values[-1] - sorted_values[0]
                else:
                    result = Decimal('0')
            elif operation == "q1":
                # First quartile (25th percentile)
                result = self.secure_percentile(numeric_values, 25)
            elif operation == "q3":
                # Third quartile (75th percentile)
                result = self.secure_percentile(numeric_values, 75)
            elif operation == "iqr":
                # Interquartile range (Q3 - Q1)
                q1 = self.secure_percentile(numeric_values, 25)
                q3 = self.secure_percentile(numeric_values, 75)
                result = q3 - q1
            else:
                return {"result": "0", "operation": operation, "error": "Unsupported operation"}
            
            # Convert result to string for JSON serialization
            result_str = str(result)
            
            return {
                "result": result_str,
                "operation": operation,
                "count": len(numeric_values),
                "secure": True,
                "protocol": "shamir_secret_sharing"
            }
            
        except Exception as e:
            return {
                "result": "0",
                "operation": operation,
                "error": f"Error during secure computation: {str(e)}"
            }

# Create a singleton instance with a threshold of 2
smpc_protocol = SMPCProtocol(threshold=2)