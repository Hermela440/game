import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from telegram import Update, Message, Chat, User as TelegramUser
from telegram.ext import CallbackContext
from bot import (
    start, help_command, register, login, create_game, join_game,
    leave_game, place_bet, check_balance, get_game_status,
    handle_game_update, handle_error, handle_unknown_command
)
from models import User, Game, Transaction
from database import db

@pytest.fixture
def mock_db():
    """Mock database session"""
    with patch('bot.db') as mock:
        yield mock

@pytest.fixture
def mock_game_engine():
    """Mock game engine"""
    with patch('bot.game_engine') as mock:
        yield mock

@pytest.fixture
def mock_payment_manager():
    """Mock payment manager"""
    with patch('bot.payment_manager') as mock:
        yield mock

@pytest.fixture
def mock_wallet_manager():
    """Mock wallet manager"""
    with patch('bot.wallet_manager') as mock:
        yield mock

@pytest.fixture
def mock_update():
    """Create a mock Telegram update"""
    update = Mock(spec=Update)
    update.message = Mock(spec=Message)
    update.message.chat = Mock(spec=Chat)
    update.message.chat.id = 123456
    update.message.from_user = Mock(spec=TelegramUser)
    update.message.from_user.id = 789012
    update.message.from_user.username = "test_user"
    update.message.text = "/start"
    return update

@pytest.fixture
def mock_context():
    """Create a mock callback context"""
    context = Mock(spec=CallbackContext)
    context.bot = Mock()
    context.bot.send_message = Mock()
    return context

class TestTelegramBot:
    """Test suite for Telegram bot commands and handlers"""

    def test_start_command(self, mock_update, mock_context, mock_db):
        """Test /start command"""
        # Arrange
        mock_db.session.query.return_value.filter.return_value.first.return_value = None

        # Act
        start(mock_update, mock_context)

        # Assert
        mock_context.bot.send_message.assert_called_once()
        call_args = mock_context.bot.send_message.call_args[1]
        assert "Welcome" in call_args['text']
        assert "register" in call_args['text'].lower()

    def test_help_command(self, mock_update, mock_context):
        """Test /help command"""
        # Act
        help_command(mock_update, mock_context)

        # Assert
        mock_context.bot.send_message.assert_called_once()
        call_args = mock_context.bot.send_message.call_args[1]
        assert "Available commands" in call_args['text']
        assert "/register" in call_args['text']
        assert "/login" in call_args['text']

    def test_register_new_user(self, mock_update, mock_context, mock_db):
        """Test user registration"""
        # Arrange
        mock_update.message.text = "/register test@example.com password123"
        mock_db.session.query.return_value.filter.return_value.first.return_value = None

        # Act
        register(mock_update, mock_context)

        # Assert
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()
        mock_context.bot.send_message.assert_called_once()
        assert "Registration successful" in mock_context.bot.send_message.call_args[1]['text']

    def test_register_existing_user(self, mock_update, mock_context, mock_db):
        """Test registering existing user"""
        # Arrange
        mock_update.message.text = "/register test@example.com password123"
        mock_db.session.query.return_value.filter.return_value.first.return_value = User(
            username="test_user",
            email="test@example.com"
        )

        # Act
        register(mock_update, mock_context)

        # Assert
        mock_db.session.add.assert_not_called()
        mock_context.bot.send_message.assert_called_once()
        assert "already registered" in mock_context.bot.send_message.call_args[1]['text'].lower()

    def test_login_success(self, mock_update, mock_context, mock_db):
        """Test successful login"""
        # Arrange
        mock_update.message.text = "/login test@example.com password123"
        mock_db.session.query.return_value.filter.return_value.first.return_value = User(
            username="test_user",
            email="test@example.com",
            password_hash="hashed_password"
        )

        # Act
        login(mock_update, mock_context)

        # Assert
        mock_context.bot.send_message.assert_called_once()
        assert "Login successful" in mock_context.bot.send_message.call_args[1]['text']

    def test_login_failure(self, mock_update, mock_context, mock_db):
        """Test failed login"""
        # Arrange
        mock_update.message.text = "/login test@example.com wrong_password"
        mock_db.session.query.return_value.filter.return_value.first.return_value = User(
            username="test_user",
            email="test@example.com",
            password_hash="hashed_password"
        )

        # Act
        login(mock_update, mock_context)

        # Assert
        mock_context.bot.send_message.assert_called_once()
        assert "Invalid credentials" in mock_context.bot.send_message.call_args[1]['text']

    def test_create_game(self, mock_update, mock_context, mock_db, mock_game_engine):
        """Test game creation"""
        # Arrange
        mock_update.message.text = "/create_game poker 10 100 4"
        mock_db.session.query.return_value.filter.return_value.first.return_value = User(
            username="test_user",
            email="test@example.com"
        )
        mock_game_engine.create_game.return_value = Game(
            room_code="TEST123",
            game_type="poker",
            min_bet=10.0,
            max_bet=100.0,
            max_players=4
        )

        # Act
        create_game(mock_update, mock_context)

        # Assert
        mock_game_engine.create_game.assert_called_once()
        mock_context.bot.send_message.assert_called_once()
        assert "Game created" in mock_context.bot.send_message.call_args[1]['text']
        assert "TEST123" in mock_context.bot.send_message.call_args[1]['text']

    def test_join_game(self, mock_update, mock_context, mock_db, mock_game_engine):
        """Test joining a game"""
        # Arrange
        mock_update.message.text = "/join_game TEST123"
        mock_db.session.query.return_value.filter.return_value.first.return_value = User(
            username="test_user",
            email="test@example.com"
        )
        mock_game_engine.join_game.return_value = True

        # Act
        join_game(mock_update, mock_context)

        # Assert
        mock_game_engine.join_game.assert_called_once()
        mock_context.bot.send_message.assert_called_once()
        assert "joined the game" in mock_context.bot.send_message.call_args[1]['text'].lower()

    def test_leave_game(self, mock_update, mock_context, mock_db, mock_game_engine):
        """Test leaving a game"""
        # Arrange
        mock_update.message.text = "/leave_game TEST123"
        mock_db.session.query.return_value.filter.return_value.first.return_value = User(
            username="test_user",
            email="test@example.com"
        )
        mock_game_engine.leave_game.return_value = True

        # Act
        leave_game(mock_update, mock_context)

        # Assert
        mock_game_engine.leave_game.assert_called_once()
        mock_context.bot.send_message.assert_called_once()
        assert "left the game" in mock_context.bot.send_message.call_args[1]['text'].lower()

    def test_place_bet(self, mock_update, mock_context, mock_db, mock_game_engine):
        """Test placing a bet"""
        # Arrange
        mock_update.message.text = "/bet TEST123 50"
        mock_db.session.query.return_value.filter.return_value.first.return_value = User(
            username="test_user",
            email="test@example.com",
            balance=1000.0
        )
        mock_game_engine.place_bet.return_value = True

        # Act
        place_bet(mock_update, mock_context)

        # Assert
        mock_game_engine.place_bet.assert_called_once()
        mock_context.bot.send_message.assert_called_once()
        assert "bet placed" in mock_context.bot.send_message.call_args[1]['text'].lower()

    def test_check_balance(self, mock_update, mock_context, mock_db, mock_wallet_manager):
        """Test checking balance"""
        # Arrange
        mock_update.message.text = "/balance"
        mock_db.session.query.return_value.filter.return_value.first.return_value = User(
            username="test_user",
            email="test@example.com",
            balance=1000.0
        )
        mock_wallet_manager.get_balance.return_value = 1000.0

        # Act
        check_balance(mock_update, mock_context)

        # Assert
        mock_wallet_manager.get_balance.assert_called_once()
        mock_context.bot.send_message.assert_called_once()
        assert "1000.0" in mock_context.bot.send_message.call_args[1]['text']

    def test_get_game_status(self, mock_update, mock_context, mock_db, mock_game_engine):
        """Test getting game status"""
        # Arrange
        mock_update.message.text = "/status TEST123"
        mock_game_engine.get_game_state.return_value = {
            "room_code": "TEST123",
            "status": "active",
            "current_players": 2,
            "max_players": 4
        }

        # Act
        get_game_status(mock_update, mock_context)

        # Assert
        mock_game_engine.get_game_state.assert_called_once()
        mock_context.bot.send_message.assert_called_once()
        assert "TEST123" in mock_context.bot.send_message.call_args[1]['text']
        assert "active" in mock_context.bot.send_message.call_args[1]['text']

    def test_handle_game_update(self, mock_update, mock_context, mock_db):
        """Test handling game updates"""
        # Arrange
        game_data = {
            "room_code": "TEST123",
            "status": "active",
            "current_players": 2,
            "max_players": 4
        }

        # Act
        handle_game_update(game_data)

        # Assert
        mock_context.bot.send_message.assert_called_once()
        assert "Game Update" in mock_context.bot.send_message.call_args[1]['text']
        assert "TEST123" in mock_context.bot.send_message.call_args[1]['text']

    def test_handle_error(self, mock_update, mock_context):
        """Test error handling"""
        # Arrange
        error = Exception("Test error")

        # Act
        handle_error(mock_update, mock_context, error)

        # Assert
        mock_context.bot.send_message.assert_called_once()
        assert "An error occurred" in mock_context.bot.send_message.call_args[1]['text']

    def test_handle_unknown_command(self, mock_update, mock_context):
        """Test handling unknown commands"""
        # Arrange
        mock_update.message.text = "/unknown_command"

        # Act
        handle_unknown_command(mock_update, mock_context)

        # Assert
        mock_context.bot.send_message.assert_called_once()
        assert "Unknown command" in mock_context.bot.send_message.call_args[1]['text']

    def test_invalid_command_format(self, mock_update, mock_context):
        """Test handling invalid command format"""
        # Arrange
        mock_update.message.text = "/create_game invalid"

        # Act
        create_game(mock_update, mock_context)

        # Assert
        mock_context.bot.send_message.assert_called_once()
        assert "Invalid format" in mock_context.bot.send_message.call_args[1]['text']

    def test_unauthorized_command(self, mock_update, mock_context, mock_db):
        """Test handling unauthorized commands"""
        # Arrange
        mock_update.message.text = "/create_game poker 10 100 4"
        mock_db.session.query.return_value.filter.return_value.first.return_value = None

        # Act
        create_game(mock_update, mock_context)

        # Assert
        mock_context.bot.send_message.assert_called_once()
        assert "Please login first" in mock_context.bot.send_message.call_args[1]['text'] 