from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Enum, JSON, ForeignKey
from sqlalchemy.orm import relationship
from database import db
import enum

class GameStatus(enum.Enum):
    WAITING = "waiting"
    STARTING = "starting"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class Round(enum.Enum):
    PRE_FLOP = "pre_flop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"

class MoveType(enum.Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"

class Game(db.Model):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=False)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(Enum(GameStatus), default=GameStatus.WAITING)
    
    # Game Settings
    min_players = Column(Integer, default=2)
    max_players = Column(Integer, default=9)
    min_bet = Column(Float, default=1.0)
    max_bet = Column(Float, default=100.0)
    starting_stack = Column(Float, default=1000.0)
    
    # Player Management
    players = Column(JSON, default=list)  # List of player IDs
    player_status = Column(JSON, default=dict)  # Player status (active, folded, etc.)
    player_stacks = Column(JSON, default=dict)  # Current stack for each player
    player_bets = Column(JSON, default=dict)  # Current bet for each player
    player_positions = Column(JSON, default=dict)  # Player positions at table
    
    # Game State
    current_player = Column(Integer)  # ID of current player
    dealer_position = Column(Integer, default=0)
    pot = Column(Float, default=0.0)
    community_cards = Column(JSON, default=list)
    player_cards = Column(JSON, default=dict)  # Cards for each player
    current_round = Column(Enum(Round), default=Round.PRE_FLOP)
    round_number = Column(Integer, default=0)
    
    # Game History
    moves = Column(JSON, default=list)  # List of moves made in the game
    rounds = Column(JSON, default=list)  # List of completed rounds
    winners = Column(JSON, default=list)  # List of winners and their winnings
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    
    # Relationships
    room = relationship('Room', back_populates='games')
    creator = relationship('User', backref='created_games')
    transactions = relationship('Transaction', backref='game', lazy='dynamic')
    
    def __init__(self, room_id, created_by, **kwargs):
        self.room_id = room_id
        self.created_by = created_by
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def add_player(self, player_id):
        """Add a player to the game"""
        if player_id not in self.players and len(self.players) < self.max_players:
            self.players.append(player_id)
            self.player_status[player_id] = 'active'
            self.player_stacks[player_id] = self.starting_stack
            self.player_bets[player_id] = 0.0
            return True
        return False
    
    def remove_player(self, player_id):
        """Remove a player from the game"""
        if player_id in self.players:
            self.players.remove(player_id)
            self.player_status.pop(player_id, None)
            self.player_stacks.pop(player_id, None)
            self.player_bets.pop(player_id, None)
            self.player_positions.pop(player_id, None)
            self.player_cards.pop(player_id, None)
            return True
        return False
    
    def record_move(self, player_id, move_type, amount=None, round_number=None):
        """Record a player's move"""
        move = {
            'player_id': player_id,
            'move_type': move_type.value,
            'amount': amount,
            'round': round_number or self.round_number,
            'timestamp': datetime.utcnow().isoformat()
        }
        self.moves.append(move)
        
        # Update player status based on move
        if move_type == MoveType.FOLD:
            self.player_status[player_id] = 'folded'
        elif move_type == MoveType.ALL_IN:
            self.player_status[player_id] = 'all_in'
    
    def start_round(self, round_type):
        """Start a new round"""
        self.current_round = round_type
        self.round_number += 1
        round_data = {
            'round_type': round_type.value,
            'round_number': self.round_number,
            'started_at': datetime.utcnow().isoformat(),
            'pot': self.pot,
            'community_cards': self.community_cards.copy(),
            'player_status': self.player_status.copy(),
            'player_stacks': self.player_stacks.copy(),
            'player_bets': self.player_bets.copy()
        }
        self.rounds.append(round_data)
    
    def end_round(self, winners):
        """End the current round and record winners"""
        if not self.rounds:
            return
            
        current_round = self.rounds[-1]
        current_round['ended_at'] = datetime.utcnow().isoformat()
        current_round['winners'] = winners
        
        # Update player stacks with winnings
        for winner in winners:
            player_id = winner['player_id']
            amount = winner['amount']
            self.player_stacks[player_id] += amount
            
        # Reset player bets for next round
        self.player_bets = {player_id: 0.0 for player_id in self.players}
        self.pot = 0.0
    
    def end_game(self, winners):
        """End the game and record final results"""
        self.status = GameStatus.COMPLETED
        self.ended_at = datetime.utcnow()
        self.winners = winners
        
        # Record final game state
        game_result = {
            'ended_at': self.ended_at.isoformat(),
            'winners': winners,
            'final_pot': self.pot,
            'final_stacks': self.player_stacks,
            'community_cards': self.community_cards,
            'player_cards': self.player_cards
        }
        self.rounds.append(game_result)
    
    def cancel_game(self):
        """Cancel the game"""
        self.status = GameStatus.CANCELLED
        self.ended_at = datetime.utcnow()
        
        # Record cancellation
        game_result = {
            'ended_at': self.ended_at.isoformat(),
            'status': 'cancelled',
            'reason': 'Game cancelled by creator',
            'final_stacks': self.player_stacks
        }
        self.rounds.append(game_result)
    
    def to_dict(self):
        """Convert game object to dictionary"""
        return {
            'id': self.id,
            'room_id': self.room_id,
            'created_by': self.created_by,
            'status': self.status.value,
            'min_players': self.min_players,
            'max_players': self.max_players,
            'min_bet': self.min_bet,
            'max_bet': self.max_bet,
            'starting_stack': self.starting_stack,
            'players': self.players,
            'player_status': self.player_status,
            'player_stacks': self.player_stacks,
            'player_bets': self.player_bets,
            'player_positions': self.player_positions,
            'current_player': self.current_player,
            'dealer_position': self.dealer_position,
            'pot': self.pot,
            'community_cards': self.community_cards,
            'current_round': self.current_round.value,
            'round_number': self.round_number,
            'moves': self.moves,
            'rounds': self.rounds,
            'winners': self.winners,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'ended_at': self.ended_at.isoformat() if self.ended_at else None
        }
    
    @staticmethod
    def get_active_games():
        """Get all active games"""
        return Game.query.filter(
            Game.status.in_([GameStatus.WAITING, GameStatus.STARTING, GameStatus.IN_PROGRESS])
        ).all()
    
    @staticmethod
    def get_player_games(player_id):
        """Get all games a player has participated in"""
        return Game.query.filter(
            Game.players.contains([player_id])
        ).order_by(Game.created_at.desc()).all()
    
    def __repr__(self):
        return f'<Game {self.id}: {self.status.value}>' 