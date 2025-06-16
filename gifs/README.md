# Rock Paper Scissors Game Animations

This directory contains the GIF animations used in the Rock Paper Scissors game. The following GIF files are required:

1. `rock_vs_scissors.gif` - Animation for when Rock (🪨) beats Scissors (✂️)
2. `paper_vs_rock.gif` - Animation for when Paper (📄) beats Rock (🪨)
3. `scissors_vs_paper.gif` - Animation for when Scissors (✂️) beats Paper (📄)
4. `draw.gif` - Animation for when there's a draw (same moves or all different moves)

## File Requirements

- All GIFs should be optimized for Telegram (file size < 8MB)
- Recommended resolution: 480x480 pixels
- Format: GIF
- Duration: 2-3 seconds per animation

## How to Add GIFs

1. Place all four GIF files in this directory
2. Make sure the filenames match exactly as listed above
3. Test the bot to ensure animations are working correctly

## Fallback Behavior

If any GIF file is missing, the bot will automatically fall back to sending a text-only message with the game result. 