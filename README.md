# Rock Paper Scissors Telegram Bot

A multiplayer Rock Paper Scissors game bot for Telegram that supports up to 3 players per game.

## Features

- 🎮 Multiplayer support (2-3 players)
- 🏆 Win/loss tracking
- 🎬 Animated battle results
- 🔄 Rematch option
- 📊 Player statistics

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/rock-paper-scissors-bot.git
cd rock-paper-scissors-bot
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your bot token:
```
BOT_TOKEN=your_telegram_bot_token_here
```

5. Add GIF animations:
   - Create a `gifs` directory
   - Add the following GIF files:
     - `rock_vs_scissors.gif`
     - `paper_vs_rock.gif`
     - `scissors_vs_paper.gif`
     - `draw.gif`

## Running the Bot

```bash
python run_bot.py
```

## Commands

- `/start` - Start the bot and get instructions
- `/play` - Start a new game
- `/stats` - View your win/loss statistics
- `/help` - Show help information

## Game Rules

1. Rock (🪨) beats Scissors (✂️)
2. Scissors (✂️) beats Paper (📄)
3. Paper (📄) beats Rock (🪨)
4. Same moves result in a draw
5. All different moves result in a draw

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details. 