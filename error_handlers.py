from flask import jsonify, request
from werkzeug.exceptions import HTTPException
from pydantic import ValidationError
from typing import Dict, Any, Optional, Tuple
import traceback
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class APIError(Exception):
    """Base class for API errors."""
    def __init__(self, message: str, status_code: int = 400, payload: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.payload = payload
        self.timestamp = datetime.utcnow()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary."""
        rv = {
            'success': False,
            'message': self.message,
            'timestamp': self.timestamp.isoformat()
        }
        if self.payload:
            rv['details'] = self.payload
        return rv

class ValidationAPIError(APIError):
    """Validation error."""
    def __init__(self, message: str, errors: Optional[Dict[str, Any]] = None):
        super().__init__(message, status_code=400)
        self.errors = errors
        
    def to_dict(self) -> Dict[str, Any]:
        rv = super().to_dict()
        if self.errors:
            rv['validation_errors'] = self.errors
        return rv

class AuthenticationError(APIError):
    """Authentication error."""
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)

class AuthorizationError(APIError):
    """Authorization error."""
    def __init__(self, message: str = "Not authorized"):
        super().__init__(message, status_code=403)

class ResourceNotFoundError(APIError):
    """Resource not found error."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)

class RateLimitError(APIError):
    """Rate limit error."""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        super().__init__(message, status_code=429)
        self.retry_after = retry_after
        
    def to_dict(self) -> Dict[str, Any]:
        rv = super().to_dict()
        if self.retry_after:
            rv['retry_after'] = self.retry_after
        return rv

class PaymentError(APIError):
    """Payment processing error."""
    def __init__(self, message: str, payment_id: Optional[str] = None):
        super().__init__(message, status_code=400)
        self.payment_id = payment_id
        
    def to_dict(self) -> Dict[str, Any]:
        rv = super().to_dict()
        if self.payment_id:
            rv['payment_id'] = self.payment_id
        return rv

class GameError(APIError):
    """Game-related error."""
    def __init__(self, message: str, game_id: Optional[str] = None):
        super().__init__(message, status_code=400)
        self.game_id = game_id
        
    def to_dict(self) -> Dict[str, Any]:
        rv = super().to_dict()
        if self.game_id:
            rv['game_id'] = self.game_id
        return rv

def register_error_handlers(app) -> None:
    """Register error handlers with Flask application."""
    
    @app.errorhandler(APIError)
    def handle_api_error(error: APIError) -> Tuple[Dict[str, Any], int]:
        """Handle API errors."""
        response = error.to_dict()
        logger.error(f"API Error: {error.message}", extra={
            'status_code': error.status_code,
            'payload': error.payload,
            'path': request.path,
            'method': request.method
        })
        return jsonify(response), error.status_code
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError) -> Tuple[Dict[str, Any], int]:
        """Handle Pydantic validation errors."""
        response = {
            'success': False,
            'message': 'Validation error',
            'validation_errors': error.errors(),
            'timestamp': datetime.utcnow().isoformat()
        }
        logger.error(f"Validation Error: {str(error)}", extra={
            'errors': error.errors(),
            'path': request.path,
            'method': request.method
        })
        return jsonify(response), 400
    
    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException) -> Tuple[Dict[str, Any], int]:
        """Handle HTTP errors."""
        response = {
            'success': False,
            'message': error.description,
            'timestamp': datetime.utcnow().isoformat()
        }
        logger.error(f"HTTP Error: {error.description}", extra={
            'status_code': error.code,
            'path': request.path,
            'method': request.method
        })
        return jsonify(response), error.code
    
    @app.errorhandler(Exception)
    def handle_generic_error(error: Exception) -> Tuple[Dict[str, Any], int]:
        """Handle unexpected errors."""
        response = {
            'success': False,
            'message': 'An unexpected error occurred',
            'timestamp': datetime.utcnow().isoformat()
        }
        
        # Log the full traceback
        logger.error(f"Unexpected Error: {str(error)}", extra={
            'traceback': traceback.format_exc(),
            'path': request.path,
            'method': request.method
        })
        
        # Include error details in development mode
        if app.debug:
            response['error'] = str(error)
            response['traceback'] = traceback.format_exc()
            
        return jsonify(response), 500
    
    @app.errorhandler(429)
    def handle_rate_limit_error(error: RateLimitError) -> Tuple[Dict[str, Any], int]:
        """Handle rate limit errors."""
        response = {
            'success': False,
            'message': 'Rate limit exceeded',
            'timestamp': datetime.utcnow().isoformat()
        }
        if hasattr(error, 'description'):
            response['retry_after'] = error.description
        logger.warning(f"Rate Limit Exceeded: {request.path}", extra={
            'path': request.path,
            'method': request.method
        })
        return jsonify(response), 429 