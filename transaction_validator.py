from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from models.transaction import Transaction, TransactionType, TransactionStatus
from models.user import User
from database import db

class TransactionValidator:
    def __init__(self):
        # Daily transaction limits
        self.daily_deposit_limit = 10000.0  # $10,000
        self.daily_withdrawal_limit = 5000.0  # $5,000
        
        # Transaction amount limits
        self.min_deposit = 10.0  # $10
        self.max_deposit = 5000.0  # $5,000
        self.min_withdrawal = 20.0  # $20
        self.max_withdrawal = 2000.0  # $2,000
        
        # Rate limits
        self.max_daily_transactions = 10
        self.max_hourly_transactions = 3
        
        # Cooldown periods (in minutes)
        self.deposit_cooldown = 5
        self.withdrawal_cooldown = 15
        
    def validate_deposit(self, user: User, amount: float) -> Tuple[bool, str]:
        """
        Validate deposit transaction.
        
        Args:
            user: User object
            amount: Deposit amount
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check minimum amount
            if amount < self.min_deposit:
                return False, f"Minimum deposit amount is ${self.min_deposit}"
            
            # Check maximum amount
            if amount > self.max_deposit:
                return False, f"Maximum deposit amount is ${self.max_deposit}"
            
            # Check daily limit
            daily_deposits = self._get_daily_transactions(user, TransactionType.DEPOSIT)
            if daily_deposits + amount > self.daily_deposit_limit:
                return False, f"Daily deposit limit exceeded. Remaining: ${self.daily_deposit_limit - daily_deposits}"
            
            # Check transaction count limits
            if not self._check_transaction_limits(user, TransactionType.DEPOSIT):
                return False, "Transaction limit exceeded"
            
            # Check cooldown period
            if not self._check_cooldown(user, TransactionType.DEPOSIT):
                return False, f"Please wait {self.deposit_cooldown} minutes between deposits"
            
            return True, "Deposit validation successful"
            
        except Exception as e:
            return False, f"Error validating deposit: {str(e)}"
    
    def validate_withdrawal(self, user: User, amount: float) -> Tuple[bool, str]:
        """
        Validate withdrawal transaction.
        
        Args:
            user: User object
            amount: Withdrawal amount
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check minimum amount
            if amount < self.min_withdrawal:
                return False, f"Minimum withdrawal amount is ${self.min_withdrawal}"
            
            # Check maximum amount
            if amount > self.max_withdrawal:
                return False, f"Maximum withdrawal amount is ${self.max_withdrawal}"
            
            # Check user balance
            if user.balance < amount:
                return False, "Insufficient balance"
            
            # Check daily limit
            daily_withdrawals = self._get_daily_transactions(user, TransactionType.WITHDRAWAL)
            if daily_withdrawals + amount > self.daily_withdrawal_limit:
                return False, f"Daily withdrawal limit exceeded. Remaining: ${self.daily_withdrawal_limit - daily_withdrawals}"
            
            # Check transaction count limits
            if not self._check_transaction_limits(user, TransactionType.WITHDRAWAL):
                return False, "Transaction limit exceeded"
            
            # Check cooldown period
            if not self._check_cooldown(user, TransactionType.WITHDRAWAL):
                return False, f"Please wait {self.withdrawal_cooldown} minutes between withdrawals"
            
            return True, "Withdrawal validation successful"
            
        except Exception as e:
            return False, f"Error validating withdrawal: {str(e)}"
    
    def _get_daily_transactions(self, user: User, transaction_type: TransactionType) -> float:
        """Get total amount of daily transactions for a user."""
        try:
            today = datetime.utcnow().date()
            transactions = Transaction.query.filter(
                Transaction.user_id == user.id,
                Transaction.type == transaction_type,
                Transaction.status == TransactionStatus.COMPLETED,
                Transaction.created_at >= today
            ).all()
            
            return sum(t.amount for t in transactions)
            
        except Exception:
            return 0.0
    
    def _check_transaction_limits(self, user: User, transaction_type: TransactionType) -> bool:
        """Check if user has exceeded transaction limits."""
        try:
            # Check daily limit
            today = datetime.utcnow().date()
            daily_count = Transaction.query.filter(
                Transaction.user_id == user.id,
                Transaction.type == transaction_type,
                Transaction.created_at >= today
            ).count()
            
            if daily_count >= self.max_daily_transactions:
                return False
            
            # Check hourly limit
            hour_ago = datetime.utcnow() - timedelta(hours=1)
            hourly_count = Transaction.query.filter(
                Transaction.user_id == user.id,
                Transaction.type == transaction_type,
                Transaction.created_at >= hour_ago
            ).count()
            
            return hourly_count < self.max_hourly_transactions
            
        except Exception:
            return False
    
    def _check_cooldown(self, user: User, transaction_type: TransactionType) -> bool:
        """Check if user is in cooldown period."""
        try:
            # Get cooldown period
            cooldown_minutes = self.deposit_cooldown if transaction_type == TransactionType.DEPOSIT else self.withdrawal_cooldown
            
            # Get last transaction
            last_transaction = Transaction.query.filter(
                Transaction.user_id == user.id,
                Transaction.type == transaction_type
            ).order_by(Transaction.created_at.desc()).first()
            
            if not last_transaction:
                return True
            
            # Check if cooldown period has passed
            cooldown_time = last_transaction.created_at + timedelta(minutes=cooldown_minutes)
            return datetime.utcnow() >= cooldown_time
            
        except Exception:
            return False
    
    def get_remaining_limits(self, user: User) -> Dict[str, float]:
        """
        Get remaining transaction limits for a user.
        
        Args:
            user: User object
            
        Returns:
            Dictionary of remaining limits
        """
        try:
            daily_deposits = self._get_daily_transactions(user, TransactionType.DEPOSIT)
            daily_withdrawals = self._get_daily_transactions(user, TransactionType.WITHDRAWAL)
            
            return {
                'daily_deposit_remaining': self.daily_deposit_limit - daily_deposits,
                'daily_withdrawal_remaining': self.daily_withdrawal_limit - daily_withdrawals,
                'min_deposit': self.min_deposit,
                'max_deposit': self.max_deposit,
                'min_withdrawal': self.min_withdrawal,
                'max_withdrawal': self.max_withdrawal
            }
            
        except Exception:
            return {
                'daily_deposit_remaining': 0.0,
                'daily_withdrawal_remaining': 0.0,
                'min_deposit': self.min_deposit,
                'max_deposit': self.max_deposit,
                'min_withdrawal': self.min_withdrawal,
                'max_withdrawal': self.max_withdrawal
            } 