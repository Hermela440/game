from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship
from models.user import Base, User
import enum

class RoomStatus(enum.Enum):
    WAITING = "waiting"
    PLAYING = "playing"
    FINISHED = "finished"

class Room(Base):
    __tablename__ = 'rooms'

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    creator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    status = Column(Enum(RoomStatus), default=RoomStatus.WAITING)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    max_players = Column(Integer, default=6)
    min_players = Column(Integer, default=2)
    current_players = Column(Integer, default=1)
    game_type = Column(String(50), default="poker")
    buy_in = Column(Integer, default=0)
    is_private = Column(Boolean, default=False)
    password = Column(String(100), nullable=True)

    # Relationships
    creator = relationship('User', backref='created_rooms', foreign_keys=[creator_id])
    players = relationship('User', secondary='room_players', backref='joined_rooms')
    games = relationship('Game', backref='room', lazy='dynamic')

    def __init__(self, name, creator_id, game_type="poker", buy_in=0, is_private=False, password=None):
        self.name = name
        self.creator_id = creator_id
        self.game_type = game_type
        self.buy_in = buy_in
        self.is_private = is_private
        self.password = password

    def add_player(self, user):
        if self.current_players < self.max_players and user not in self.players:
            self.players.append(user)
            self.current_players += 1
            return True
        return False

    def remove_player(self, user):
        if user in self.players:
            self.players.remove(user)
            self.current_players -= 1
            return True
        return False

    def is_full(self):
        return self.current_players >= self.max_players

    def can_start(self):
        return self.current_players >= self.min_players

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'creator_id': self.creator_id,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'is_active': self.is_active,
            'max_players': self.max_players,
            'min_players': self.min_players,
            'current_players': self.current_players,
            'game_type': self.game_type,
            'buy_in': self.buy_in,
            'is_private': self.is_private
        }
