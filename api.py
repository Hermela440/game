from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
from sqlalchemy.orm import Session
from models import Base, User, Room, Game, GameHistory, UserRole
from functools import wraps
import jwt
import datetime
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from typing import List, Optional, Callable
from schemas import (
    UserSchema, UserRegistrationSchema, UserLoginSchema, UserUpdateSchema,
    RoomSchema, GameSchema, GameHistorySchema, WalletDepositSchema, ErrorSchema
)
from marshmallow import ValidationError

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = datetime.timedelta(days=1)
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = datetime.timedelta(days=30)

db = SQLAlchemy(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize schemas
user_schema = UserSchema()
user_registration_schema = UserRegistrationSchema()
user_login_schema = UserLoginSchema()
user_update_schema = UserUpdateSchema()
room_schema = RoomSchema()
game_schema = GameSchema()
game_history_schema = GameHistorySchema()
wallet_deposit_schema = WalletDepositSchema()
error_schema = ErrorSchema()

def handle_validation_error(error):
    """Handle validation errors and return appropriate response."""
    return jsonify(error_schema.dump({
        'message': 'Validation error',
        'errors': error.messages
    })), 400

# Authentication decorators
def role_required(roles: List[UserRole]):
    """Decorator to check user roles."""
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            token = request.headers.get('Authorization')
            if not token:
                return jsonify({'message': 'Token is missing!'}), 401
            try:
                token = token.split(' ')[1]  # Remove 'Bearer ' prefix
                data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
                current_user = User.query.get(data['user_id'])
                if not current_user:
                    return jsonify({'message': 'User not found!'}), 401
                if not current_user.is_active:
                    return jsonify({'message': 'User is inactive!'}), 401
                if current_user.role not in roles:
                    return jsonify({'message': 'Insufficient permissions!'}), 403
            except jwt.ExpiredSignatureError:
                return jsonify({'message': 'Token has expired!'}), 401
            except jwt.InvalidTokenError:
                return jsonify({'message': 'Invalid token!'}), 401
            return f(current_user, *args, **kwargs)
        return decorated
    return decorator

def token_required(f):
    """Decorator to check JWT token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        try:
            token = token.split(' ')[1]  # Remove 'Bearer ' prefix
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'message': 'User not found!'}), 401
            if not current_user.is_active:
                return jsonify({'message': 'User is inactive!'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token has expired!'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token!'}), 401
        return f(current_user, *args, **kwargs)
    return decorated

# Authentication endpoints
@app.route('/api/auth/register', methods=['POST'])
def register():
    try:
        data = user_registration_schema.load(request.get_json())
    except ValidationError as err:
        return handle_validation_error(err)
    
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists!'}), 400
    
    if User.query.filter_by(email=data['email']).first():
        return jsonify({'message': 'Email already exists!'}), 400
    
    hashed_password = generate_password_hash(data['password'])
    new_user = User(
        username=data['username'],
        telegram_id=data['telegram_id'],
        password_hash=hashed_password,
        email=data['email'],
        role=UserRole.ADMIN if data.get('is_admin') else UserRole.USER
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': 'User created successfully!'}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = user_login_schema.load(request.get_json())
    except ValidationError as err:
        return handle_validation_error(err)
    
    user = User.query.filter_by(username=data['username']).first()
    if not user or not check_password_hash(user.password_hash, data['password']):
        return jsonify({'message': 'Invalid credentials!'}), 401
    
    if not user.is_active:
        return jsonify({'message': 'User account is inactive!'}), 401
    
    # Update last login
    user.last_login = datetime.datetime.utcnow()
    db.session.commit()
    
    # Generate tokens
    access_token = jwt.encode({
        'user_id': user.id,
        'role': user.role.value,
        'exp': datetime.datetime.utcnow() + app.config['JWT_ACCESS_TOKEN_EXPIRES']
    }, app.config['SECRET_KEY'])
    
    refresh_token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + app.config['JWT_REFRESH_TOKEN_EXPIRES']
    }, app.config['SECRET_KEY'])
    
    return jsonify({
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user': user_schema.dump(user)
    })

@app.route('/api/auth/refresh', methods=['POST'])
def refresh_token():
    refresh_token = request.headers.get('Authorization')
    if not refresh_token:
        return jsonify({'message': 'Refresh token is missing!'}), 401
    
    try:
        refresh_token = refresh_token.split(' ')[1]
        data = jwt.decode(refresh_token, app.config['SECRET_KEY'], algorithms=["HS256"])
        user = User.query.get(data['user_id'])
        
        if not user or not user.is_active:
            return jsonify({'message': 'Invalid user!'}), 401
        
        access_token = jwt.encode({
            'user_id': user.id,
            'role': user.role.value,
            'exp': datetime.datetime.utcnow() + app.config['JWT_ACCESS_TOKEN_EXPIRES']
        }, app.config['SECRET_KEY'])
        
        return jsonify({'access_token': access_token})
    except:
        return jsonify({'message': 'Invalid refresh token!'}), 401

# Admin endpoints
@app.route('/api/admin/users', methods=['GET'])
@role_required([UserRole.ADMIN])
def get_users(current_user):
    users = User.query.all()
    return jsonify(user_schema.dump(users, many=True))

@app.route('/api/admin/users/<int:user_id>', methods=['PUT'])
@role_required([UserRole.ADMIN])
def update_user(current_user, user_id):
    try:
        data = user_update_schema.load(request.get_json())
    except ValidationError as err:
        return handle_validation_error(err)
    
    user = User.query.get_or_404(user_id)
    
    if 'role' in data:
        try:
            user.role = UserRole(data['role'])
        except ValueError:
            return jsonify({'message': 'Invalid role!'}), 400
    
    if 'is_active' in data:
        user.is_active = data['is_active']
    
    if 'email' in data:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'message': 'Email already exists!'}), 400
        user.email = data['email']
    
    db.session.commit()
    return jsonify({'message': 'User updated successfully!'})

# Wallet endpoints
@app.route('/api/wallet/balance', methods=['GET'])
@token_required
def get_balance(current_user):
    return jsonify({'balance': float(current_user.balance)})

@app.route('/api/wallet/deposit', methods=['POST'])
@token_required
def deposit(current_user):
    try:
        data = wallet_deposit_schema.load(request.get_json())
    except ValidationError as err:
        return handle_validation_error(err)
    
    current_user.balance += data['amount']
    db.session.commit()
    
    # Emit balance update
    emit_user_update(current_user.id, 'balance_updated', {
        'balance': float(current_user.balance)
    })
    
    return jsonify({'message': 'Deposit successful!', 'new_balance': float(current_user.balance)})

# Room endpoints
@app.route('/api/rooms', methods=['GET'])
@token_required
def get_rooms(current_user):
    rooms = Room.query.filter_by(is_active=True).all()
    return jsonify(room_schema.dump(rooms, many=True))

@app.route('/api/rooms', methods=['POST'])
@token_required
def create_room(current_user):
    try:
        data = room_schema.load(request.get_json())
    except ValidationError as err:
        return handle_validation_error(err)
    
    new_room = Room(
        name=data['name'],
        created_by=current_user.id,
        max_players=data['max_players']
    )
    
    db.session.add(new_room)
    db.session.commit()
    
    # Emit room creation event
    emit_room_update(new_room.id, 'room_created', room_schema.dump(new_room))
    
    return jsonify(room_schema.dump(new_room)), 201

# Game endpoints
@app.route('/api/games', methods=['GET'])
@token_required
def get_games(current_user):
    room_id = request.args.get('room_id', type=int)
    if not room_id:
        return jsonify({'message': 'Room ID is required!'}), 400
    
    games = Game.query.filter_by(room_id=room_id).all()
    return jsonify(game_schema.dump(games, many=True))

@app.route('/api/games', methods=['POST'])
@token_required
def create_game(current_user):
    try:
        data = game_schema.load(request.get_json())
    except ValidationError as err:
        return handle_validation_error(err)
    
    new_game = Game(
        room_id=data['room_id'],
        total_rounds=data['total_rounds'],
        min_bet=data['min_bet'],
        max_bet=data['max_bet']
    )
    
    db.session.add(new_game)
    db.session.commit()
    
    # Emit game creation event
    emit_game_update(new_game.id, 'game_created', game_schema.dump(new_game))
    
    return jsonify(game_schema.dump(new_game)), 201

@app.route('/api/games/<int:game_id>/history', methods=['GET'])
@token_required
def get_game_history(current_user, game_id):
    history = GameHistory.query.filter_by(game_id=game_id).all()
    return jsonify(game_history_schema.dump(history, many=True))

# WebSocket event handlers
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    token = request.args.get('token')
    if not token:
        return False
    
    try:
        token = token.split(' ')[1]  # Remove 'Bearer ' prefix
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        user = User.query.get(data['user_id'])
        if not user or not user.is_active:
            return False
        return True
    except:
        return False

@socketio.on('join_room')
def handle_join_room(data):
    """Handle joining a game room."""
    token = request.args.get('token')
    if not token:
        socketio.emit('error', {'message': 'Authentication required'})
        return
    
    try:
        token = token.split(' ')[1]
        data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        user = User.query.get(data['user_id'])
        if not user:
            socketio.emit('error', {'message': 'User not found'})
            return
        
        room_id = data.get('room_id')
        if not room_id:
            socketio.emit('error', {'message': 'Room ID is required'})
            return
        
        room = Room.query.get(room_id)
        if not room:
            socketio.emit('error', {'message': 'Room not found'})
            return
        
        socketio.join_room(f'room_{room_id}')
        socketio.emit('room_joined', {
            'room': room_schema.dump(room),
            'user': user_schema.dump(user)
        }, room=f'room_{room_id}')
    except:
        socketio.emit('error', {'message': 'Invalid token'})

# Helper functions for real-time updates
def emit_room_update(room_id, event_type, data):
    """Emit room update to all users in the room."""
    socketio.emit('room_update', {
        'type': event_type,
        'data': data
    }, room=f'room_{room_id}')

def emit_game_update(game_id, event_type, data):
    """Emit game update to all users in the game's room."""
    game = Game.query.get(game_id)
    if game:
        socketio.emit('game_update', {
            'type': event_type,
            'data': data
        }, room=f'room_{game.room_id}')

def emit_user_update(user_id, event_type, data):
    """Emit update to a specific user."""
    socketio.emit('user_update', {
        'type': event_type,
        'data': data
    }, room=f'user_{user_id}')

# Error handlers
@app.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify(error_schema.dump({
        'message': 'Validation error',
        'errors': error.messages
    })), 400

@app.errorhandler(404)
def handle_not_found(error):
    return jsonify(error_schema.dump({
        'message': 'Resource not found',
        'errors': {'resource': ['The requested resource does not exist']}
    })), 404

@app.errorhandler(500)
def handle_server_error(error):
    return jsonify(error_schema.dump({
        'message': 'Internal server error',
        'errors': {'server': ['An unexpected error occurred']}
    })), 500

if __name__ == '__main__':
    socketio.run(app, debug=True) 