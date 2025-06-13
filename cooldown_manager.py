from typing import Dict, Optional
from datetime import datetime, timedelta
from models import Game, User, db

class CooldownManager:
    def __init__(self):
        self.cooldowns: Dict[int, Dict[int, datetime]] = {}  # game_id -> {user_id -> cooldown_end}
        self.DEFAULT_COOLDOWN = timedelta(minutes=5)  # 5 minutes default cooldown
        self.ACTION_COOLDOWNS = {
            'bet': timedelta(seconds=30),
            'raise': timedelta(seconds=30),
            'call': timedelta(seconds=30),
            'check': timedelta(seconds=15),
            'fold': timedelta(seconds=15)
        }

    def start_game_cooldown(self, game_id: int, user_id: int) -> None:
        """Start cooldown for a user after a game ends"""
        if game_id not in self.cooldowns:
            self.cooldowns[game_id] = {}
        
        self.cooldowns[game_id][user_id] = datetime.utcnow() + self.DEFAULT_COOLDOWN

    def start_action_cooldown(self, game_id: int, user_id: int, action: str) -> None:
        """Start cooldown for a specific action"""
        if game_id not in self.cooldowns:
            self.cooldowns[game_id] = {}
        
        cooldown_time = self.ACTION_COOLDOWNS.get(action, self.DEFAULT_COOLDOWN)
        self.cooldowns[game_id][user_id] = datetime.utcnow() + cooldown_time

    def is_on_cooldown(self, game_id: int, user_id: int) -> bool:
        """Check if a user is on cooldown for a game"""
        if game_id not in self.cooldowns:
            return False
        
        if user_id not in self.cooldowns[game_id]:
            return False
        
        return datetime.utcnow() < self.cooldowns[game_id][user_id]

    def get_cooldown_remaining(self, game_id: int, user_id: int) -> Optional[timedelta]:
        """Get remaining cooldown time for a user"""
        if not self.is_on_cooldown(game_id, user_id):
            return None
        
        return self.cooldowns[game_id][user_id] - datetime.utcnow()

    def clear_cooldown(self, game_id: int, user_id: int) -> None:
        """Clear cooldown for a user"""
        if game_id in self.cooldowns and user_id in self.cooldowns[game_id]:
            del self.cooldowns[game_id][user_id]

    def clear_game_cooldowns(self, game_id: int) -> None:
        """Clear all cooldowns for a game"""
        if game_id in self.cooldowns:
            del self.cooldowns[game_id]

    def handle_game_end(self, game: Game) -> None:
        """Handle cooldowns when a game ends"""
        # Start cooldown for all players
        for player_id in game.players:
            self.start_game_cooldown(game.id, player_id)
            
            # Update user's last game time
            user = User.query.get(player_id)
            if user:
                user.last_game_time = datetime.utcnow()
                db.session.commit()

    def handle_player_leave(self, game: Game, user_id: int) -> None:
        """Handle cooldown when a player leaves a game"""
        if game.status == 'in_progress':
            # If player leaves during game, apply longer cooldown
            self.start_game_cooldown(game.id, user_id)
        else:
            # If player leaves before game starts, clear cooldown
            self.clear_cooldown(game.id, user_id)

# Initialize cooldown manager
cooldown_manager = CooldownManager() 