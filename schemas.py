from marshmallow import Schema, fields, validate, ValidationError
from datetime import datetime
from models import UserRole

class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    email = fields.Email(required=True)
    telegram_id = fields.Str(required=True)
    role = fields.Str(validate=validate.OneOf([role.value for role in UserRole]))
    is_active = fields.Bool(dump_only=True)
    balance = fields.Decimal(dump_only=True)
    registered_at = fields.DateTime(dump_only=True)
    last_login = fields.DateTime(dump_only=True)

class UserRegistrationSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=50))
    password = fields.Str(required=True, validate=validate.Length(min=6))
    email = fields.Email(required=True)
    telegram_id = fields.Str(required=True)
    is_admin = fields.Bool(load_default=False)

class UserLoginSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)

class UserUpdateSchema(Schema):
    email = fields.Email()
    role = fields.Str(validate=validate.OneOf([role.value for role in UserRole]))
    is_active = fields.Bool()

class RoomSchema(Schema):
    id = fields.Int(dump_only=True)
    name = fields.Str(required=True, validate=validate.Length(min=3, max=100))
    created_by = fields.Int(required=True)
    created_at = fields.DateTime(dump_only=True)
    is_active = fields.Bool(dump_only=True)
    current_players = fields.Int(dump_only=True)
    max_players = fields.Int(required=True, validate=validate.Range(min=2, max=10))

class GameSchema(Schema):
    id = fields.Int(dump_only=True)
    room_id = fields.Int(required=True)
    created_at = fields.DateTime(dump_only=True)
    status = fields.Str(dump_only=True)
    current_round = fields.Int(dump_only=True)
    total_rounds = fields.Int(required=True, validate=validate.Range(min=1, max=100))
    min_bet = fields.Decimal(required=True, validate=validate.Range(min=0))
    max_bet = fields.Decimal(required=True, validate=validate.Range(min=0))

class GameHistorySchema(Schema):
    id = fields.Int(dump_only=True)
    game_id = fields.Int(required=True)
    user_id = fields.Int(required=True)
    bet_amount = fields.Decimal(required=True, validate=validate.Range(min=0))
    result = fields.Str(required=True)
    created_at = fields.DateTime(dump_only=True)

class WalletDepositSchema(Schema):
    amount = fields.Decimal(required=True, validate=validate.Range(min=0.01))

class ErrorSchema(Schema):
    message = fields.Str(required=True)
    errors = fields.Dict(keys=fields.Str(), values=fields.List(fields.Str()))

# Custom validators
def validate_password_strength(password):
    """Validate password strength."""
    if len(password) < 6:
        raise ValidationError('Password must be at least 6 characters long')
    if not any(c.isupper() for c in password):
        raise ValidationError('Password must contain at least one uppercase letter')
    if not any(c.islower() for c in password):
        raise ValidationError('Password must contain at least one lowercase letter')
    if not any(c.isdigit() for c in password):
        raise ValidationError('Password must contain at least one number')
    if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
        raise ValidationError('Password must contain at least one special character')

# Update UserRegistrationSchema with password strength validation
UserRegistrationSchema.password.validators.append(validate_password_strength) 