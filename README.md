# Telegram Bot Project

A Telegram bot built with Python using the python-telegram-bot library.

## Features

- User registration and management
- Game room creation and management
- Balance tracking
- Game statistics

## Setup

1. Clone the repository:
```bash
git clone <your-repository-url>
cd <repository-name>
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: .\venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file with your configuration:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
DATABASE_URL=sqlite:///bot.db
```

5. Run the bot:
```bash
python run_bot.py
```

## Project Structure

- `bot.py` - Main bot logic and command handlers
- `models/` - Database models
  - `user.py` - User model
  - `room.py` - Room model
  - `game.py` - Game model
- `database.py` - Database configuration
- `password_manager.py` - Password hashing and verification
- `run_bot.py` - Bot entry point

## Commands

- `/start` - Start the bot and register
- `/help` - Show available commands
- `/balance` - Check your balance
- `/create_room` - Create a new game room
- `/join_room` - Join an existing room
- `/leave_room` - Leave current room
- `/room_info` - Show room information
- `/game_status` - Show current game status

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 