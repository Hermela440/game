from flask_socketio import SocketIO, emit, join_room, leave_room
from flask import request, current_app
from functools import wraps
import jwt
from models import User, Room, Game, db
from matchmaking import matchmaking
from game_logic import (
    initialize_game, submit_move, end_round, cancel_game,
    GameState, Round
)
from poker_logic import poker_hand
import json
from cooldown_manager import cooldown_manager
from balance_manager import balance_manager
from payment_manager import payment_manager
from wallet_manager import wallet_manager

socketio = SocketIO()

def authenticated_only(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if not request.args.get('token'):
            return False
        try:
            token = request.args.get('token')
            data = jwt.decode(token, current_app.config['JWT_SECRET_KEY'], algorithms=['HS256'])
            request.user_id = data['user_id']
            return f(*args, **kwargs)
        except:
            return False
    return wrapped

@socketio.on('connect')
@authenticated_only
def handle_connect():
    user = User.query.get(request.user_id)
    if user:
        emit('connection_response', {'data': 'Connected'})

@socketio.on('disconnect')
@authenticated_only
def handle_disconnect():
    """Handle client disconnection"""
    # Leave all rooms
    for room_id in matchmaking.active_rooms:
        if request.user_id in matchmaking.active_rooms[room_id]['players']:
            matchmaking.leave_room(room_id, request.user_id)

@socketio.on('create_room')
@authenticated_only
def handle_create_room(data):
    """Handle room creation"""
    try:
        room = matchmaking.create_room(request.user_id, data)
        join_room(f"room_{room.id}")
        emit('room_created', {
            'room_id': room.id,
            'name': room.name,
            'status': room.status
        })
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('join_room')
@authenticated_only
def handle_join_room(data):
    room_id = data.get('room_id')
    if not room_id:
        emit('error', {'message': 'Room ID is required'})
        return

    game = Game.query.get(room_id)
    if not game:
        emit('error', {'message': 'Game not found'})
        return

    # Check cooldown
    if cooldown_manager.is_on_cooldown(game.id, request.user_id):
        remaining = cooldown_manager.get_cooldown_remaining(game.id, request.user_id)
        emit('cooldown_notification', {
            'message': f'You are on cooldown for {remaining.seconds} seconds',
            'remaining_seconds': remaining.seconds
        })
        return

    # Join the room
    join_room(room_id)
    
    # Notify others
    emit('user_joined', {
        'user_id': request.user_id,
        'username': User.query.get(request.user_id).username
    }, room=room_id)

    # If game is waiting and has enough players, start it
    if game.status == GameState.WAITING and len(game.players) >= 2:
        result = initialize_game(game)
        if 'error' in result:
            emit('error', {'message': result['error']})
            return

        emit('game_started', {
            'status': result['status'],
            'round': result['round'],
            'current_player': result['current_player'],
            'pot': result['pot'],
            'player_bets': result['player_bets'],
            'player_status': result['player_status']
        }, room=room_id)

@socketio.on('leave_room')
@authenticated_only
def handle_leave_room(data):
    room_id = data.get('room_id')
    if not room_id:
        emit('error', {'message': 'Room ID is required'})
        return

    game = Game.query.get(room_id)
    if not game:
        emit('error', {'message': 'Game not found'})
        return

    # If game is in progress, handle player leaving
    if game.status == GameState.IN_PROGRESS:
        if request.user_id in game.player_status:
            game.player_status[request.user_id] = 'folded'
            # Check if game should end
            active_players = [p for p in game.player_status if game.player_status[p] == 'active']
            if len(active_players) <= 1:
                end_result = end_round(game)
                emit('game_over', {
                    'winners': end_result['winners'],
                    'pot': end_result['pot'],
                    'status': end_result['status']
                }, room=room_id)

    # Handle cooldown for leaving player
    cooldown_manager.handle_player_leave(game, request.user_id)

    # Leave the room
    leave_room(room_id)
    emit('user_left', {
        'user_id': request.user_id,
        'username': User.query.get(request.user_id).username
    }, room=room_id)

@socketio.on('get_available_rooms')
@authenticated_only
def handle_get_available_rooms():
    """Handle getting available rooms"""
    try:
        rooms = matchmaking.get_available_rooms()
        emit('available_rooms', {
            'rooms': [{
                'id': room.id,
                'name': room.name,
                'game_type': room.game_type,
                'min_bet': room.min_bet,
                'max_bet': room.max_bet,
                'players_count': len(matchmaking.active_rooms[room.id]['players']),
                'max_players': room.max_players
            } for room in rooms]
        })
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('get_room_status')
@authenticated_only
def handle_get_room_status(data):
    """Handle getting room status"""
    try:
        room_id = data['room_id']
        status = matchmaking.get_room_status(room_id)
        if status:
            emit('room_status', status)
        else:
            emit('error', {'message': 'Room not found'})
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('game_action')
@authenticated_only
def handle_game_action(data):
    room_id = data.get('room_id')
    action = data.get('action')
    amount = data.get('amount')

    if not all([room_id, action]):
        emit('error', {'message': 'Room ID and action are required'})
        return

    game = Game.query.get(room_id)
    if not game:
        emit('error', {'message': 'Game not found'})
        return

    # Check action cooldown
    if cooldown_manager.is_on_cooldown(game.id, request.user_id):
        remaining = cooldown_manager.get_cooldown_remaining(game.id, request.user_id)
        emit('cooldown_notification', {
            'message': f'Action cooldown: {remaining.seconds} seconds remaining',
            'remaining_seconds': remaining.seconds
        })
        return

    # Submit the move
    result = submit_move(game, request.user_id, action, amount)
    
    if 'error' in result:
        emit('error', {'message': result['error']})
        return

    # Get updated game state
    game_state = {
        'current_player': game.current_player,
        'pot': game.pot,
        'player_bets': game.player_bets,
        'player_status': game.player_status,
        'community_cards': game.community_cards,
        'round': Round.get_name(game.round),
        'status': game.status
    }

    # Add player's own cards
    if request.user_id in game.player_cards:
        game_state['player_cards'] = game.player_cards[request.user_id]

    # Emit game state update
    emit('game_state_update', game_state, room=room_id)

    # Emit balance update for the acting player
    if 'new_balance' in result:
        emit('balance_update', {
            'user_id': request.user_id,
            'new_balance': result['new_balance'],
            'action': action,
            'amount': result.get('amount', 0)
        }, room=room_id)

    # If the game is over, emit winner information
    if game.status == GameState.COMPLETED:
        winners = []
        for winner in result['winners']:
            player = User.query.get(winner['player_id'])
            winners.append({
                'player_id': winner['player_id'],
                'username': player.username,
                'hand': winner['hand'],
                'amount': winner['amount'],
                'success': winner['success'],
                'message': winner['message']
            })

            # Emit balance update for winners
            if winner['success']:
                emit('balance_update', {
                    'user_id': winner['player_id'],
                    'new_balance': balance_manager.get_user_balance(winner['player_id']),
                    'action': 'win',
                    'amount': winner['amount']
                }, room=room_id)

        emit('game_over', {
            'winners': winners,
            'pot': result['pot'],
            'status': result['status']
        }, room=room_id)

        # Emit cooldown information
        for player_id in game.players:
            remaining = cooldown_manager.get_cooldown_remaining(game.id, player_id)
            if remaining:
                emit('cooldown_notification', {
                    'player_id': player_id,
                    'message': f'Game cooldown: {remaining.seconds} seconds',
                    'remaining_seconds': remaining.seconds
                }, room=room_id)

@socketio.on('get_game_state')
@authenticated_only
def handle_get_game_state(data):
    room_id = data.get('room_id')
    if not room_id:
        emit('error', {'message': 'Room ID is required'})
        return

    game = Game.query.get(room_id)
    if not game:
        emit('error', {'message': 'Game not found'})
        return

    # Get game state
    game_state = {
        'current_player': game.current_player,
        'pot': game.pot,
        'player_bets': game.player_bets,
        'player_status': game.player_status,
        'community_cards': game.community_cards,
        'round': Round.get_name(game.round),
        'status': game.status
    }

    # Add player's own cards
    if request.user_id in game.player_cards:
        game_state['player_cards'] = game.player_cards[request.user_id]

    emit('game_state', game_state)

@socketio.on('get_balance')
@authenticated_only
def handle_get_balance(data):
    """Handle getting current balance"""
    balance = balance_manager.get_user_balance(request.user_id)
    if balance is not None:
        emit('balance_info', {
            'balance': float(balance),
            'message': f'Current balance: {balance}'
        })
    else:
        emit('error', {'message': 'Could not retrieve balance'})

@socketio.on('cancel_game')
@authenticated_only
def handle_cancel_game(data):
    room_id = data.get('room_id')
    if not room_id:
        emit('error', {'message': 'Room ID is required'})
        return

    game = Game.query.get(room_id)
    if not game:
        emit('error', {'message': 'Game not found'})
        return

    # Only room creator can cancel the game
    if request.user_id != game.created_by:
        emit('error', {'message': 'Only room creator can cancel the game'})
        return

    result = cancel_game(game)
    if 'error' in result:
        emit('error', {'message': result['error']})
        return

    # Emit refund notifications
    for refund in result['refunds']:
        if refund['success']:
            emit('balance_update', {
                'user_id': refund['player_id'],
                'new_balance': balance_manager.get_user_balance(refund['player_id']),
                'action': 'refund',
                'amount': refund['amount']
            }, room=room_id)

    emit('game_cancelled', {
        'status': result['status'],
        'message': result['message'],
        'refunds': result['refunds']
    }, room=room_id)

@socketio.on('get_cooldown')
@authenticated_only
def handle_get_cooldown(data):
    room_id = data.get('room_id')
    if not room_id:
        emit('error', {'message': 'Room ID is required'})
        return

    remaining = cooldown_manager.get_cooldown_remaining(room_id, request.user_id)
    if remaining:
        emit('cooldown_info', {
            'remaining_seconds': remaining.seconds,
            'message': f'Cooldown: {remaining.seconds} seconds remaining'
        })
    else:
        emit('cooldown_info', {
            'remaining_seconds': 0,
            'message': 'No cooldown active'
        })

@socketio.on('initiate_payment')
def handle_initiate_payment(data):
    """Handle payment initiation request."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            emit('error', {'message': 'Authentication required'})
            return
            
        amount = float(data.get('amount', 0))
        currency = data.get('currency', 'USD')
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            emit('error', {'message': 'User not found'})
            return
            
        # Initialize payment
        success, message, payment_data = payment_manager.initiate_payment(
            user=user,
            amount=amount,
            currency=currency
        )
        
        if success:
            emit('payment_initiated', {
                'message': message,
                'checkout_url': payment_data['checkout_url'],
                'transaction_id': payment_data['tx_ref']
            })
        else:
            emit('error', {'message': message})
            
    except Exception as e:
        emit('error', {'message': f'Error initiating payment: {str(e)}'})

@socketio.on('verify_payment')
def handle_verify_payment(data):
    """Handle payment verification request."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            emit('error', {'message': 'Authentication required'})
            return
            
        transaction_id = data.get('transaction_id')
        if not transaction_id:
            emit('error', {'message': 'Transaction ID required'})
            return
            
        # Verify payment
        success, message, payment_data = payment_manager.verify_payment(transaction_id)
        
        if success:
            emit('payment_verified', {
                'message': message,
                'status': 'success',
                'amount': payment_data['amount'],
                'currency': payment_data['currency']
            })
        else:
            emit('error', {'message': message})
            
    except Exception as e:
        emit('error', {'message': f'Error verifying payment: {str(e)}'})

@socketio.on('get_wallet_balance')
def handle_get_wallet_balance():
    """Handle wallet balance inquiry request."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            emit('error', {'message': 'Authentication required'})
            return
            
        # Get user
        user = User.query.get(user_id)
        if not user:
            emit('error', {'message': 'User not found'})
            return
            
        # Get wallet balance
        success, message, balance_data = wallet_manager.get_wallet_balance(user)
        
        if success:
            emit('wallet_balance', {
                'message': message,
                'balance': balance_data['balance'],
                'currency': balance_data['currency']
            })
        else:
            emit('error', {'message': message})
            
    except Exception as e:
        emit('error', {'message': f'Error getting wallet balance: {str(e)}'})

@socketio.on('withdraw_funds')
def handle_withdraw_funds(data):
    """Handle withdrawal request."""
    try:
        user_id = get_current_user_id()
        if not user_id:
            emit('error', {'message': 'Authentication required'})
            return
            
        amount = float(data.get('amount', 0))
        currency = data.get('currency', 'USD')
        
        # Get user
        user = User.query.get(user_id)
        if not user:
            emit('error', {'message': 'User not found'})
            return
            
        # Initiate withdrawal
        success, message, withdrawal_data = wallet_manager.withdraw_funds(
            user=user,
            amount=amount,
            currency=currency
        )
        
        if success:
            emit('withdrawal_initiated', {
                'message': message,
                'transaction_id': withdrawal_data['reference'],
                'amount': amount,
                'currency': currency
            })
        else:
            emit('error', {'message': message})
            
    except Exception as e:
        emit('error', {'message': f'Error initiating withdrawal: {str(e)}'})

# Error handlers
@socketio.on_error()
def error_handler(e):
    emit('error', {'message': str(e)})

@socketio.on_error_default
def default_error_handler(e):
    emit('error', {'message': 'An unexpected error occurred'}) 