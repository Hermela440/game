import sys
from .game import RockPaperScissors

def print_menu():
    """Print the game menu."""
    print("\nRock Paper Scissors Game")
    print("1. Rock")
    print("2. Paper")
    print("3. Scissors")
    print("4. Quit")
    print("\nEnter your choice (1-4): ", end="")

def main():
    """Main game loop."""
    game = RockPaperScissors()
    
    while True:
        print_menu()
        choice = input().strip()
        
        if choice == "4":
            print("Thanks for playing!")
            break
            
        if choice not in ["1", "2", "3"]:
            print("Invalid choice! Please try again.")
            continue
            
        # Map choice to game option
        choice_map = {
            "1": "rock",
            "2": "paper",
            "3": "scissors"
        }
        
        player_choice = choice_map[choice]
        result = game.play_round(player_choice)
        
        print("\nResults:")
        print(f"Player chose: {result[0]}")
        print(f"Computer chose: {result[1]}")
        print(f"Winner: {result[2]}")
        if result[3]:
            print(f"Winning choice: {result[3]}")
            
        input("\nPress Enter to continue...")
    
    game.cleanup()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nGame terminated by user.")
        sys.exit(0) 