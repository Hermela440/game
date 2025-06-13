import random
from typing import Tuple, Optional
from .battle_animation import BattleAnimation

class RockPaperScissors:
    def __init__(self):
        """Initialize the Rock Paper Scissors game."""
        self.choices = ["rock", "paper", "scissors"]
        self.battle_animation = BattleAnimation()
        
    def get_computer_choice(self) -> str:
        """Get a random choice for the computer."""
        return random.choice(self.choices)
    
    def determine_winner(self, player_choice: str, computer_choice: str) -> Tuple[str, Optional[str]]:
        """Determine the winner of the game."""
        if player_choice == computer_choice:
            return "tie", None
            
        winning_combinations = {
            "rock": "scissors",
            "paper": "rock",
            "scissors": "paper"
        }
        
        if winning_combinations[player_choice] == computer_choice:
            return "player", player_choice
        else:
            return "computer", computer_choice
    
    def play_round(self, player_choice: str) -> Tuple[str, str, str, Optional[str]]:
        """Play a round of Rock Paper Scissors."""
        computer_choice = self.get_computer_choice()
        winner, winning_choice = self.determine_winner(player_choice, computer_choice)
        
        # Show battle animation
        self.battle_animation.animate_battle(player_choice, computer_choice, winner)
        
        return player_choice, computer_choice, winner, winning_choice
    
    def cleanup(self) -> None:
        """Clean up game resources."""
        self.battle_animation.cleanup()

# Example usage
if __name__ == "__main__":
    game = RockPaperScissors()
    player_choice = "rock"
    result = game.play_round(player_choice)
    print(f"Player chose: {result[0]}")
    print(f"Computer chose: {result[1]}")
    print(f"Winner: {result[2]}")
    if result[3]:
        print(f"Winning choice: {result[3]}")
    game.cleanup() 