import pygame
import os
import sys
from typing import Tuple, Optional

class BattleAnimation:
    def __init__(self, width: int = 800, height: int = 600):
        """Initialize the battle animation system."""
        pygame.init()
        self.width = width
        self.height = height
        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Rock Paper Scissors Battle")
        
        # Load and scale assets
        self.assets = self._load_assets()
        self.font = pygame.font.SysFont(None, 60)
        
    def _load_assets(self) -> dict:
        """Load and scale game assets."""
        asset_path = os.path.join(os.path.dirname(__file__), "assets")
        assets = {}
        
        for item in ["rock", "paper", "scissors"]:
            img_path = os.path.join(asset_path, f"{item}.png")
            if os.path.exists(img_path):
                img = pygame.image.load(img_path)
                assets[item] = pygame.transform.scale(img, (200, 200))
            else:
                # Create a placeholder if image not found
                surf = pygame.Surface((200, 200))
                surf.fill((100, 100, 100))
                assets[item] = surf
                
        return assets
    
    def draw_text(self, text: str, y: int, color: Tuple[int, int, int] = (255, 0, 0)) -> None:
        """Draw centered text on screen."""
        text_surface = self.font.render(text, True, color)
        x = (self.width - text_surface.get_width()) // 2
        self.screen.blit(text_surface, (x, y))
    
    def animate_battle(self, player_choice: str, computer_choice: str, winner: Optional[str]) -> None:
        """Animate the battle between player and computer choices."""
        clock = pygame.time.Clock()
        player_x = 100
        computer_x = 500
        shake = 0
        
        # Determine winner position and animation
        winner_pos = "left" if winner == "player" else "right" if winner == "computer" else None
        
        for frame in range(60):  # 60 frames (~1 second)
            self.screen.fill((30, 30, 30))
            
            # Draw choices
            self.screen.blit(self.assets[player_choice], (player_x, 200))
            self.screen.blit(self.assets[computer_choice], (computer_x, 200))
            
            # Animate winner
            if winner_pos:
                shake = (-1) ** frame * 10 if frame < 30 else 0
                if winner_pos == "left":
                    self.screen.blit(self.assets[player_choice], (player_x + shake, 200))
                else:
                    self.screen.blit(self.assets[computer_choice], (computer_x + shake, 200))
                
                # Fade out loser
                if frame >= 30:
                    fade_surf = pygame.Surface((200, 200))
                    fade_surf.set_alpha((frame - 30) * 8)
                    fade_surf.fill((30, 30, 30))
                    if winner_pos == "left":
                        self.screen.blit(fade_surf, (computer_x, 200))
                    else:
                        self.screen.blit(fade_surf, (player_x, 200))
            
            # Draw battle text
            self.draw_text(f"{player_choice.capitalize()} VS {computer_choice.capitalize()}", 50)
            
            # Draw winner text
            if frame == 59 and winner:
                if winner == "tie":
                    self.draw_text("It's a Tie!", 450, (255, 255, 0))
                else:
                    winner_choice = player_choice if winner == "player" else computer_choice
                    self.draw_text(f"💥 {winner_choice.capitalize()} Wins!", 450)
            
            pygame.display.flip()
            clock.tick(60)
            
            # Handle quit events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
    
    def cleanup(self) -> None:
        """Clean up pygame resources."""
        pygame.quit()

# Example usage
if __name__ == "__main__":
    battle = BattleAnimation()
    battle.animate_battle("rock", "scissors", "player")
    battle.cleanup() 