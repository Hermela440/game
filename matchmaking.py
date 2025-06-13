from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import and_, or_
from models import Room, User, Game, GameHistory, db
from schemas import RoomCreateSchema, GameCreateSchema
from flask_socketio import emit
import random

class MatchmakingSystem:
    def __init__(self, min_players: int = 2, max_players: int = 4, 
                 match_timeout: int = 30, balance_threshold: float = 100.0):
        self.min_players = min_players
        self.max_players = max_players
        self.match_timeout = match_timeout  # seconds
        self.balance_threshold = balance_threshold
        self.active_rooms: Dict[int, Dict[str, Any]] = {}

    def create_room(self, creator_id: int, room_data: dict) -> Room:
        """Create a new game room"""
        # Validate room data
        schema = RoomCreateSchema()
        validated_data = schema.load(room_data)
        
        # Create room
        room = Room(
            name=validated_data['name'],
            creator_id=creator_id,
            min_players=self.min_players,
            max_players=self.max_players,
            min_bet=validated_data.get('min_bet', 10.0),
            max_bet=validated_data.get('max_bet', 1000.0),
            game_type=validated_data.get('game_type', 'poker'),
            status='waiting'
        )
        
        db.session.add(room)
        db.session.commit()
        
        # Add creator to room
        self.join_room(room.id, creator_id)
        
        # Initialize room in active rooms
        self.active_rooms[room.id] = {
            'players': [creator_id],
            'created_at': datetime.utcnow(),
            'last_activity': datetime.utcnow()
        }
        
        # Emit room created event
        emit('room_created', {
            'room_id': room.id,
            'name': room.name,
            'creator_id': creator_id,
            'status': room.status
        }, broadcast=True)
        
        return room

    def join_room(self, room_id: int, user_id: int) -> bool:
        """Join a game room"""
        room = Room.query.get(room_id)
        if not room:
            raise ValueError("Room not found")
            
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")
            
        # Check if room is full
        if len(self.active_rooms[room_id]['players']) >= room.max_players:
            raise ValueError("Room is full")
            
        # Check if user has sufficient balance
        if user.balance < room.min_bet:
            raise ValueError("Insufficient balance")
            
        # Check if user is already in the room
        if user_id in self.active_rooms[room_id]['players']:
            raise ValueError("User already in room")
            
        # Add user to room
        self.active_rooms[room_id]['players'].append(user_id)
        self.active_rooms[room_id]['last_activity'] = datetime.utcnow()
        
        # Emit player joined event
        emit('player_joined', {
            'room_id': room_id,
            'user_id': user_id,
            'username': user.username,
            'players_count': len(self.active_rooms[room_id]['players'])
        }, broadcast=True)
        
        # Check if room is ready to start
        if len(self.active_rooms[room_id]['players']) >= room.min_players:
            self._check_room_ready(room_id)
            
        return True

    def leave_room(self, room_id: int, user_id: int) -> bool:
        """Leave a game room"""
        if room_id not in self.active_rooms:
            raise ValueError("Room not found")
            
        if user_id not in self.active_rooms[room_id]['players']:
            raise ValueError("User not in room")
            
        # Remove user from room
        self.active_rooms[room_id]['players'].remove(user_id)
        self.active_rooms[room_id]['last_activity'] = datetime.utcnow()
        
        # Emit player left event
        emit('player_left', {
            'room_id': room_id,
            'user_id': user_id,
            'players_count': len(self.active_rooms[room_id]['players'])
        }, broadcast=True)
        
        # If room is empty, close it
        if not self.active_rooms[room_id]['players']:
            self._close_room(room_id)
            
        return True

    def _check_room_ready(self, room_id: int) -> None:
        """Check if room has enough players to start"""
        room = Room.query.get(room_id)
        if not room:
            return
            
        if len(self.active_rooms[room_id]['players']) >= room.min_players:
            # Start countdown
            emit('room_ready', {
                'room_id': room_id,
                'countdown': 10,
                'players': self.active_rooms[room_id]['players']
            }, broadcast=True)
            
            # Start game after countdown
            self._start_game(room_id)

    def _start_game(self, room_id: int) -> None:
        """Start a new game in the room"""
        room = Room.query.get(room_id)
        if not room:
            return
            
        # Create new game
        game = Game(
            room_id=room_id,
            status='active',
            game_type=room.game_type,
            min_bet=room.min_bet,
            max_bet=room.max_bet
        )
        
        db.session.add(game)
        db.session.commit()
        
        # Initialize game state
        game_state = {
            'game_id': game.id,
            'room_id': room_id,
            'players': self.active_rooms[room_id]['players'],
            'current_round': 1,
            'current_player': 0,
            'pot': 0,
            'bets': {},
            'cards': self._deal_cards(len(self.active_rooms[room_id]['players']))
        }
        
        # Emit game started event
        emit('game_started', {
            'game_id': game.id,
            'room_id': room_id,
            'players': self.active_rooms[room_id]['players'],
            'game_type': room.game_type
        }, broadcast=True)
        
        # Start first round
        self._start_round(game_state)

    def _start_round(self, game_state: dict) -> None:
        """Start a new round in the game"""
        # Emit round started event
        emit('round_started', {
            'game_id': game_state['game_id'],
            'round': game_state['current_round'],
            'current_player': game_state['current_player'],
            'pot': game_state['pot']
        }, broadcast=True)
        
        # Notify first player
        self._notify_player_turn(game_state)

    def _notify_player_turn(self, game_state: dict) -> None:
        """Notify current player it's their turn"""
        current_player_id = game_state['players'][game_state['current_player']]
        
        emit('player_turn', {
            'game_id': game_state['game_id'],
            'player_id': current_player_id,
            'cards': game_state['cards'][current_player_id],
            'pot': game_state['pot'],
            'time_limit': 30
        }, room=f"user_{current_player_id}")

    def _deal_cards(self, num_players: int) -> Dict[int, List[str]]:
        """Deal cards to players"""
        # Simple card dealing for poker
        suits = ['♠', '♥', '♦', '♣']
        values = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        deck = [f"{value}{suit}" for suit in suits for value in values]
        random.shuffle(deck)
        
        # Deal 2 cards to each player
        return {i: deck[i*2:(i+1)*2] for i in range(num_players)}

    def _close_room(self, room_id: int) -> None:
        """Close an empty room"""
        room = Room.query.get(room_id)
        if room:
            room.status = 'closed'
            db.session.commit()
            
        # Remove from active rooms
        if room_id in self.active_rooms:
            del self.active_rooms[room_id]
            
        # Emit room closed event
        emit('room_closed', {
            'room_id': room_id
        }, broadcast=True)

    def cleanup_inactive_rooms(self) -> None:
        """Clean up inactive rooms"""
        current_time = datetime.utcnow()
        rooms_to_close = []
        
        for room_id, room_data in self.active_rooms.items():
            if (current_time - room_data['last_activity']) > timedelta(seconds=self.match_timeout):
                rooms_to_close.append(room_id)
                
        for room_id in rooms_to_close:
            self._close_room(room_id)

    def get_available_rooms(self) -> List[Room]:
        """Get list of available rooms"""
        return Room.query.filter(
            and_(
                Room.status == 'waiting',
                Room.created_at > datetime.utcnow() - timedelta(minutes=30)
            )
        ).all()

    def get_room_status(self, room_id: int) -> Optional[Dict[str, Any]]:
        """Get current status of a room"""
        if room_id not in self.active_rooms:
            return None
            
        room = Room.query.get(room_id)
        if not room:
            return None
            
        return {
            'room_id': room_id,
            'name': room.name,
            'status': room.status,
            'players': self.active_rooms[room_id]['players'],
            'created_at': self.active_rooms[room_id]['created_at'],
            'last_activity': self.active_rooms[room_id]['last_activity']
        }

# Initialize matchmaking system
matchmaking = MatchmakingSystem() 