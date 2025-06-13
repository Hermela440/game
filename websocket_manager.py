from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_login import current_user
from functools import wraps
import json

socketio = SocketIO()

def authenticated_only(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return
        return f(*args, **kwargs)
    return wrapped

class WebSocketManager:
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        socketio.init_app(app, cors_allowed_origins="*")

    @socketio.on('connect')
    @authenticated_only
    def handle_connect():
        """Handle client connection."""
        if current_user.is_authenticated:
            join_room(f'user_{current_user.id}')
            emit('connection_established', {
                'message': 'Connected to WebSocket server',
                'user_id': current_user.id
            })

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection."""
        if current_user.is_authenticated:
            leave_room(f'user_{current_user.id}')

    @socketio.on('join_game_room')
    @authenticated_only
    def handle_join_game_room(data):
        """Handle joining a game room."""
        room_id = data.get('room_id')
        if room_id:
            join_room(f'game_{room_id}')
            emit('room_joined', {
                'room_id': room_id,
                'message': f'Joined game room {room_id}'
            }, room=f'game_{room_id}')

    @socketio.on('leave_game_room')
    @authenticated_only
    def handle_leave_game_room(data):
        """Handle leaving a game room."""
        room_id = data.get('room_id')
        if room_id:
            leave_room(f'game_{room_id}')
            emit('room_left', {
                'room_id': room_id,
                'message': f'Left game room {room_id}'
            }, room=f'game_{room_id}')

    @staticmethod
    def emit_balance_update(user_id, new_balance, currency):
        """Emit balance update to a specific user."""
        socketio.emit('balance_update', {
            'balance': new_balance,
            'currency': currency
        }, room=f'user_{user_id}')

    @staticmethod
    def emit_transaction_update(user_id, transaction):
        """Emit transaction update to a specific user."""
        socketio.emit('transaction_update', {
            'transaction': transaction.to_dict()
        }, room=f'user_{user_id}')

    @staticmethod
    def emit_game_update(room_id, game_data):
        """Emit game update to all users in a game room."""
        socketio.emit('game_update', game_data, room=f'game_{room_id}')

    @staticmethod
    def emit_player_joined(room_id, player_data):
        """Emit player joined event to a game room."""
        socketio.emit('player_joined', player_data, room=f'game_{room_id}')

    @staticmethod
    def emit_player_left(room_id, player_data):
        """Emit player left event to a game room."""
        socketio.emit('player_left', player_data, room=f'game_{room_id}')

    @staticmethod
    def emit_game_started(room_id, game_data):
        """Emit game started event to a game room."""
        socketio.emit('game_started', game_data, room=f'game_{room_id}')

    @staticmethod
    def emit_game_ended(room_id, game_data):
        """Emit game ended event to a game room."""
        socketio.emit('game_ended', game_data, room=f'game_{room_id}')

    @staticmethod
    def emit_chat_message(room_id, message_data):
        """Emit chat message to a game room."""
        socketio.emit('chat_message', message_data, room=f'game_{room_id}')

    @staticmethod
    def emit_error(user_id, error_message):
        """Emit error message to a specific user."""
        socketio.emit('error', {
            'message': error_message
        }, room=f'user_{user_id}')

# Initialize WebSocket manager
ws_manager = WebSocketManager() 