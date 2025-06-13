from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Enum, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import db
import enum

class TransactionType(enum.Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    BET = "bet"
    WIN = "win"
    REFUND = "refund"
    BONUS = "bonus"
    PENALTY = "penalty"
    RAKE = "rake"
    TRANSFER = "transfer"

class TransactionStatus(enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"

class PaymentMethod(enum.Enum):
    CREDIT_CARD = "credit_card"
    BANK_TRANSFER = "bank_transfer"
    PAYPAL = "paypal"
    CRYPTO = "crypto"
    SYSTEM = "system"

class Transaction(db.Model):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.PENDING)
    amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    
    # Payment Information
    payment_method = Column(Enum(PaymentMethod))
    payment_details = Column(JSON)  # Store payment-specific details
    transaction_id = Column(String(100))  # External payment processor ID
    fee = Column(Float, default=0.0)  # Transaction fee
    
    # Game-related Information
    game_id = Column(Integer, ForeignKey('games.id'))
    round_number = Column(Integer)  # Game round number if applicable
    
    # Metadata
    description = Column(String(500))
    metadata = Column(JSON)  # Additional transaction metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    completed_at = Column(DateTime)
    
    # Relationships
    user = relationship('User', back_populates='transactions')
    game = relationship('Game', backref='transactions')
    
    def __init__(self, user_id, type, amount, payment_method=None, **kwargs):
        self.user_id = user_id
        self.type = type
        self.amount = amount
        self.payment_method = payment_method
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def process(self):
        """Process the transaction"""
        if self.status != TransactionStatus.PENDING:
            return False, "Transaction is not pending"
            
        try:
            # Update user balance
            user = User.query.get(self.user_id)
            if not user:
                return False, "User not found"
                
            self.balance_before = user.balance
            
            # Handle different transaction types
            if self.type in [TransactionType.DEPOSIT, TransactionType.WIN, TransactionType.BONUS, TransactionType.REFUND]:
                user.balance += self.amount
            elif self.type in [TransactionType.WITHDRAWAL, TransactionType.BET, TransactionType.PENALTY, TransactionType.RAKE]:
                if user.balance < self.amount:
                    return False, "Insufficient balance"
                user.balance -= self.amount
                
            self.balance_after = user.balance
            self.status = TransactionStatus.COMPLETED
            self.completed_at = datetime.utcnow()
            
            # Update user stats
            if self.type == TransactionType.BET:
                user.total_bets += self.amount
            elif self.type == TransactionType.WIN:
                user.total_winnings += self.amount
                
            db.session.commit()
            return True, "Transaction completed successfully"
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    def cancel(self):
        """Cancel the transaction"""
        if self.status != TransactionStatus.PENDING:
            return False, "Transaction cannot be cancelled"
            
        self.status = TransactionStatus.CANCELLED
        self.updated_at = datetime.utcnow()
        db.session.commit()
        return True, "Transaction cancelled"
    
    def refund(self):
        """Refund the transaction"""
        if self.status != TransactionStatus.COMPLETED:
            return False, "Transaction cannot be refunded"
            
        try:
            # Create refund transaction
            refund = Transaction(
                user_id=self.user_id,
                type=TransactionType.REFUND,
                amount=self.amount,
                payment_method=self.payment_method,
                description=f"Refund for transaction {self.id}",
                metadata={'original_transaction_id': self.id}
            )
            
            # Process refund
            success, message = refund.process()
            if success:
                self.status = TransactionStatus.REFUNDED
                self.updated_at = datetime.utcnow()
                db.session.commit()
                return True, "Transaction refunded successfully"
            return False, message
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)
    
    def to_dict(self):
        """Convert transaction object to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'type': self.type.value,
            'status': self.status.value,
            'amount': self.amount,
            'balance_before': self.balance_before,
            'balance_after': self.balance_after,
            'payment_method': self.payment_method.value if self.payment_method else None,
            'payment_details': self.payment_details,
            'transaction_id': self.transaction_id,
            'fee': self.fee,
            'game_id': self.game_id,
            'round_number': self.round_number,
            'description': self.description,
            'metadata': self.metadata,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
    
    @staticmethod
    def get_user_transactions(user_id, limit=50, offset=0, transaction_type=None):
        """Get user's transaction history"""
        query = Transaction.query.filter_by(user_id=user_id)
        if transaction_type:
            query = query.filter_by(type=transaction_type)
        return query.order_by(Transaction.created_at.desc())\
            .limit(limit)\
            .offset(offset)\
            .all()
    
    @staticmethod
    def get_game_transactions(game_id):
        """Get all transactions for a game"""
        return Transaction.query.filter_by(game_id=game_id)\
            .order_by(Transaction.created_at.asc())\
            .all()
    
    @staticmethod
    def get_pending_transactions():
        """Get all pending transactions"""
        return Transaction.query.filter_by(status=TransactionStatus.PENDING)\
            .order_by(Transaction.created_at.asc())\
            .all()
    
    def __repr__(self):
        return f'<Transaction {self.id}: {self.type.value} {self.amount}>' 