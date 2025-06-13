import hmac
import hashlib
import json
import time
from typing import Dict, Optional, Tuple
from datetime import datetime

class SignatureManager:
    def __init__(self, secret_key: str):
        """
        Initialize the signature manager.
        
        Args:
            secret_key: Secret key for HMAC signing
        """
        self.secret_key = secret_key.encode()
        
    def generate_signature(self, data: Dict, timestamp: Optional[int] = None) -> Tuple[str, int]:
        """
        Generate HMAC signature for request data.
        
        Args:
            data: Request data to sign
            timestamp: Optional timestamp (will generate if not provided)
            
        Returns:
            Tuple of (signature, timestamp)
        """
        try:
            # Generate timestamp if not provided
            if timestamp is None:
                timestamp = int(time.time())
            
            # Add timestamp to data
            data_with_timestamp = data.copy()
            data_with_timestamp['timestamp'] = timestamp
            
            # Sort data keys for consistent signing
            sorted_data = dict(sorted(data_with_timestamp.items()))
            
            # Convert data to JSON string
            data_string = json.dumps(sorted_data, separators=(',', ':'))
            
            # Generate HMAC signature
            signature = hmac.new(
                self.secret_key,
                data_string.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return signature, timestamp
            
        except Exception as e:
            raise Exception(f"Error generating signature: {str(e)}")
    
    def verify_signature(self, data: Dict, signature: str, timestamp: int, max_age: int = 300) -> bool:
        """
        Verify HMAC signature for request data.
        
        Args:
            data: Request data to verify
            signature: Signature to verify against
            timestamp: Timestamp from request
            max_age: Maximum age of request in seconds (default: 5 minutes)
            
        Returns:
            True if signature is valid, False otherwise
        """
        try:
            # Check if request is too old
            current_time = int(time.time())
            if current_time - timestamp > max_age:
                return False
            
            # Generate expected signature
            expected_signature, _ = self.generate_signature(data, timestamp)
            
            # Compare signatures
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception:
            return False
    
    def get_signed_headers(self, data: Dict) -> Dict[str, str]:
        """
        Get headers with signature for API request.
        
        Args:
            data: Request data to sign
            
        Returns:
            Dictionary of headers including signature
        """
        try:
            # Generate signature
            signature, timestamp = self.generate_signature(data)
            
            # Return headers
            return {
                'X-API-Signature': signature,
                'X-API-Timestamp': str(timestamp),
                'Content-Type': 'application/json'
            }
            
        except Exception as e:
            raise Exception(f"Error getting signed headers: {str(e)}")
    
    def verify_request(self, request_data: Dict, headers: Dict) -> Tuple[bool, str]:
        """
        Verify incoming request signature.
        
        Args:
            request_data: Request data to verify
            headers: Request headers containing signature
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Get signature and timestamp from headers
            signature = headers.get('X-API-Signature')
            timestamp = headers.get('X-API-Timestamp')
            
            if not signature or not timestamp:
                return False, "Missing signature or timestamp"
            
            try:
                timestamp = int(timestamp)
            except ValueError:
                return False, "Invalid timestamp format"
            
            # Verify signature
            if self.verify_signature(request_data, signature, timestamp):
                return True, "Signature verified"
            else:
                return False, "Invalid signature"
                
        except Exception as e:
            return False, f"Error verifying request: {str(e)}"
    
    def rotate_key(self, new_key: str) -> None:
        """
        Rotate the secret key.
        
        Args:
            new_key: New secret key
        """
        self.secret_key = new_key.encode() 