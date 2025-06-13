from marshmallow import Schema, fields
from datetime import datetime

class GameStatsSchema(Schema):
    total_games = fields.Int()
    active_games = fields.Int()
    total_bets = fields.Decimal()
    total_wins = fields.Decimal()
    average_bet = fields.Decimal()
    win_rate = fields.Decimal()
    popular_games = fields.List(fields.Dict())
    recent_games = fields.List(fields.Dict())

class UserStatsSchema(Schema):
    total_users = fields.Int()
    active_users = fields.Int()
    new_users_today = fields.Int()
    new_users_week = fields.Int()
    top_players = fields.List(fields.Dict())
    user_activity = fields.List(fields.Dict())

class TransactionLogSchema(Schema):
    id = fields.Int()
    user_id = fields.Int()
    username = fields.Str()
    transaction_type = fields.Str()
    amount = fields.Decimal()
    balance_before = fields.Decimal()
    balance_after = fields.Decimal()
    created_at = fields.DateTime()
    description = fields.Str()

class AdminDashboardSchema(Schema):
    game_stats = fields.Nested(GameStatsSchema)
    user_stats = fields.Nested(UserStatsSchema)
    recent_transactions = fields.List(fields.Nested(TransactionLogSchema))
    system_status = fields.Dict() 