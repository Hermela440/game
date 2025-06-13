import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from models import User, Transaction, Wallet, PaymentMethod
from payment_manager import PaymentManager
from transaction_validator import TransactionValidator
from database import db

@pytest.fixture
def mock_db():
    """Mock database session"""
    with patch('payment_manager.db') as mock:
        yield mock

@pytest.fixture
def mock_encryption():
    """Mock encryption manager"""
    with patch('payment_manager.encryption_manager') as mock:
        mock.encrypt.return_value = "encrypted_data"
        mock.decrypt.return_value = "decrypted_data"
        yield mock

@pytest.fixture
def mock_signature():
    """Mock signature manager"""
    with patch('payment_manager.signature_manager') as mock:
        mock.sign.return_value = "signed_data"
        mock.verify.return_value = True
        yield mock

@pytest.fixture
def payment_manager(mock_db, mock_encryption, mock_signature):
    """Create PaymentManager instance with mocked dependencies"""
    return PaymentManager(
        api_key="test_key",
        api_secret="test_secret",
        encryption_key="test_encryption_key"
    )

@pytest.fixture
def transaction_validator():
    """Create TransactionValidator instance"""
    return TransactionValidator()

@pytest.fixture
def sample_user():
    """Create a sample user for testing"""
    return User(
        username="testuser",
        email="test@example.com",
        password_hash="hashed_password"
    )

@pytest.fixture
def sample_wallet(sample_user):
    """Create a sample wallet for testing"""
    return Wallet(
        user_id=sample_user.id,
        balance=1000.0,
        currency="USD"
    )

@pytest.fixture
def sample_payment_method(sample_user):
    """Create a sample payment method for testing"""
    return PaymentMethod(
        user_id=sample_user.id,
        method_type="card",
        details={
            "card_number": "****1234",
            "expiry": "12/25",
            "holder_name": "Test User"
        }
    )

class TestPaymentManager:
    """Test suite for PaymentManager class"""

    def test_initiate_payment(self, payment_manager, mock_db, sample_user, sample_wallet):
        """Test payment initiation"""
        # Arrange
        amount = Decimal("100.00")
        currency = "USD"
        payment_method = "card"

        # Act
        result = payment_manager.initiate_payment(
            user_id=sample_user.id,
            amount=amount,
            currency=currency,
            payment_method=payment_method
        )

        # Assert
        assert result["status"] == "pending"
        assert result["amount"] == amount
        assert result["currency"] == currency
        assert "transaction_id" in result
        mock_db.session.add.assert_called_once()
        mock_db.session.commit.assert_called_once()

    def test_verify_payment(self, payment_manager, mock_db, sample_user):
        """Test payment verification"""
        # Arrange
        transaction_id = "test_transaction_id"
        mock_db.session.query.return_value.filter.return_value.first.return_value = Transaction(
            id=transaction_id,
            user_id=sample_user.id,
            amount=Decimal("100.00"),
            status="pending"
        )

        # Act
        result = payment_manager.verify_payment(transaction_id)

        # Assert
        assert result["status"] == "completed"
        assert result["transaction_id"] == transaction_id
        mock_db.session.commit.assert_called_once()

    def test_process_webhook(self, payment_manager, mock_db, sample_user):
        """Test webhook processing"""
        # Arrange
        webhook_data = {
            "transaction_id": "test_transaction_id",
            "status": "completed",
            "amount": "100.00",
            "currency": "USD",
            "signature": "test_signature"
        }

        # Act
        result = payment_manager.process_webhook(webhook_data)

        # Assert
        assert result["status"] == "success"
        assert result["transaction_id"] == webhook_data["transaction_id"]
        mock_db.session.commit.assert_called_once()

    def test_get_transaction_history(self, payment_manager, mock_db, sample_user):
        """Test retrieving transaction history"""
        # Arrange
        mock_db.session.query.return_value.filter.return_value.all.return_value = [
            Transaction(
                id="1",
                user_id=sample_user.id,
                amount=Decimal("100.00"),
                status="completed"
            ),
            Transaction(
                id="2",
                user_id=sample_user.id,
                amount=Decimal("50.00"),
                status="completed"
            )
        ]

        # Act
        result = payment_manager.get_transaction_history(sample_user.id)

        # Assert
        assert len(result) == 2
        assert result[0]["amount"] == Decimal("100.00")
        assert result[1]["amount"] == Decimal("50.00")

    def test_handle_payment_error(self, payment_manager, mock_db, sample_user):
        """Test payment error handling"""
        # Arrange
        transaction_id = "test_transaction_id"
        error_message = "Payment failed"

        # Act
        result = payment_manager.handle_payment_error(transaction_id, error_message)

        # Assert
        assert result["status"] == "failed"
        assert result["error"] == error_message
        mock_db.session.commit.assert_called_once()

class TestTransactionValidator:
    """Test suite for TransactionValidator class"""

    def test_validate_deposit(self, transaction_validator, sample_user, sample_wallet):
        """Test deposit validation"""
        # Arrange
        amount = Decimal("100.00")
        currency = "USD"

        # Act
        result = transaction_validator.validate_deposit(
            user_id=sample_user.id,
            amount=amount,
            currency=currency
        )

        # Assert
        assert result["is_valid"] is True
        assert "remaining_limit" in result

    def test_validate_withdrawal(self, transaction_validator, sample_user, sample_wallet):
        """Test withdrawal validation"""
        # Arrange
        amount = Decimal("50.00")
        currency = "USD"

        # Act
        result = transaction_validator.validate_withdrawal(
            user_id=sample_user.id,
            amount=amount,
            currency=currency
        )

        # Assert
        assert result["is_valid"] is True
        assert "remaining_limit" in result

    def test_validate_transaction_limits(self, transaction_validator, sample_user):
        """Test transaction limits validation"""
        # Arrange
        amount = Decimal("1000.00")  # Exceeds daily limit

        # Act
        result = transaction_validator.validate_deposit(
            user_id=sample_user.id,
            amount=amount,
            currency="USD"
        )

        # Assert
        assert result["is_valid"] is False
        assert "error" in result

    def test_validate_currency(self, transaction_validator, sample_user):
        """Test currency validation"""
        # Arrange
        amount = Decimal("100.00")
        currency = "INVALID"

        # Act
        result = transaction_validator.validate_deposit(
            user_id=sample_user.id,
            amount=amount,
            currency=currency
        )

        # Assert
        assert result["is_valid"] is False
        assert "error" in result

    def test_validate_minimum_amount(self, transaction_validator, sample_user):
        """Test minimum amount validation"""
        # Arrange
        amount = Decimal("1.00")  # Below minimum
        currency = "USD"

        # Act
        result = transaction_validator.validate_deposit(
            user_id=sample_user.id,
            amount=amount,
            currency=currency
        )

        # Assert
        assert result["is_valid"] is False
        assert "error" in result

    def test_validate_maximum_amount(self, transaction_validator, sample_user):
        """Test maximum amount validation"""
        # Arrange
        amount = Decimal("10000.00")  # Above maximum
        currency = "USD"

        # Act
        result = transaction_validator.validate_deposit(
            user_id=sample_user.id,
            amount=amount,
            currency=currency
        )

        # Assert
        assert result["is_valid"] is False
        assert "error" in result

    def test_validate_cooldown_period(self, transaction_validator, sample_user):
        """Test cooldown period validation"""
        # Arrange
        amount = Decimal("100.00")
        currency = "USD"

        # Mock recent transaction
        with patch('transaction_validator.get_recent_transactions') as mock:
            mock.return_value = [{
                "created_at": datetime.utcnow() - timedelta(minutes=1)
            }]

            # Act
            result = transaction_validator.validate_deposit(
                user_id=sample_user.id,
                amount=amount,
                currency=currency
            )

            # Assert
            assert result["is_valid"] is False
            assert "cooldown" in result["error"].lower()

    def test_get_remaining_limits(self, transaction_validator, sample_user):
        """Test getting remaining transaction limits"""
        # Act
        result = transaction_validator.get_remaining_limits(sample_user.id)

        # Assert
        assert "daily_deposit_limit" in result
        assert "daily_withdrawal_limit" in result
        assert "transaction_count_limit" in result

    def test_validate_payment_method(self, transaction_validator, sample_user, sample_payment_method):
        """Test payment method validation"""
        # Act
        result = transaction_validator.validate_payment_method(
            user_id=sample_user.id,
            payment_method_id=sample_payment_method.id
        )

        # Assert
        assert result["is_valid"] is True
        assert "payment_method" in result

    def test_validate_insufficient_balance(self, transaction_validator, sample_user, sample_wallet):
        """Test insufficient balance validation"""
        # Arrange
        amount = Decimal("2000.00")  # More than wallet balance
        currency = "USD"

        # Act
        result = transaction_validator.validate_withdrawal(
            user_id=sample_user.id,
            amount=amount,
            currency=currency
        )

        # Assert
        assert result["is_valid"] is False
        assert "insufficient balance" in result["error"].lower()

    def test_validate_transaction_status(self, transaction_validator, sample_user):
        """Test transaction status validation"""
        # Arrange
        transaction_id = "test_transaction_id"
        status = "pending"

        # Act
        result = transaction_validator.validate_transaction_status(
            transaction_id=transaction_id,
            status=status
        )

        # Assert
        assert result["is_valid"] is True
        assert "status" in result

    def test_validate_transaction_currency_match(self, transaction_validator, sample_user, sample_wallet):
        """Test transaction currency match validation"""
        # Arrange
        amount = Decimal("100.00")
        currency = "EUR"  # Different from wallet currency

        # Act
        result = transaction_validator.validate_deposit(
            user_id=sample_user.id,
            amount=amount,
            currency=currency
        )

        # Assert
        assert result["is_valid"] is False
        assert "currency mismatch" in result["error"].lower() 