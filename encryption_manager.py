from cryptography.fernet import Fernet
import base64
import os
from typing import Dict, Any, Optional
import json

class EncryptionManager:
    def __init__(self, key: Optional[str] = None):
        """
        Initialize the encryption manager.
        
        Args:
            key: Optional encryption key. If not provided, a new key will be generated.
        """
        if key:
            self.key = base64.urlsafe_b64encode(key.encode()[:32].ljust(32, b'0'))
        else:
            self.key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.key)
        
    def get_key(self) -> str:
        """Get the encryption key."""
        return self.key.decode()
    
    def encrypt_data(self, data: Dict[str, Any]) -> str:
        """
        Encrypt sensitive payment data.
        
        Args:
            data: Dictionary containing payment data
            
        Returns:
            Encrypted string
        """
        try:
            # Convert dictionary to JSON string
            json_data = json.dumps(data)
            
            # Encrypt the data
            encrypted_data = self.cipher_suite.encrypt(json_data.encode())
            
            # Return base64 encoded string
            return base64.urlsafe_b64encode(encrypted_data).decode()
            
        except Exception as e:
            raise Exception(f"Error encrypting data: {str(e)}")
    
    def decrypt_data(self, encrypted_data: str) -> Dict[str, Any]:
        """
        Decrypt sensitive payment data.
        
        Args:
            encrypted_data: Base64 encoded encrypted string
            
        Returns:
            Decrypted dictionary
        """
        try:
            # Decode base64 string
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_data)
            
            # Decrypt the data
            decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
            
            # Convert JSON string back to dictionary
            return json.loads(decrypted_data.decode())
            
        except Exception as e:
            raise Exception(f"Error decrypting data: {str(e)}")
    
    def encrypt_payment_details(self, payment_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in payment details.
        
        Args:
            payment_details: Dictionary containing payment details
            
        Returns:
            Dictionary with encrypted sensitive fields
        """
        try:
            # Create a copy of payment details
            encrypted_details = payment_details.copy()
            
            # Fields to encrypt
            sensitive_fields = [
                'card_number',
                'cvv',
                'expiry_date',
                'account_number',
                'routing_number',
                'bank_account',
                'wallet_address',
                'private_key'
            ]
            
            # Encrypt sensitive fields
            for field in sensitive_fields:
                if field in encrypted_details:
                    encrypted_details[field] = self.encrypt_data({field: encrypted_details[field]})
            
            return encrypted_details
            
        except Exception as e:
            raise Exception(f"Error encrypting payment details: {str(e)}")
    
    def decrypt_payment_details(self, encrypted_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in payment details.
        
        Args:
            encrypted_details: Dictionary containing encrypted payment details
            
        Returns:
            Dictionary with decrypted sensitive fields
        """
        try:
            # Create a copy of payment details
            decrypted_details = encrypted_details.copy()
            
            # Fields to decrypt
            sensitive_fields = [
                'card_number',
                'cvv',
                'expiry_date',
                'account_number',
                'routing_number',
                'bank_account',
                'wallet_address',
                'private_key'
            ]
            
            # Decrypt sensitive fields
            for field in sensitive_fields:
                if field in decrypted_details:
                    decrypted_data = self.decrypt_data(decrypted_details[field])
                    decrypted_details[field] = decrypted_data[field]
            
            return decrypted_details
            
        except Exception as e:
            raise Exception(f"Error decrypting payment details: {str(e)}")
    
    def rotate_key(self) -> str:
        """
        Generate a new encryption key.
        
        Returns:
            New encryption key
        """
        self.key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.key)
        return self.get_key() 