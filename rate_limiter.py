from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import Flask, request
from functools import wraps
import redis
from typing import Optional, Callable, Union, List

class RateLimiter:
    def __init__(self, app: Flask, redis_url: Optional[str] = None):
        """
        Initialize rate limiter.
        
        Args:
            app: Flask application instance
            redis_url: Optional Redis URL for distributed rate limiting
        """
        # Configure storage
        if redis_url:
            storage_uri = redis_url
        else:
            storage_uri = "memory://"
            
        # Initialize limiter
        self.limiter = Limiter(
            app=app,
            key_func=get_remote_address,
            storage_uri=storage_uri,
            default_limits=["200 per day", "50 per hour"],
            strategy="fixed-window"  # or "moving-window"
        )
        
        # Store app reference
        self.app = app
        
    def limit(self, 
              limit_value: Union[str, List[str]], 
              key_func: Optional[Callable] = None,
              exempt_when: Optional[Callable] = None,
              error_message: Optional[str] = None,
              exempt_roles: Optional[List[str]] = None) -> Callable:
        """
        Decorator to apply rate limiting to a route.
        
        Args:
            limit_value: Rate limit string or list of limits
            key_func: Optional function to generate rate limit key
            exempt_when: Optional function to determine when to exempt from rate limiting
            error_message: Optional custom error message
            exempt_roles: Optional list of roles exempt from rate limiting
            
        Returns:
            Decorated function
        """
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                # Check if user is exempt based on role
                if exempt_roles:
                    from flask_login import current_user
                    if hasattr(current_user, 'role') and current_user.role in exempt_roles:
                        return f(*args, **kwargs)
                        
                # Check if request should be exempt
                if exempt_when and exempt_when():
                    return f(*args, **kwargs)
                    
                # Apply rate limit
                return self.limiter.limit(
                    limit_value,
                    key_func=key_func,
                    error_message=error_message
                )(f)(*args, **kwargs)
                
            return wrapped
        return decorator
        
    def shared_limit(self, 
                    limit_value: str, 
                    scope: Optional[Union[str, Callable]] = None,
                    key_func: Optional[Callable] = None,
                    error_message: Optional[str] = None) -> Callable:
        """
        Decorator to apply shared rate limiting across multiple routes.
        
        Args:
            limit_value: Rate limit string
            scope: Optional scope for shared limit
            key_func: Optional function to generate rate limit key
            error_message: Optional custom error message
            
        Returns:
            Decorated function
        """
        return self.limiter.shared_limit(
            limit_value,
            scope=scope,
            key_func=key_func,
            error_message=error_message
        )
        
    def exempt(self, f: Callable) -> Callable:
        """
        Decorator to exempt a route from rate limiting.
        
        Args:
            f: Function to exempt
            
        Returns:
            Decorated function
        """
        return self.limiter.exempt(f)
        
    def reset(self, key: str) -> bool:
        """
        Reset rate limit for a key.
        
        Args:
            key: Rate limit key to reset
            
        Returns:
            True if reset was successful
        """
        return self.limiter.reset(key)
        
    def get_view_rate_limit(self) -> Optional[dict]:
        """
        Get rate limit information for the current request.
        
        Returns:
            Dictionary containing rate limit information
        """
        return self.limiter.get_view_rate_limit()
        
    def check(self) -> bool:
        """
        Check if the current request is within rate limits.
        
        Returns:
            True if request is allowed
        """
        return self.limiter.check()
        
    def update_limits(self, new_limits: List[str]) -> None:
        """
        Update default rate limits.
        
        Args:
            new_limits: List of new rate limit strings
        """
        self.limiter.update_limits(new_limits)
        
    def get_limits(self) -> List[str]:
        """
        Get current rate limits.
        
        Returns:
            List of current rate limit strings
        """
        return self.limiter.get_limits()
        
    def get_limits_for_endpoint(self, endpoint: str) -> List[str]:
        """
        Get rate limits for a specific endpoint.
        
        Args:
            endpoint: Endpoint to get limits for
            
        Returns:
            List of rate limit strings for the endpoint
        """
        return self.limiter.get_limits_for_endpoint(endpoint) 