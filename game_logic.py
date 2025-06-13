from typing import List, Dict, Any, Optional, Tuple
from models import Game, GameHistory, User, db
from datetime import datetime
import random
from poker_logic import poker_hand
from cooldown_manager import cooldown_manager
from balance_manager import balance_manager

class GameState:
    WAITING = 'waiting'
    STARTING = 'starting'
    IN_PROGRESS = 'in_progress'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'

class Round:
    PREFLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3
    SHOWDOWN = 4

    @staticmethod
    def get_name(round_num: int) -> str:
        return {
            Round.PREFLOP: 'Pre-Flop',
            Round.FLOP: 'Flop',
            Round.TURN: 'Turn',
            Round.RIVER: 'River',
            Round.SHOWDOWN: 'Showdown'
        }[round_num]

    @staticmethod
    def get_cards_to_deal(round_num: int) -> int:
        return {
            Round.PREFLOP: 0,  # Hole cards already dealt
            Round.FLOP: 3,
            Round.TURN: 1,
            Round.RIVER: 1,
            Round.SHOWDOWN: 0
        }[round_num]

class GameLogic:
    def __init__(self):
        self.valid_actions = ['bet', 'fold', 'check', 'call', 'raise']
        self.card_values = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8,
            '9': 9, '10': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14
        }
        self.card_suits = ['♠', '♥', '♦', '♣']

    def validate_move(self, game: Game, user_id: int, action: str, amount: float = 0) -> Tuple[bool, str]:
        """
        Validate a player's move
        Returns: (is_valid, error_message)
        """
        # Check if game exists and is active
        if not game or game.status != 'active':
            return False, "Game is not active"

        # Check if it's the player's turn
        if game.current_player_id != user_id:
            return False, "Not your turn"

        # Check if action is valid
        if action not in self.valid_actions:
            return False, f"Invalid action. Valid actions are: {', '.join(self.valid_actions)}"

        # Get player's current bet
        player_bet = game.player_bets.get(str(user_id), 0)
        current_bet = max(game.player_bets.values()) if game.player_bets else 0

        # Validate specific actions
        if action == 'bet':
            if amount < game.min_bet:
                return False, f"Minimum bet is {game.min_bet}"
            if amount > game.max_bet:
                return False, f"Maximum bet is {game.max_bet}"
            if amount > game.players[user_id].balance:
                return False, "Insufficient balance"

        elif action == 'raise':
            if amount <= current_bet:
                return False, f"Raise must be greater than current bet of {current_bet}"
            if amount > game.max_bet:
                return False, f"Maximum bet is {game.max_bet}"
            if amount > game.players[user_id].balance:
                return False, "Insufficient balance"

        elif action == 'call':
            if current_bet > game.players[user_id].balance:
                return False, "Insufficient balance to call"

        return True, ""

    def submit_move(self, game: Game, user_id: int, action: str, amount: float = 0) -> Dict[str, Any]:
        """
        Submit and process a player's move
        Returns: Dict containing move result and updated game state
        """
        # Validate move
        is_valid, error_message = self.validate_move(game, user_id, action, amount)
        if not is_valid:
            return {
                'success': False,
                'error': error_message
            }

        player = game.players[user_id]
        current_bet = max(game.player_bets.values()) if game.player_bets else 0

        # Process move
        if action == 'bet':
            player.balance -= amount
            game.pot += amount
            game.player_bets[str(user_id)] = amount

        elif action == 'raise':
            player.balance -= amount
            game.pot += amount
            game.player_bets[str(user_id)] = amount

        elif action == 'call':
            call_amount = current_bet - game.player_bets.get(str(user_id), 0)
            player.balance -= call_amount
            game.pot += call_amount
            game.player_bets[str(user_id)] = current_bet

        elif action == 'check':
            # No action needed for check
            pass

        elif action == 'fold':
            game.folded_players.add(user_id)

        # Update game state
        game.last_action = {
            'player_id': user_id,
            'action': action,
            'amount': amount,
            'timestamp': datetime.utcnow()
        }

        # Move to next player
        self._advance_to_next_player(game)

        # Check if round is complete
        if self._is_round_complete(game):
            self._end_round(game)

        # Save changes
        db.session.commit()

        return {
            'success': True,
            'game_state': {
                'pot': game.pot,
                'current_player': game.current_player_id,
                'player_bets': game.player_bets,
                'folded_players': list(game.folded_players),
                'last_action': game.last_action
            }
        }

    def _advance_to_next_player(self, game: Game) -> None:
        """Advance to the next active player"""
        active_players = [p for p in game.players if p not in game.folded_players]
        if not active_players:
            return

        current_index = active_players.index(game.current_player_id)
        next_index = (current_index + 1) % len(active_players)
        game.current_player_id = active_players[next_index]

    def _is_round_complete(self, game: Game) -> bool:
        """Check if the current round is complete"""
        active_players = [p for p in game.players if p not in game.folded_players]
        if not active_players:
            return True

        # Round is complete if all active players have bet the same amount
        target_bet = max(game.player_bets.values()) if game.player_bets else 0
        return all(
            game.player_bets.get(str(p), 0) == target_bet
            for p in active_players
        )

    def _end_round(self, game: Game) -> None:
        """End the current round and start the next one"""
        # If only one player remains, they win
        active_players = [p for p in game.players if p not in game.folded_players]
        if len(active_players) == 1:
            self._end_game(game, active_players[0])
            return

        # Deal next community cards
        if game.current_round == 1:
            # Deal flop (3 cards)
            game.community_cards.extend(self._deal_cards(3))
        elif game.current_round == 2:
            # Deal turn (1 card)
            game.community_cards.extend(self._deal_cards(1))
        elif game.current_round == 3:
            # Deal river (1 card)
            game.community_cards.extend(self._deal_cards(1))
        elif game.current_round == 4:
            # Showdown
            winner = self._determine_winner(game)
            self._end_game(game, winner)

        # Reset player bets for next round
        game.player_bets = {}
        game.current_round += 1

    def _end_game(self, game: Game, winner_id: int) -> None:
        """End the game and distribute winnings"""
        winner = game.players[winner_id]
        winner.balance += game.pot

        # Record game history
        game.status = 'completed'
        game.winner_id = winner_id
        game.end_time = datetime.utcnow()

        # Save changes
        db.session.commit()

    def _determine_winner(self, game: Game) -> int:
        """Determine the winner based on poker hand rankings"""
        active_players = [p for p in game.players if p not in game.folded_players]
        if len(active_players) == 1:
            return active_players[0]

        # Evaluate each player's hand
        best_hand = None
        winner = None

        for player_id in active_players:
            player_cards = game.player_cards[player_id]
            all_cards = player_cards + game.community_cards
            hand_value = self._evaluate_hand(all_cards)

            if best_hand is None or hand_value > best_hand:
                best_hand = hand_value
                winner = player_id

        return winner

    def _evaluate_hand(self, cards: List[str]) -> int:
        """
        Evaluate a poker hand and return its value
        Returns: Integer representing hand strength (higher is better)
        """
        # Sort cards by value
        sorted_cards = sorted(cards, key=lambda x: self.card_values[x[:-1]], reverse=True)
        
        # Check for straight flush
        if self._is_straight_flush(sorted_cards):
            return 8000 + self.card_values[sorted_cards[0][:-1]]
            
        # Check for four of a kind
        if self._is_four_of_a_kind(sorted_cards):
            return 7000 + self.card_values[sorted_cards[0][:-1]]
            
        # Check for full house
        if self._is_full_house(sorted_cards):
            return 6000 + self.card_values[sorted_cards[0][:-1]]
            
        # Check for flush
        if self._is_flush(sorted_cards):
            return 5000 + self.card_values[sorted_cards[0][:-1]]
            
        # Check for straight
        if self._is_straight(sorted_cards):
            return 4000 + self.card_values[sorted_cards[0][:-1]]
            
        # Check for three of a kind
        if self._is_three_of_a_kind(sorted_cards):
            return 3000 + self.card_values[sorted_cards[0][:-1]]
            
        # Check for two pair
        if self._is_two_pair(sorted_cards):
            return 2000 + self.card_values[sorted_cards[0][:-1]]
            
        # Check for one pair
        if self._is_one_pair(sorted_cards):
            return 1000 + self.card_values[sorted_cards[0][:-1]]
            
        # High card
        return self.card_values[sorted_cards[0][:-1]]

    def _is_straight_flush(self, cards: List[str]) -> bool:
        """Check for straight flush"""
        return self._is_flush(cards) and self._is_straight(cards)

    def _is_four_of_a_kind(self, cards: List[str]) -> bool:
        """Check for four of a kind"""
        values = [c[:-1] for c in cards]
        return any(values.count(v) >= 4 for v in set(values))

    def _is_full_house(self, cards: List[str]) -> bool:
        """Check for full house"""
        values = [c[:-1] for c in cards]
        return any(values.count(v) == 3 for v in set(values)) and any(values.count(v) == 2 for v in set(values))

    def _is_flush(self, cards: List[str]) -> bool:
        """Check for flush"""
        suits = [c[-1] for c in cards]
        return any(suits.count(s) >= 5 for s in set(suits))

    def _is_straight(self, cards: List[str]) -> bool:
        """Check for straight"""
        values = sorted(set(self.card_values[c[:-1]] for c in cards))
        for i in range(len(values) - 4):
            if values[i:i+5] == list(range(values[i], values[i]+5)):
                return True
        return False

    def _is_three_of_a_kind(self, cards: List[str]) -> bool:
        """Check for three of a kind"""
        values = [c[:-1] for c in cards]
        return any(values.count(v) >= 3 for v in set(values))

    def _is_two_pair(self, cards: List[str]) -> bool:
        """Check for two pair"""
        values = [c[:-1] for c in cards]
        pairs = [v for v in set(values) if values.count(v) >= 2]
        return len(pairs) >= 2

    def _is_one_pair(self, cards: List[str]) -> bool:
        """Check for one pair"""
        values = [c[:-1] for c in cards]
        return any(values.count(v) >= 2 for v in set(values))

    def _deal_cards(self, num_cards: int) -> List[str]:
        """Deal a specified number of cards"""
        deck = [f"{value}{suit}" for suit in self.card_suits for value in self.card_values.keys()]
        random.shuffle(deck)
        return deck[:num_cards]

def determine_winners(game: Game) -> List[Tuple[int, str]]:
    """
    Determine the winner(s) of the game
    Returns: List of (player_id, hand_description) tuples
    """
    # Get all active players and their hole cards
    active_players = {
        player_id: game.player_cards[player_id]
        for player_id in game.player_cards
        if game.player_status[player_id] == 'active'
    }

    if not active_players:
        return []

    # Get community cards
    community_cards = game.community_cards

    # Determine winners
    winners = poker_hand.determine_winners(active_players, community_cards)

    # Format winner information
    winner_info = []
    for player_id, (ranking, kickers) in winners:
        hand_description = poker_hand.get_hand_description(ranking, kickers)
        winner_info.append((player_id, hand_description))

    return winner_info

def end_round(game: Game) -> Dict:
    """End the current round and determine winners"""
    if game.status != GameState.IN_PROGRESS:
        return {'error': 'Game is not in progress'}

    # Get all active players
    active_players = [p for p in game.players if game.player_status.get(p) != 'folded']
    
    if len(active_players) <= 1:
        # Only one player left, they win
        winner_id = active_players[0]
        result = balance_manager.handle_win(game.id, winner_id, game.pot)
        if not result['success']:
            return {'error': result['message']}
            
        game.status = GameState.COMPLETED
        game.current_player = None
        db.session.commit()
        
        return {
            'status': 'completed',
            'winners': [{
                'player_id': winner_id,
                'hand': None,
                'amount': game.pot,
                'success': True,
                'message': 'Won by default (all others folded)'
            }],
            'pot': game.pot
        }
    
    # Evaluate hands for all active players
    hands = {p: game.player_cards[p] for p in active_players}
    winners = poker_hand.evaluate_hands(hands, game.community_cards)
    
    if not winners:
        return {'error': 'Could not determine winners'}
    
    # Calculate split amount
    split_amount = game.pot / len(winners)
    
    # Distribute winnings
    winner_results = []
    for winner in winners:
        result = balance_manager.handle_win(game.id, winner['player_id'], split_amount)
        winner_results.append({
            'player_id': winner['player_id'],
            'hand': winner['hand'],
            'amount': split_amount,
            'success': result['success'],
            'message': result['message']
        })
    
    # Update game state
    game.status = GameState.COMPLETED
    game.current_player = None
    db.session.commit()
    
    return {
        'status': 'completed',
        'winners': winner_results,
        'pot': game.pot
    }

def initialize_game(game: Game) -> Dict[str, Any]:
    """Initialize a new game"""
    if game.status != GameState.WAITING:
        return {'error': 'Game is not in waiting state'}

    # Check cooldowns for all players
    for player_id in game.players:
        if cooldown_manager.is_on_cooldown(game.id, player_id):
            remaining = cooldown_manager.get_cooldown_remaining(game.id, player_id)
            return {
                'error': f'Player {player_id} is on cooldown for {remaining.seconds} seconds'
            }

    # Set up initial game state
    game.status = GameState.STARTING
    game.round = Round.PREFLOP
    game.pot = 0
    game.current_player = None
    game.player_bets = {}
    game.player_status = {}
    game.community_cards = []
    game.deck = create_deck()
    game.player_cards = {}

    # Deal hole cards to players
    for player_id in game.players:
        game.player_cards[player_id] = deal_cards(game.deck, 2)
        game.player_status[player_id] = 'active'
        game.player_bets[player_id] = 0

    # Set first player (small blind)
    game.current_player = game.players[0]

    # Post blinds
    post_blinds(game)

    # Update game status
    game.status = GameState.IN_PROGRESS
    game.started_at = datetime.utcnow()

    # Save changes
    db.session.commit()

    return {
        'status': game.status,
        'round': Round.get_name(game.round),
        'current_player': game.current_player,
        'pot': game.pot,
        'player_bets': game.player_bets,
        'player_status': game.player_status
    }

def post_blinds(game: Game) -> None:
    """Post small and big blinds"""
    if len(game.players) < 2:
        return

    # Small blind (first player)
    small_blind_player = game.players[0]
    small_blind_amount = Decimal(str(game.min_bet)) / Decimal('2')
    success, message = balance_manager.handle_blind(
        user_id=small_blind_player,
        game_id=game.id,
        amount=small_blind_amount,
        blind_type='Small'
    )
    if success:
        game.player_bets[small_blind_player] = float(small_blind_amount)
        game.pot += float(small_blind_amount)

    # Big blind (second player)
    big_blind_player = game.players[1]
    big_blind_amount = Decimal(str(game.min_bet))
    success, message = balance_manager.handle_blind(
        user_id=big_blind_player,
        game_id=game.id,
        amount=big_blind_amount,
        blind_type='Big'
    )
    if success:
        game.player_bets[big_blind_player] = float(big_blind_amount)
        game.pot += float(big_blind_amount)

def advance_round(game: Game) -> Dict[str, Any]:
    """Advance to the next round"""
    if game.status != GameState.IN_PROGRESS:
        return {'error': 'Game is not in progress'}

    # Check if all players have acted and bets are equal
    active_players = [p for p in game.player_status if game.player_status[p] == 'active']
    if not all(game.player_bets[p] == max(game.player_bets.values()) for p in active_players):
        return {'error': 'Not all players have acted'}

    # Advance to next round
    game.round += 1

    # Deal community cards based on round
    cards_to_deal = Round.get_cards_to_deal(game.round)
    if cards_to_deal > 0:
        new_cards = deal_cards(game.deck, cards_to_deal)
        game.community_cards.extend(new_cards)

    # Reset player bets for new round
    for player_id in active_players:
        game.player_bets[player_id] = 0

    # Set first player for new round (player after dealer)
    game.current_player = active_players[0]

    # Check if game should end
    if game.round == Round.SHOWDOWN:
        return end_round(game)

    # Save changes
    db.session.commit()

    return {
        'status': game.status,
        'round': Round.get_name(game.round),
        'current_player': game.current_player,
        'community_cards': game.community_cards,
        'pot': game.pot,
        'player_bets': game.player_bets
    }

def submit_move(game: Game, user_id: int, action: str, amount: Optional[float] = None) -> Dict[str, Any]:
    """Submit a move in the game"""
    if game.status != GameState.IN_PROGRESS:
        return {'error': 'Game is not in progress'}

    if user_id != game.current_player:
        return {'error': 'Not your turn'}

    if game.player_status[user_id] != 'active':
        return {'error': 'Player is not active'}

    # Check action cooldown
    if cooldown_manager.is_on_cooldown(game.id, user_id):
        remaining = cooldown_manager.get_cooldown_remaining(game.id, user_id)
        return {'error': f'Action cooldown: {remaining.seconds} seconds remaining'}

    # Handle the move
    if action == 'fold':
        game.player_status[user_id] = 'folded'
        result = {'status': 'folded'}
    elif action == 'check':
        if max(game.player_bets.values()) > game.player_bets[user_id]:
            return {'error': 'Cannot check, must call or fold'}
        result = {'status': 'checked'}
    elif action in ['bet', 'raise', 'call']:
        # Calculate bet amount
        if action == 'call':
            amount = max(game.player_bets.values()) - game.player_bets[user_id]
        elif action == 'raise':
            if amount < game.min_bet or amount > game.max_bet:
                return {'error': 'Invalid bet amount'}

        # Handle bet
        success, message = balance_manager.handle_bet(
            user_id=user_id,
            game_id=game.id,
            amount=Decimal(str(amount))
        )
        if not success:
            return {'error': message}

        # Update game state
        game.player_bets[user_id] = game.player_bets.get(user_id, 0) + amount
        game.pot += amount

        result = {
            'status': action,
            'amount': amount,
            'new_balance': balance_manager.get_user_balance(user_id)
        }

    # Start action cooldown
    cooldown_manager.start_action_cooldown(game.id, user_id, action)

    # Check if round should end
    active_players = [p for p in game.player_status if game.player_status[p] == 'active']
    if len(active_players) <= 1:
        # End the game
        end_result = end_round(game)
        result.update(end_result)
        # Handle game end cooldowns
        cooldown_manager.handle_game_end(game)
    else:
        # Move to next player
        current_index = active_players.index(user_id)
        next_index = (current_index + 1) % len(active_players)
        game.current_player = active_players[next_index]

        # Check if round should end
        if all(game.player_bets[p] == max(game.player_bets.values()) for p in active_players):
            round_result = advance_round(game)
            result.update(round_result)

    # Save changes
    db.session.commit()

    return result

def cancel_game(game: Game) -> Dict[str, Any]:
    """Cancel the game and refund players"""
    if game.status not in [GameState.WAITING, GameState.STARTING]:
        return {'error': 'Cannot cancel game in progress'}

    # Refund all bets
    refund_results = balance_manager.refund_game(game)

    # Update game status
    game.status = GameState.CANCELLED
    game.ended_at = datetime.utcnow()
    game.pot = 0

    # Clear all cooldowns for this game
    cooldown_manager.clear_game_cooldowns(game.id)

    # Save changes
    db.session.commit()

    return {
        'status': game.status,
        'message': 'Game cancelled and players refunded',
        'refunds': refund_results
    }

# Initialize game logic
game_logic = GameLogic() 