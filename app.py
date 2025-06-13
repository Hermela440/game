from flask import Flask, request, jsonify
from flask_socketio import SocketIO
from flask_login import LoginManager, login_required, current_user
from models.user import User
from models.transaction import Transaction
from payment_manager import PaymentManager
from wallet_manager import WalletManager
from rate_limiter import RateLimiter
from validators import (
    PaymentRequest, WithdrawalRequest, GameRequest,
    UserRegistration, RoomCreation, TransactionFilter
)
from error_handlers import (
    register_error_handlers, APIError, ValidationAPIError,
    AuthenticationError, AuthorizationError, ResourceNotFoundError,
    PaymentError, GameError
)
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize LoginManager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize rate limiter
rate_limiter = RateLimiter(
    app,
    redis_url=os.getenv('REDIS_URL')
)

# Initialize payment and wallet managers
payment_manager = PaymentManager(
    api_key=os.getenv('CHAPA_API_KEY'),
    api_secret=os.getenv('CHAPA_API_SECRET'),
    webhook_secret=os.getenv('CHAPA_WEBHOOK_SECRET')
)

wallet_manager = WalletManager(
    api_key=os.getenv('CAPA_API_KEY'),
    api_secret=os.getenv('CAPA_API_SECRET'),
    webhook_secret=os.getenv('CAPA_WEBHOOK_SECRET')
)

# Register error handlers
register_error_handlers(app)

@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if not user:
        raise ResourceNotFoundError("User not found")
    return user

# Auth routes
@app.route('/api/auth/register', methods=['POST'])
@rate_limiter.limit("5 per minute")
def register():
    try:
        data = UserRegistration(**request.get_json())
        # ... registration logic ...
        return jsonify({'success': True, 'message': 'Registration successful'})
    except Exception as e:
        raise ValidationAPIError("Registration failed", str(e))

@app.route('/api/auth/login', methods=['POST'])
@rate_limiter.limit("10 per minute")
def login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            raise ValidationAPIError("Login failed", "Email and password are required")
            
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            raise AuthenticationError("Invalid email or password")
            
        # ... login logic ...
        return jsonify({'success': True, 'message': 'Login successful'})
    except APIError:
        raise
    except Exception as e:
        raise ValidationAPIError("Login failed", str(e))

# Payment routes
@app.route('/api/payment/initiate', methods=['POST'])
@login_required
@rate_limiter.limit("20 per hour")
def initiate_payment():
    try:
        data = PaymentRequest(**request.get_json())
        
        success, message, payment_data = payment_manager.initiate_payment(
            user=current_user,
            amount=data.amount,
            currency=data.currency,
            payment_details={
                'payment_method': data.payment_method,
                'description': data.description
            }
        )
        
        if not success:
            raise PaymentError(message, payment_data.get('payment_id'))
            
        return jsonify({
            'success': True,
            'message': message,
            'data': payment_data
        })
    except APIError:
        raise
    except Exception as e:
        raise PaymentError("Payment initiation failed", str(e))

@app.route('/api/payment/verify/<transaction_id>', methods=['GET'])
@login_required
@rate_limiter.limit("30 per hour")
def verify_payment(transaction_id):
    try:
        success, message, verification_data = payment_manager.verify_payment(transaction_id)
        
        if not success:
            raise PaymentError(message, transaction_id)
            
        return jsonify({
            'success': True,
            'message': message,
            'data': verification_data
        })
    except APIError:
        raise
    except Exception as e:
        raise PaymentError("Payment verification failed", transaction_id)

# Wallet routes
@app.route('/api/wallet/balance', methods=['GET'])
@login_required
@rate_limiter.limit("60 per hour")
def get_wallet_balance():
    success, message, balance_data = wallet_manager.get_wallet_balance(current_user)
    
    return jsonify({
        'success': success,
        'message': message,
        'data': balance_data
    })

@app.route('/api/wallet/withdraw', methods=['POST'])
@login_required
@rate_limiter.limit("10 per hour")
def withdraw_funds():
    try:
        data = WithdrawalRequest(**request.get_json())
        
        success, message, withdrawal_data = wallet_manager.withdraw_funds(
            user=current_user,
            amount=data.amount,
            currency=data.currency,
            wallet_details={
                'wallet_address': data.wallet_address,
                'bank_details': data.bank_details
            }
        )
        
        if not success:
            raise PaymentError(message)
            
        return jsonify({
            'success': True,
            'message': message,
            'data': withdrawal_data
        })
    except APIError:
        raise
    except Exception as e:
        raise PaymentError("Withdrawal failed", str(e))

@app.route('/api/wallet/webhook', methods=['POST'])
@rate_limiter.limit("100 per minute")  # Higher limit for webhooks
def wallet_webhook():
    """Handle Capa Wallet webhooks."""
    try:
        # Get webhook signature from headers
        signature = request.headers.get('X-Capa-Signature')
        if not signature:
            return jsonify({'error': 'Missing signature'}), 400
            
        # Get webhook payload
        payload = request.get_json()
        if not payload:
            return jsonify({'error': 'Invalid payload'}), 400
            
        # Process webhook
        success, message = wallet_manager.handle_webhook(payload, signature)
        
        if success:
            return jsonify({'message': message}), 200
        else:
            return jsonify({'error': message}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Game routes
@app.route('/api/game/create', methods=['POST'])
@login_required
@rate_limiter.limit("10 per hour")
def create_game():
    try:
        data = RoomCreation(**request.get_json())
        # ... game creation logic ...
        return jsonify({'success': True, 'message': 'Game room created successfully'})
    except APIError:
        raise
    except Exception as e:
        raise GameError("Game creation failed", str(e))

@app.route('/api/game/join/<room_code>', methods=['POST'])
@login_required
@rate_limiter.limit("20 per hour")
def join_game(room_code):
    try:
        data = GameRequest(**{**request.get_json(), 'room_code': room_code})
        # ... game join logic ...
        return jsonify({'success': True, 'message': 'Joined game successfully'})
    except APIError:
        raise
    except Exception as e:
        raise GameError("Failed to join game", room_code)

# Transaction routes
@app.route('/api/transactions', methods=['GET'])
@login_required
@rate_limiter.limit("60 per hour")
def get_transactions():
    try:
        data = TransactionFilter(**request.args)
        # ... transaction filtering logic ...
        return jsonify({'success': True, 'data': []})
    except APIError:
        raise
    except Exception as e:
        raise APIError("Failed to fetch transactions", str(e))

# Admin routes
@app.route('/api/admin/users', methods=['GET'])
@login_required
@rate_limiter.limit("100 per hour", exempt_roles=['admin'])
def get_users():
    # ... admin user list logic ...

@app.route('/api/admin/transactions', methods=['GET'])
@login_required
@rate_limiter.limit("100 per hour", exempt_roles=['admin'])
def get_transactions():
    # ... admin transaction list logic ...

# Error handlers
@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({
        'success': False,
        'message': 'Rate limit exceeded',
        'retry_after': e.description
    }), 429

@app.errorhandler(ValidationError)
def validation_error_handler(e):
    return jsonify({
        'success': False,
        'message': str(e)
    }), 400

if __name__ == '__main__':
    socketio.run(app, debug=True) 