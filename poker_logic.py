from typing import List, Dict, Any, Tuple, Set, Optional
from collections import Counter
from itertools import combinations
from dataclasses import dataclass
from enum import Enum
import random

class HandRank(Enum):
    HIGH_CARD = 1
    PAIR = 2
    TWO_PAIR = 3
    THREE_OF_A_KIND = 4
    STRAIGHT = 5
    FLUSH = 6
    FULL_HOUSE = 7
    FOUR_OF_A_KIND = 8
    STRAIGHT_FLUSH = 9
    ROYAL_FLUSH = 10

@dataclass
class Card:
    suit: str
    value: int

    def __str__(self):
        values = {11: 'J', 12: 'Q', 13: 'K', 14: 'A'}
        value_str = values.get(self.value, str(self.value))
        return f"{value_str}{self.suit}"

class PokerHand:
    def __init__(self, cards: List[Card]):
        self.cards = sorted(cards, key=lambda x: x.value, reverse=True)
        self.rank, self.kickers = self._evaluate_hand()

    def _evaluate_hand(self) -> Tuple[HandRank, List[int]]:
        # Check for flush
        is_flush = len(set(card.suit for card in self.cards)) == 1
        
        # Check for straight
        values = [card.value for card in self.cards]
        is_straight = (
            len(set(values)) == 5 and
            max(values) - min(values) == 4
        )
        
        # Check for royal flush
        if is_flush and is_straight and max(values) == 14:
            return HandRank.ROYAL_FLUSH, [14]
            
        # Check for straight flush
        if is_flush and is_straight:
            return HandRank.STRAIGHT_FLUSH, [max(values)]
            
        # Count card values
        value_counts = {}
        for card in self.cards:
            value_counts[card.value] = value_counts.get(card.value, 0) + 1
            
        # Sort by count (descending) and then by value (descending)
        sorted_counts = sorted(
            value_counts.items(),
            key=lambda x: (x[1], x[0]),
            reverse=True
        )
        
        # Check for four of a kind
        if sorted_counts[0][1] == 4:
            kickers = [sorted_counts[0][0]]
            kickers.extend([v for v, _ in sorted_counts[1:]])
            return HandRank.FOUR_OF_A_KIND, kickers
            
        # Check for full house
        if sorted_counts[0][1] == 3 and sorted_counts[1][1] == 2:
            return HandRank.FULL_HOUSE, [sorted_counts[0][0], sorted_counts[1][0]]
            
        # Check for flush
        if is_flush:
            return HandRank.FLUSH, [card.value for card in self.cards]
            
        # Check for straight
        if is_straight:
            return HandRank.STRAIGHT, [max(values)]
            
        # Check for three of a kind
        if sorted_counts[0][1] == 3:
            kickers = [sorted_counts[0][0]]
            kickers.extend([v for v, _ in sorted_counts[1:3]])
            return HandRank.THREE_OF_A_KIND, kickers
            
        # Check for two pair
        if sorted_counts[0][1] == 2 and sorted_counts[1][1] == 2:
            kickers = [sorted_counts[0][0], sorted_counts[1][0]]
            kickers.append(sorted_counts[2][0])
            return HandRank.TWO_PAIR, kickers
            
        # Check for pair
        if sorted_counts[0][1] == 2:
            kickers = [sorted_counts[0][0]]
            kickers.extend([v for v, _ in sorted_counts[1:4]])
            return HandRank.PAIR, kickers
            
        # High card
        return HandRank.HIGH_CARD, [card.value for card in self.cards]

    def __lt__(self, other: 'PokerHand') -> bool:
        if self.rank.value != other.rank.value:
            return self.rank.value < other.rank.value
            
        # Compare kickers for same rank
        for k1, k2 in zip(self.kickers, other.kickers):
            if k1 != k2:
                return k1 < k2
        return False

    def __eq__(self, other: 'PokerHand') -> bool:
        if self.rank.value != other.rank.value:
            return False
            
        # Compare kickers for same rank
        for k1, k2 in zip(self.kickers, other.kickers):
            if k1 != k2:
                return False
        return True

    def __str__(self):
        rank_names = {
            HandRank.HIGH_CARD: "High Card",
            HandRank.PAIR: "Pair",
            HandRank.TWO_PAIR: "Two Pair",
            HandRank.THREE_OF_A_KIND: "Three of a Kind",
            HandRank.STRAIGHT: "Straight",
            HandRank.FLUSH: "Flush",
            HandRank.FULL_HOUSE: "Full House",
            HandRank.FOUR_OF_A_KIND: "Four of a Kind",
            HandRank.STRAIGHT_FLUSH: "Straight Flush",
            HandRank.ROYAL_FLUSH: "Royal Flush"
        }
        return f"{rank_names[self.rank]} ({', '.join(str(card) for card in self.cards)})"

def evaluate_hands(hands: Dict[int, List[Card]], community_cards: List[Card]) -> List[Dict]:
    """
    Evaluate all hands and return winners with their hand information.
    Handles ties by splitting the pot among winners.
    """
    evaluated_hands = []
    
    # Evaluate each player's hand
    for player_id, hole_cards in hands.items():
        all_cards = hole_cards + community_cards
        hand = PokerHand(all_cards)
        evaluated_hands.append({
            'player_id': player_id,
            'hand': hand,
            'hole_cards': hole_cards,
            'community_cards': community_cards
        })
    
    # Sort hands by rank (descending)
    evaluated_hands.sort(key=lambda x: x['hand'], reverse=True)
    
    # Find winners (players with the same highest hand)
    winners = []
    best_hand = evaluated_hands[0]['hand']
    
    for hand_info in evaluated_hands:
        if hand_info['hand'] == best_hand:
            winners.append({
                'player_id': hand_info['player_id'],
                'hand': hand_info['hand'],
                'hole_cards': hand_info['hole_cards'],
                'community_cards': hand_info['community_cards']
            })
    
    return winners

def get_hand_description(hand: PokerHand) -> str:
    """Get a human-readable description of the hand"""
    rank_names = {
        HandRank.HIGH_CARD: "High Card",
        HandRank.PAIR: "Pair",
        HandRank.TWO_PAIR: "Two Pair",
        HandRank.THREE_OF_A_KIND: "Three of a Kind",
        HandRank.STRAIGHT: "Straight",
        HandRank.FLUSH: "Flush",
        HandRank.FULL_HOUSE: "Full House",
        HandRank.FOUR_OF_A_KIND: "Four of a Kind",
        HandRank.STRAIGHT_FLUSH: "Straight Flush",
        HandRank.ROYAL_FLUSH: "Royal Flush"
    }
    
    return rank_names[hand.rank]

def format_cards(cards: List[Card]) -> str:
    """Format a list of cards as a string"""
    return ' '.join(str(card) for card in cards)

# Initialize poker hand evaluator
poker_hand = PokerHand() 