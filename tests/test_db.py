import pytest
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from models import (
    User, Game, Transaction, GamePlayer, GameResult,
    Wallet, PaymentMethod, Notification, UserSession
)
from database import db, init_db
from werkzeug.security import generate_password_hash

@pytest.fixture(scope='session')
def app():
    """Create a Flask app for testing"""
    from flask import Flask
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['TESTING'] = True
    return app

@pytest.fixture(scope='session')
def _db(app):
    """Create database for testing"""
    with app.app_context():
        db.init_app(app)
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()

@pytest.fixture
def session(_db):
    """Create a new database session for each test"""
    connection = _db.engine.connect()
    transaction = connection.begin()
    session = _db.create_scoped_session(
        options=dict(bind=connection, binds={})
    )
    _db.session = session

    yield session

    transaction.rollback()
    connection.close()
    session.remove()

class TestUserModel:
    """Test suite for User model"""

    def test_create_user(self, session):
        """Test user creation"""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add(user)
        session.commit()

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.created_at is not None
        assert user.is_active is True

    def test_user_unique_constraints(self, session):
        """Test user unique constraints"""
        # Create first user
        user1 = User(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add(user1)
        session.commit()

        # Try to create user with same username
        user2 = User(
            username="testuser",
            email="test2@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add(user2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()

        # Try to create user with same email
        user3 = User(
            username="testuser2",
            email="test@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add(user3)
        with pytest.raises(IntegrityError):
            session.commit()

    def test_user_relationships(self, session):
        """Test user relationships"""
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add(user)
        session.commit()

        # Create wallet
        wallet = Wallet(user_id=user.id, balance=1000.0)
        session.add(wallet)

        # Create payment method
        payment_method = PaymentMethod(
            user_id=user.id,
            method_type="card",
            details={"card_number": "****1234"}
        )
        session.add(payment_method)

        # Create notification
        notification = Notification(
            user_id=user.id,
            message="Test notification",
            type="info"
        )
        session.add(notification)

        session.commit()

        assert user.wallet is not None
        assert user.wallet.balance == 1000.0
        assert len(user.payment_methods) == 1
        assert len(user.notifications) == 1

class TestGameModel:
    """Test suite for Game model"""

    def test_create_game(self, session):
        """Test game creation"""
        game = Game(
            room_code="TEST123",
            game_type="poker",
            min_bet=10.0,
            max_bet=100.0,
            max_players=4,
            status="waiting"
        )
        session.add(game)
        session.commit()

        assert game.id is not None
        assert game.room_code == "TEST123"
        assert game.game_type == "poker"
        assert game.min_bet == 10.0
        assert game.max_bet == 100.0
        assert game.max_players == 4
        assert game.status == "waiting"
        assert game.created_at is not None

    def test_game_relationships(self, session):
        """Test game relationships"""
        # Create users
        user1 = User(
            username="player1",
            email="player1@example.com",
            password_hash=generate_password_hash("password123")
        )
        user2 = User(
            username="player2",
            email="player2@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add_all([user1, user2])
        session.commit()

        # Create game
        game = Game(
            room_code="TEST123",
            game_type="poker",
            min_bet=10.0,
            max_bet=100.0,
            max_players=4,
            status="waiting"
        )
        session.add(game)
        session.commit()

        # Add players
        game_player1 = GamePlayer(
            game_id=game.id,
            user_id=user1.id,
            joined_at=datetime.utcnow()
        )
        game_player2 = GamePlayer(
            game_id=game.id,
            user_id=user2.id,
            joined_at=datetime.utcnow()
        )
        session.add_all([game_player1, game_player2])

        # Add game result
        game_result = GameResult(
            game_id=game.id,
            user_id=user1.id,
            amount=100.0,
            won=True
        )
        session.add(game_result)
        session.commit()

        assert len(game.players) == 2
        assert len(game.results) == 1
        assert game.results[0].amount == 100.0
        assert game.results[0].won is True

class TestTransactionModel:
    """Test suite for Transaction model"""

    def test_create_transaction(self, session):
        """Test transaction creation"""
        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add(user)
        session.commit()

        # Create transaction
        transaction = Transaction(
            user_id=user.id,
            type="deposit",
            amount=100.0,
            currency="USD",
            status="completed"
        )
        session.add(transaction)
        session.commit()

        assert transaction.id is not None
        assert transaction.user_id == user.id
        assert transaction.type == "deposit"
        assert transaction.amount == 100.0
        assert transaction.currency == "USD"
        assert transaction.status == "completed"
        assert transaction.created_at is not None

    def test_transaction_relationships(self, session):
        """Test transaction relationships"""
        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add(user)
        session.commit()

        # Create wallet
        wallet = Wallet(user_id=user.id, balance=1000.0)
        session.add(wallet)

        # Create payment method
        payment_method = PaymentMethod(
            user_id=user.id,
            method_type="card",
            details={"card_number": "****1234"}
        )
        session.add(payment_method)
        session.commit()

        # Create transaction
        transaction = Transaction(
            user_id=user.id,
            type="deposit",
            amount=100.0,
            currency="USD",
            status="completed",
            payment_method_id=payment_method.id
        )
        session.add(transaction)
        session.commit()

        assert transaction.user is not None
        assert transaction.payment_method is not None
        assert transaction.payment_method.method_type == "card"

class TestWalletModel:
    """Test suite for Wallet model"""

    def test_create_wallet(self, session):
        """Test wallet creation"""
        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add(user)
        session.commit()

        # Create wallet
        wallet = Wallet(
            user_id=user.id,
            balance=1000.0,
            currency="USD"
        )
        session.add(wallet)
        session.commit()

        assert wallet.id is not None
        assert wallet.user_id == user.id
        assert wallet.balance == 1000.0
        assert wallet.currency == "USD"
        assert wallet.created_at is not None

    def test_wallet_operations(self, session):
        """Test wallet operations"""
        # Create user and wallet
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add(user)
        session.commit()

        wallet = Wallet(
            user_id=user.id,
            balance=1000.0,
            currency="USD"
        )
        session.add(wallet)
        session.commit()

        # Test deposit
        wallet.balance += 100.0
        session.commit()
        assert wallet.balance == 1100.0

        # Test withdrawal
        wallet.balance -= 50.0
        session.commit()
        assert wallet.balance == 1050.0

class TestPaymentMethodModel:
    """Test suite for PaymentMethod model"""

    def test_create_payment_method(self, session):
        """Test payment method creation"""
        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add(user)
        session.commit()

        # Create payment method
        payment_method = PaymentMethod(
            user_id=user.id,
            method_type="card",
            details={
                "card_number": "****1234",
                "expiry": "12/25",
                "holder_name": "Test User"
            },
            is_default=True
        )
        session.add(payment_method)
        session.commit()

        assert payment_method.id is not None
        assert payment_method.user_id == user.id
        assert payment_method.method_type == "card"
        assert payment_method.details["card_number"] == "****1234"
        assert payment_method.is_default is True
        assert payment_method.created_at is not None

class TestNotificationModel:
    """Test suite for Notification model"""

    def test_create_notification(self, session):
        """Test notification creation"""
        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add(user)
        session.commit()

        # Create notification
        notification = Notification(
            user_id=user.id,
            message="Test notification",
            type="info",
            is_read=False
        )
        session.add(notification)
        session.commit()

        assert notification.id is not None
        assert notification.user_id == user.id
        assert notification.message == "Test notification"
        assert notification.type == "info"
        assert notification.is_read is False
        assert notification.created_at is not None

class TestUserSessionModel:
    """Test suite for UserSession model"""

    def test_create_session(self, session):
        """Test session creation"""
        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add(user)
        session.commit()

        # Create session
        user_session = UserSession(
            user_id=user.id,
            session_token="test_token",
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        session.add(user_session)
        session.commit()

        assert user_session.id is not None
        assert user_session.user_id == user.id
        assert user_session.session_token == "test_token"
        assert user_session.expires_at is not None
        assert user_session.created_at is not None

    def test_session_expiration(self, session):
        """Test session expiration"""
        # Create user
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=generate_password_hash("password123")
        )
        session.add(user)
        session.commit()

        # Create expired session
        expired_session = UserSession(
            user_id=user.id,
            session_token="expired_token",
            expires_at=datetime.utcnow() - timedelta(days=1)
        )
        session.add(expired_session)
        session.commit()

        # Create valid session
        valid_session = UserSession(
            user_id=user.id,
            session_token="valid_token",
            expires_at=datetime.utcnow() + timedelta(days=1)
        )
        session.add(valid_session)
        session.commit()

        # Query for valid sessions
        valid_sessions = session.query(UserSession).filter(
            UserSession.expires_at > datetime.utcnow()
        ).all()

        assert len(valid_sessions) == 1
        assert valid_sessions[0].session_token == "valid_token" 