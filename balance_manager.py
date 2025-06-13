from typing import Dict, List, Tuple, Optional
from datetime import datetime
from decimal import Decimal
from models import User, Game, GameHistory, db
from sqlalchemy.exc import SQLAlchemyError

class BalanceManager:
    def __init__(self):
        self.MIN_BALANCE = Decimal('0.00')
        self.MAX_BALANCE = Decimal('1000000.00')  # $1M max balance
        self.MIN_BET = Decimal('1.00')
        self.MAX_BET = Decimal('10000.00')

    def validate_balance(self, amount: Decimal) -> bool:
        """Validate if a balance amount is within allowed limits"""
        return self.MIN_BALANCE <= amount <= self.MAX_BALANCE

    def validate_bet(self, amount: Decimal) -> bool:
        """Validate if a bet amount is within allowed limits"""
        return self.MIN_BET <= amount <= self.MAX_BET

    def get_user_balance(self, user_id: int) -> Optional[Decimal]:
        """Get current balance for a user"""
        user = User.query.get(user_id)
        return Decimal(str(user.balance)) if user else None

    def update_balance(self, user_id: int, amount: Decimal, 
                      game_id: int, action: str, description: str) -> Tuple[bool, str]:
        """
        Update user balance and create transaction log
        Returns: (success, message)
        """
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"

            current_balance = Decimal(str(user.balance))
            new_balance = current_balance + amount

            # Validate new balance
            if not self.validate_balance(new_balance):
                return False, f"Balance would exceed limits: {new_balance}"

            # Update balance
            user.balance = float(new_balance)

            # Create transaction log
            history = GameHistory(
                game_id=game_id,
                user_id=user_id,
                action=action,
                amount=float(amount),
                balance_before=float(current_balance),
                balance_after=float(new_balance),
                description=description
            )
            db.session.add(history)
            db.session.commit()

            return True, f"Balance updated: {new_balance}"

        except SQLAlchemyError as e:
            db.session.rollback()
            return False, f"Database error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating balance: {str(e)}"

    def handle_bet(self, user_id: int, game_id: int, amount: Decimal) -> Tuple[bool, str]:
        """Handle a bet action"""
        if not self.validate_bet(amount):
            return False, f"Invalid bet amount: {amount}"

        current_balance = self.get_user_balance(user_id)
        if current_balance is None:
            return False, "User not found"

        if current_balance < amount:
            return False, f"Insufficient balance: {current_balance}"

        return self.update_balance(
            user_id=user_id,
            amount=-amount,  # Negative amount for bet
            game_id=game_id,
            action='bet',
            description=f"Bet of {amount}"
        )

    def handle_win(self, user_id: int, game_id: int, amount: Decimal, 
                  hand_description: str) -> Tuple[bool, str]:
        """Handle a win action"""
        return self.update_balance(
            user_id=user_id,
            amount=amount,  # Positive amount for win
            game_id=game_id,
            action='win',
            description=f"Won {amount} with {hand_description}"
        )

    def handle_refund(self, user_id: int, game_id: int, amount: Decimal, 
                     reason: str) -> Tuple[bool, str]:
        """Handle a refund action"""
        return self.update_balance(
            user_id=user_id,
            amount=amount,  # Positive amount for refund
            game_id=game_id,
            action='refund',
            description=f"Refund of {amount}: {reason}"
        )

    def handle_blind(self, user_id: int, game_id: int, amount: Decimal, 
                    blind_type: str) -> Tuple[bool, str]:
        """Handle posting blinds"""
        return self.update_balance(
            user_id=user_id,
            amount=-amount,  # Negative amount for blind
            game_id=game_id,
            action='blind',
            description=f"{blind_type} blind of {amount}"
        )

    def distribute_pot(self, game: Game, winners: List[Tuple[int, str]]) -> List[Dict]:
        """
        Distribute pot among winners
        Returns: List of distribution results
        """
        if not winners:
            return []

        pot = Decimal(str(game.pot))
        num_winners = len(winners)
        pot_per_winner = pot // num_winners
        remainder = pot % num_winners

        distribution_results = []
        for i, (player_id, hand_description) in enumerate(winners):
            # Add remainder to first winner(s)
            amount = pot_per_winner + (Decimal('1.00') if i < remainder else Decimal('0.00'))
            
            success, message = self.handle_win(
                user_id=player_id,
                game_id=game.id,
                amount=amount,
                hand_description=hand_description
            )

            distribution_results.append({
                'player_id': player_id,
                'amount': float(amount),
                'hand': hand_description,
                'success': success,
                'message': message
            })

        return distribution_results

    def refund_game(self, game: Game) -> List[Dict]:
        """Refund all bets in a game"""
        refund_results = []
        for player_id, bet_amount in game.player_bets.items():
            amount = Decimal(str(bet_amount))
            if amount > 0:
                success, message = self.handle_refund(
                    user_id=player_id,
                    game_id=game.id,
                    amount=amount,
                    reason="Game cancelled"
                )
                refund_results.append({
                    'player_id': player_id,
                    'amount': float(amount),
                    'success': success,
                    'message': message
                })
        return refund_results

# Initialize balance manager
balance_manager = BalanceManager() 