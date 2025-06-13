import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from game_engine import GameEngine, GameState, GameType
from models import Game, User, Transaction
from database import db

@pytest.fixture
def mock_db():
    """Mock database session"""
    with patch('game_engine.db') as mock:
        yield mock

@pytest.fixture
def mock_socketio():
    """Mock SocketIO instance"""
    with patch('game_engine.socketio') as mock:
        yield mock

@pytest.fixture
def game_engine(mock_db, mock_socketio):
    """Create a GameEngine instance with mocked dependencies"""
    return GameEngine()

@pytest.fixture
def sample_users():
    """Create sample users for testing"""
    users = []
    for i in range(4):
        user = User(
            username=f"player{i}",
            email=f"player{i}@example.com",
            password_hash="hashed_password",
            balance=1000.0
        )
        users.append(user)
    return users

@pytest.fixture
def sample_game(sample_users):
    """Create a sample game for testing"""
    game = Game(
        room_code="TEST123",
        game_type=GameType.POKER,
        min_bet=10.0,
        max_bet=100.0,
        max_players=4,
        status="waiting",
        created_at=datetime.utcnow()
    )
    game.players = sample_users[:2]  # Add first two players
    return game

class TestGameEngine:
    """Test suite for GameEngine class"""

    def test_create_game(self, game_engine, mock_db, sample_users):
        """Test game creation"""
        # Arrange
        game_data = {
            "room_code": "TEST123",
            "game_type": GameType.POKER,
            "min_bet": 10.0,
            "max_bet": 100.0,
            "max_players": 4,
            "creator": sample_users[0]
        }

        # Act
        game = game_engine.create_game(**game_data)

        # Assert
        assert game.room_code == "TEST123"
        assert game.game_type == GameType.POKER
        assert game.min_bet == 10.0
        assert game.max_bet == 100.0
        assert game.max_players == 4
        assert game.status == "waiting"
        assert game.creator == sample_users[0]
        assert len(game.players) == 1
        assert game.players[0] == sample_users[0]
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()

    def test_join_game(self, game_engine, mock_db, sample_game, sample_users):
        """Test joining a game"""
        # Arrange
        new_player = sample_users[2]

        # Act
        success = game_engine.join_game(sample_game, new_player)

        # Assert
        assert success is True
        assert new_player in sample_game.players
        assert len(sample_game.players) == 3
        mock_db.session.commit.assert_called_once()

    def test_join_full_game(self, game_engine, mock_db, sample_game, sample_users):
        """Test joining a full game"""
        # Arrange
        sample_game.players = sample_users  # Fill the game
        new_player = User(
            username="extra_player",
            email="extra@example.com",
            password_hash="hashed_password"
        )

        # Act
        success = game_engine.join_game(sample_game, new_player)

        # Assert
        assert success is False
        assert new_player not in sample_game.players
        assert len(sample_game.players) == 4

    def test_leave_game(self, game_engine, mock_db, sample_game, sample_users):
        """Test leaving a game"""
        # Arrange
        player_to_leave = sample_game.players[0]

        # Act
        success = game_engine.leave_game(sample_game, player_to_leave)

        # Assert
        assert success is True
        assert player_to_leave not in sample_game.players
        assert len(sample_game.players) == 1
        mock_db.session.commit.assert_called_once()

    def test_start_game(self, game_engine, mock_db, mock_socketio, sample_game):
        """Test starting a game"""
        # Act
        success = game_engine.start_game(sample_game)

        # Assert
        assert success is True
        assert sample_game.status == "active"
        assert sample_game.started_at is not None
        mock_db.session.commit.assert_called_once()
        mock_socketio.emit.assert_called_with(
            'game_started',
            {
                'room_id': sample_game.room_code,
                'started_at': sample_game.started_at.isoformat()
            },
            room=sample_game.room_code
        )

    def test_start_game_insufficient_players(self, game_engine, mock_db, sample_game):
        """Test starting a game with insufficient players"""
        # Arrange
        sample_game.players = [sample_game.players[0]]  # Only one player

        # Act
        success = game_engine.start_game(sample_game)

        # Assert
        assert success is False
        assert sample_game.status == "waiting"
        assert sample_game.started_at is None

    def test_end_game(self, game_engine, mock_db, mock_socketio, sample_game):
        """Test ending a game"""
        # Arrange
        sample_game.status = "active"
        sample_game.started_at = datetime.utcnow()

        # Act
        game_engine.end_game(sample_game)

        # Assert
        assert sample_game.status == "ended"
        assert sample_game.ended_at is not None
        mock_db.session.commit.assert_called_once()
        mock_socketio.emit.assert_called_with(
            'game_ended',
            {
                'room_id': sample_game.room_code,
                'ended_at': sample_game.ended_at.isoformat()
            },
            room=sample_game.room_code
        )

    def test_place_bet(self, game_engine, mock_db, mock_socketio, sample_game, sample_users):
        """Test placing a bet"""
        # Arrange
        sample_game.status = "active"
        player = sample_users[0]
        bet_amount = 50.0

        # Act
        success = game_engine.place_bet(sample_game, player, bet_amount)

        # Assert
        assert success is True
        assert player.balance == 950.0  # 1000 - 50
        mock_db.session.commit.assert_called_once()
        mock_socketio.emit.assert_called_with(
            'bet_placed',
            {
                'room_id': sample_game.room_code,
                'user_id': player.id,
                'amount': bet_amount,
                'new_balance': player.balance
            },
            room=sample_game.room_code
        )

    def test_place_invalid_bet(self, game_engine, mock_db, sample_game, sample_users):
        """Test placing an invalid bet"""
        # Arrange
        sample_game.status = "active"
        player = sample_users[0]
        bet_amount = 150.0  # Exceeds max_bet

        # Act
        success = game_engine.place_bet(sample_game, player, bet_amount)

        # Assert
        assert success is False
        assert player.balance == 1000.0  # Unchanged
        mock_db.session.commit.assert_not_called()

    def test_process_game_results(self, game_engine, mock_db, mock_socketio, sample_game, sample_users):
        """Test processing game results"""
        # Arrange
        sample_game.status = "active"
        sample_game.started_at = datetime.utcnow()
        results = [
            {"user_id": sample_users[0].id, "won": True, "amount": 100.0},
            {"user_id": sample_users[1].id, "won": False, "amount": 50.0}
        ]

        # Act
        game_engine.process_game_results(sample_game, results)

        # Assert
        assert sample_users[0].balance == 1100.0  # 1000 + 100
        assert sample_users[1].balance == 950.0   # 1000 - 50
        mock_db.session.commit.assert_called_once()
        mock_socketio.emit.assert_called_with(
            'game_results',
            {
                'room_id': sample_game.room_code,
                'results': results
            },
            room=sample_game.room_code
        )

    def test_handle_player_disconnect(self, game_engine, mock_db, mock_socketio, sample_game, sample_users):
        """Test handling player disconnection"""
        # Arrange
        sample_game.status = "active"
        disconnected_player = sample_users[0]

        # Act
        game_engine.handle_player_disconnect(sample_game, disconnected_player)

        # Assert
        assert disconnected_player not in sample_game.players
        mock_db.session.commit.assert_called_once()
        mock_socketio.emit.assert_called_with(
            'player_left',
            {
                'room_id': sample_game.room_code,
                'user_id': disconnected_player.id,
                'username': disconnected_player.username,
                'current_players': len(sample_game.players),
                'max_players': sample_game.max_players
            },
            room=sample_game.room_code
        )

    def test_cleanup_inactive_games(self, game_engine, mock_db, sample_game):
        """Test cleanup of inactive games"""
        # Arrange
        sample_game.created_at = datetime.utcnow() - timedelta(hours=2)
        mock_db.session.query.return_value.filter.return_value.all.return_value = [sample_game]

        # Act
        game_engine.cleanup_inactive_games()

        # Assert
        mock_db.session.delete.assert_called_once_with(sample_game)
        mock_db.session.commit.assert_called_once()

    def test_get_game_state(self, game_engine, sample_game):
        """Test getting game state"""
        # Act
        state = game_engine.get_game_state(sample_game)

        # Assert
        assert isinstance(state, dict)
        assert state['room_code'] == sample_game.room_code
        assert state['status'] == sample_game.status
        assert state['current_players'] == len(sample_game.players)
        assert state['max_players'] == sample_game.max_players
        assert 'created_at' in state
        assert 'started_at' in state
        assert 'ended_at' in state

    def test_validate_game_action(self, game_engine, sample_game, sample_users):
        """Test game action validation"""
        # Test valid action
        assert game_engine.validate_game_action(sample_game, sample_users[0], "join") is True

        # Test invalid action (game full)
        sample_game.players = sample_users  # Fill the game
        assert game_engine.validate_game_action(sample_game, sample_users[0], "join") is False

        # Test invalid action (game already started)
        sample_game.status = "active"
        assert game_engine.validate_game_action(sample_game, sample_users[0], "start") is False

    def test_handle_game_error(self, game_engine, mock_socketio, sample_game):
        """Test handling game errors"""
        # Arrange
        error_message = "Test error message"

        # Act
        game_engine.handle_game_error(sample_game, error_message)

        # Assert
        mock_socketio.emit.assert_called_with(
            'error',
            {
                'room_id': sample_game.room_code,
                'message': error_message
            },
            room=sample_game.room_code
        ) 