from flask import Blueprint, jsonify, request
from models import User, Room, Game, GameHistory, UserRole
from schemas.admin import (
    GameStatsSchema, UserStatsSchema, TransactionLogSchema,
    AdminDashboardSchema
)
from datetime import datetime, timedelta
from sqlalchemy import func, desc
from functools import wraps
import jwt
import os

admin_bp = Blueprint('admin', __name__, url_prefix='/api/admin')

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        try:
            token = token.split(' ')[1]
            data = jwt.decode(token, os.getenv('JWT_SECRET_KEY', 'your-secret-key'), algorithms=["HS256"])
            user = User.query.get(data['user_id'])
            
            if not user or user.role != UserRole.ADMIN:
                return jsonify({'message': 'Admin access required!'}), 403
                
            return f(user, *args, **kwargs)
        except:
            return jsonify({'message': 'Invalid token!'}), 401
            
    return decorated

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def get_dashboard_stats(current_user):
    # Get game statistics
    game_stats = {
        'total_games': Game.query.count(),
        'active_games': Game.query.filter_by(status='active').count(),
        'total_bets': GameHistory.query.with_entities(
            func.sum(GameHistory.bet_amount)
        ).scalar() or 0,
        'total_wins': GameHistory.query.with_entities(
            func.sum(GameHistory.win_amount)
        ).scalar() or 0,
        'average_bet': GameHistory.query.with_entities(
            func.avg(GameHistory.bet_amount)
        ).scalar() or 0,
        'win_rate': GameHistory.query.filter(
            GameHistory.result == 'win'
        ).count() / max(GameHistory.query.count(), 1) * 100,
        'popular_games': Game.query.with_entities(
            Game.room_id,
            func.count(Game.id)
        ).group_by(Game.room_id).order_by(desc(func.count(Game.id))).limit(5).all(),
        'recent_games': Game.query.order_by(desc(Game.created_at)).limit(5).all()
    }
    
    # Get user statistics
    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    
    user_stats = {
        'total_users': User.query.count(),
        'active_users': User.query.filter_by(is_active=True).count(),
        'new_users_today': User.query.filter(
            func.date(User.registered_at) == today
        ).count(),
        'new_users_week': User.query.filter(
            func.date(User.registered_at) >= week_ago
        ).count(),
        'top_players': User.query.order_by(desc(User.balance)).limit(5).all(),
        'user_activity': User.query.order_by(desc(User.last_login)).limit(5).all()
    }
    
    # Get recent transactions
    recent_transactions = GameHistory.query.order_by(
        desc(GameHistory.created_at)
    ).limit(10).all()
    
    # Get system status
    system_status = {
        'total_rooms': Room.query.count(),
        'active_rooms': Room.query.filter_by(is_active=True).count(),
        'total_transactions': GameHistory.query.count(),
        'server_time': datetime.utcnow().isoformat()
    }
    
    # Combine all data
    dashboard_data = {
        'game_stats': game_stats,
        'user_stats': user_stats,
        'recent_transactions': recent_transactions,
        'system_status': system_status
    }
    
    return jsonify(AdminDashboardSchema().dump(dashboard_data))

@admin_bp.route('/users', methods=['GET'])
@admin_required
def get_users(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    users = User.query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'users': [{
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role.value,
            'is_active': user.is_active,
            'balance': float(user.balance),
            'registered_at': user.registered_at.isoformat(),
            'last_login': user.last_login.isoformat() if user.last_login else None
        } for user in users.items],
        'total': users.total,
        'pages': users.pages,
        'current_page': users.page
    })

@admin_bp.route('/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user(current_user, user_id):
    user = User.query.get_or_404(user_id)
    data = request.get_json()
    
    if 'role' in data:
        try:
            user.role = UserRole(data['role'])
        except ValueError:
            return jsonify({'message': 'Invalid role!'}), 400
    
    if 'is_active' in data:
        user.is_active = data['is_active']
    
    if 'email' in data:
        if User.query.filter_by(email=data['email']).first():
            return jsonify({'message': 'Email already exists!'}), 400
        user.email = data['email']
    
    db.session.commit()
    return jsonify({'message': 'User updated successfully!'})

@admin_bp.route('/transactions', methods=['GET'])
@admin_required
def get_transactions(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    transactions = GameHistory.query.order_by(
        desc(GameHistory.created_at)
    ).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'transactions': [{
            'id': t.id,
            'user_id': t.user_id,
            'username': t.user.username,
            'game_id': t.game_id,
            'bet_amount': float(t.bet_amount),
            'win_amount': float(t.win_amount),
            'result': t.result,
            'created_at': t.created_at.isoformat()
        } for t in transactions.items],
        'total': transactions.total,
        'pages': transactions.pages,
        'current_page': transactions.page
    })

@admin_bp.route('/games', methods=['GET'])
@admin_required
def get_games(current_user):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    games = Game.query.order_by(
        desc(Game.created_at)
    ).paginate(page=page, per_page=per_page)
    
    return jsonify({
        'games': [{
            'id': game.id,
            'room_id': game.room_id,
            'status': game.status,
            'total_rounds': game.total_rounds,
            'current_round': game.current_round,
            'min_bet': float(game.min_bet),
            'max_bet': float(game.max_bet),
            'created_at': game.created_at.isoformat(),
            'ended_at': game.ended_at.isoformat() if game.ended_at else None
        } for game in games.items],
        'total': games.total,
        'pages': games.pages,
        'current_page': games.page
    }) 