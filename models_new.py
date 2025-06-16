from sqlalchemy import Column, Integer, String, DateTime, Boolean, Numeric, ForeignKey, Table, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"

# Association table for game participants
game_participants = Table('game_participants', Base.metadata,
    Column('game_id', Integer, ForeignKey('games.id')),
    Column('user_id', Integer, ForeignKey('users.id'))
)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    email = Column(String(255), unique=True, nullable=True)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    registered_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    balance = Column(Numeric(10, 2), default=0.00)  # Balance with 2 decimal places
    current_room_id = Column(Integer, ForeignKey('rooms.id'), nullable=True)
    total_games_played = Column(Integer, default=0)
    total_wins = Column(Integer, default=0)
    total_losses = Column(Integer, default=0)
    
    # Relationships
    current_room = relationship("Room", foreign_keys=[current_room_id], back_populates="players")
    created_rooms = relationship("Room", back_populates="creator", foreign_keys="Room.creator_id")
    game_history = relationship("GameHistory", back_populates="user")
    games_played = relationship("Game", secondary=game_participants, back_populates="participants")

    def has_role(self, role: UserRole) -> bool:
        """Check if user has the specified role."""
        return self.role == role

    def is_admin(self) -> bool:
        """Check if user is an admin."""
        return self.role == UserRole.ADMIN

    def is_moderator(self) -> bool:
        """Check if user is a moderator."""
        return self.role == UserRole.MODERATOR

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username}, role={self.role.value})>"

class Room(Base):
    __tablename__ = 'rooms'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    creator_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    max_players = Column(Integer, default=4)  # Default max players per room
    
    # Relationships
    creator = relationship("User", foreign_keys=[creator_id], back_populates="created_rooms")
    players = relationship("User", foreign_keys="User.current_room_id", back_populates="current_room")
    games = relationship("Game", back_populates="room")

    def __repr__(self):
        return f"<Room(name={self.name}, creator_id={self.creator_id})>"

class Game(Base):
    __tablename__ = 'games'

    id = Column(Integer, primary_key=True)
    room_id = Column(Integer, ForeignKey('rooms.id'), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String(50), default='in_progress')  # in_progress, completed, cancelled
    game_type = Column(String(50), nullable=False)  # e.g., 'poker', 'blackjack', etc.
    
    # Relationships
    room = relationship("Room", back_populates="games")
    participants = relationship("User", secondary=game_participants, back_populates="games_played")
    history = relationship("GameHistory", back_populates="game")

    def __repr__(self):
        return f"<Game(id={self.id}, room_id={self.room_id}, status={self.status})>"

class GameHistory(Base):
    __tablename__ = 'game_history'

    id = Column(Integer, primary_key=True)
    game_id = Column(Integer, ForeignKey('games.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    bet_amount = Column(Numeric(10, 2), default=0.00)
    win_amount = Column(Numeric(10, 2), default=0.00)
    result = Column(String(50))  # win, loss, draw
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    game = relationship("Game", back_populates="history")
    user = relationship("User", back_populates="game_history")

    def __repr__(self):
        return f"<GameHistory(game_id={self.game_id}, user_id={self.user_id}, result={self.result})>" 