import bcrypt
from typing import Tuple, Optional
from models.user import User
from database import db

class PasswordManager:
    @staticmethod
    def hash_password(password: str) -> Tuple[str, str]:
        """
        Hash a password using bcrypt.
        
        Args:
            password: Plain text password
            
        Returns:
            Tuple of (hashed_password, salt)
        """
        # Generate a random salt
        salt = bcrypt.gensalt()
        
        # Hash the password with the salt
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        
        return hashed.decode('utf-8'), salt.decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.
        
        Args:
            password: Plain text password to verify
            hashed_password: Stored hashed password
            
        Returns:
            True if password matches, False otherwise
        """
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    
    @staticmethod
    def update_password(user: User, new_password: str) -> bool:
        """
        Update a user's password.
        
        Args:
            user: User object
            new_password: New plain text password
            
        Returns:
            True if password was updated successfully
        """
        try:
            # Hash the new password
            hashed_password, salt = PasswordManager.hash_password(new_password)
            
            # Update user's password
            user.password = hashed_password
            user.password_salt = salt
            
            # Save changes
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating password: {str(e)}")
            return False
    
    @staticmethod
    def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password strength.
        
        Args:
            password: Password to validate
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if len(password) < 8:
            return False, "Password must be at least 8 characters long"
            
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
            
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
            
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one number"
            
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
            return False, "Password must contain at least one special character"
            
        return True, None 