from pydantic import BaseModel, Field, validator, constr
from typing import Optional, List, Dict, Union
from decimal import Decimal
import re
from datetime import datetime

# Custom validators
def validate_amount(amount: Union[int, float, str, Decimal]) -> Decimal:
    """Validate and convert amount to Decimal."""
    try:
        amount = Decimal(str(amount))
        if amount <= 0:
            raise ValueError("Amount must be greater than 0")
        if amount > Decimal('1000000'):  # Maximum amount limit
            raise ValueError("Amount exceeds maximum limit")
        return amount
    except (ValueError, TypeError, ArithmeticError) as e:
        raise ValueError(f"Invalid amount: {str(e)}")

def validate_currency(currency: str) -> str:
    """Validate currency code."""
    if not re.match(r'^[A-Z]{3}$', currency):
        raise ValueError("Invalid currency code. Must be 3 uppercase letters")
    return currency

def validate_room_code(code: str) -> str:
    """Validate room code format."""
    if not re.match(r'^[A-Z0-9]{6}$', code):
        raise ValueError("Invalid room code. Must be 6 alphanumeric characters")
    return code

def validate_username(username: str) -> str:
    """Validate username format."""
    if not re.match(r'^[a-zA-Z0-9_]{3,20}$', username):
        raise ValueError("Username must be 3-20 characters and contain only letters, numbers, and underscores")
    return username

def validate_email(email: str) -> str:
    """Validate email format."""
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        raise ValueError("Invalid email format")
    return email

# Pydantic models for request validation
class PaymentRequest(BaseModel):
    amount: Decimal = Field(..., description="Payment amount")
    currency: str = Field(..., description="Currency code")
    payment_method: str = Field(..., description="Payment method")
    description: Optional[str] = Field(None, description="Payment description")
    
    _validate_amount = validator('amount', allow_reuse=True)(validate_amount)
    _validate_currency = validator('currency', allow_reuse=True)(validate_currency)
    
    @validator('payment_method')
    def validate_payment_method(cls, v):
        valid_methods = ['CREDIT_CARD', 'BANK_TRANSFER', 'PAYPAL', 'CRYPTO']
        if v not in valid_methods:
            raise ValueError(f"Invalid payment method. Must be one of: {', '.join(valid_methods)}")
        return v

class WithdrawalRequest(BaseModel):
    amount: Decimal = Field(..., description="Withdrawal amount")
    currency: str = Field(..., description="Currency code")
    wallet_address: Optional[str] = Field(None, description="Wallet address for crypto withdrawals")
    bank_details: Optional[Dict] = Field(None, description="Bank details for bank transfers")
    
    _validate_amount = validator('amount', allow_reuse=True)(validate_amount)
    _validate_currency = validator('currency', allow_reuse=True)(validate_currency)
    
    @validator('wallet_address')
    def validate_wallet_address(cls, v, values):
        if values.get('currency') == 'CRYPTO' and not v:
            raise ValueError("Wallet address is required for crypto withdrawals")
        if v and not re.match(r'^[a-zA-Z0-9]{30,}$', v):
            raise ValueError("Invalid wallet address format")
        return v

class GameRequest(BaseModel):
    room_code: str = Field(..., description="Room code")
    bet_amount: Decimal = Field(..., description="Bet amount")
    currency: str = Field(..., description="Currency code")
    game_type: str = Field(..., description="Game type")
    
    _validate_amount = validator('bet_amount', allow_reuse=True)(validate_amount)
    _validate_currency = validator('currency', allow_reuse=True)(validate_currency)
    _validate_room_code = validator('room_code', allow_reuse=True)(validate_room_code)
    
    @validator('game_type')
    def validate_game_type(cls, v):
        valid_types = ['TEXAS_HOLDEM', 'OMAHA', 'SEVEN_CARD_STUD']
        if v not in valid_types:
            raise ValueError(f"Invalid game type. Must be one of: {', '.join(valid_types)}")
        return v

class UserRegistration(BaseModel):
    username: constr(min_length=3, max_length=20) = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    password: constr(min_length=8) = Field(..., description="Password")
    referral_code: Optional[str] = Field(None, description="Referral code")
    
    _validate_username = validator('username', allow_reuse=True)(validate_username)
    _validate_email = validator('email', allow_reuse=True)(validate_email)
    
    @validator('password')
    def validate_password_strength(cls, v):
        if not re.search(r'[A-Z]', v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r'[a-z]', v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r'[0-9]', v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\'\\:"|,.<>\/?]', v):
            raise ValueError("Password must contain at least one special character")
        return v

class RoomCreation(BaseModel):
    name: constr(min_length=3, max_length=50) = Field(..., description="Room name")
    game_type: str = Field(..., description="Game type")
    min_bet: Decimal = Field(..., description="Minimum bet amount")
    max_bet: Decimal = Field(..., description="Maximum bet amount")
    max_players: int = Field(..., description="Maximum number of players")
    is_private: bool = Field(False, description="Whether the room is private")
    password: Optional[str] = Field(None, description="Room password for private rooms")
    
    _validate_amount = validator('min_bet', 'max_bet', allow_reuse=True)(validate_amount)
    
    @validator('max_players')
    def validate_max_players(cls, v):
        if not 2 <= v <= 9:
            raise ValueError("Maximum players must be between 2 and 9")
        return v
    
    @validator('max_bet')
    def validate_max_bet(cls, v, values):
        if 'min_bet' in values and v <= values['min_bet']:
            raise ValueError("Maximum bet must be greater than minimum bet")
        return v
    
    @validator('password')
    def validate_password(cls, v, values):
        if values.get('is_private') and not v:
            raise ValueError("Password is required for private rooms")
        if v and len(v) < 4:
            raise ValueError("Room password must be at least 4 characters long")
        return v

class TransactionFilter(BaseModel):
    start_date: Optional[datetime] = Field(None, description="Start date for filtering")
    end_date: Optional[datetime] = Field(None, description="End date for filtering")
    transaction_type: Optional[str] = Field(None, description="Transaction type")
    status: Optional[str] = Field(None, description="Transaction status")
    min_amount: Optional[Decimal] = Field(None, description="Minimum amount")
    max_amount: Optional[Decimal] = Field(None, description="Maximum amount")
    
    _validate_amount = validator('min_amount', 'max_amount', allow_reuse=True)(validate_amount)
    
    @validator('end_date')
    def validate_dates(cls, v, values):
        if 'start_date' in values and v and values['start_date'] and v < values['start_date']:
            raise ValueError("End date must be after start date")
        return v
    
    @validator('transaction_type')
    def validate_transaction_type(cls, v):
        if v and v not in ['DEPOSIT', 'WITHDRAWAL', 'BET', 'WIN', 'REFUND']:
            raise ValueError("Invalid transaction type")
        return v
    
    @validator('status')
    def validate_status(cls, v):
        if v and v not in ['PENDING', 'COMPLETED', 'FAILED', 'CANCELLED']:
            raise ValueError("Invalid transaction status")
        return v 