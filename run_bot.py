import os
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from dotenv import load_dotenv
from datetime import datetime
from enum import Enum
from telegram.error import NetworkError, TimedOut
import asyncio
import sqlite3
from collections import Counter

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Game state
game_state = {
    "rooms": {},
    "player_rooms": {}
}

def init_db():
    """Initialize the database with required tables."""
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Create users table
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                total_wins INTEGER DEFAULT 0,
                total_losses INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create games table with support for 3 players
        c.execute('''
            CREATE TABLE IF NOT EXISTS games (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room_id TEXT NOT NULL,
                player1_id INTEGER NOT NULL,
                player2_id INTEGER,
                player3_id INTEGER,
                player1_move TEXT,
                player2_move TEXT,
                player3_move TEXT,
                winner_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (player1_id) REFERENCES users (telegram_id),
                FOREIGN KEY (player2_id) REFERENCES users (telegram_id),
                FOREIGN KEY (player3_id) REFERENCES users (telegram_id),
                FOREIGN KEY (winner_id) REFERENCES users (telegram_id)
            )
        ''')
        
        conn.commit()
        logger.info("Database initialized successfully")
        
        # Verify tables were created
        c.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = c.fetchall()
        logger.info(f"Created tables: {[table[0] for table in tables]}")
        
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_db():
    """Get database connection."""
    return sqlite3.connect('bot.db')

def create_room():
    """Create a new game room."""
    room_id = f"room_{random.randint(1000, 9999)}"
    game_state.rooms[room_id] = {
        "players": [],
        "moves": {},
        "status": "waiting"
    }
    return room_id

def join_room(room_id, player_id):
    """Add a player to a room."""
    if room_id in game_state.rooms:
        room = game_state.rooms[room_id]
        if len(room["players"]) < 2 and player_id not in room["players"]:
            room["players"].append(player_id)
            game_state.player_rooms[player_id] = room_id
            return True
    return False

def get_available_room():
    """Get an available room or create a new one."""
    for room_id, room in game_state.rooms.items():
        if room["status"] == "waiting" and len(room["players"]) < 2:
            return room_id
    return create_room()

def determine_winner(move1: str, move2: str) -> int:
    """Determine the winner of a game.
    Returns: 1 if player1 wins, 2 if player2 wins, 0 if draw"""
    if move1 == move2:
        return 0
    
    winning_moves = {
        "rock": "scissors",
        "scissors": "paper",
        "paper": "rock"
    }
    
    if winning_moves[move1] == move2:
        return 1
    return 2

def evaluate_3player_game(moves: dict):
    """
    Evaluate a 3-player Rock Paper Scissors game.
    
    Args:
        moves: dict of {user_id: move}, e.g. {101: "rock", 102: "rock", 103: "paper"}
    
    Returns:
        tuple: (winner_id or None, result_text, gif_key)
    """
    # Define what each move beats
    beats = {
        "rock": "scissors",
        "scissors": "paper",
        "paper": "rock"
    }
    
    values = list(moves.values())
    move_count = Counter(values)
    unique_moves = list(move_count.keys())
    
    # Emoji mapping for moves
    emoji_map = {
        "rock": "🪨",
        "paper": "📄",
        "scissors": "✂️"
    }
    
    if len(unique_moves) == 1:
        return None, "🤝 It's a draw! Everyone chose the same.", "draw"
    
    if len(unique_moves) == 3:
        return None, "🤝 It's a draw! All three moves cancel each other.", "draw"
    
    # Only 2 moves present
    move1, move2 = unique_moves
    if beats[move1] == move2:
        winner_move, loser_move = move1, move2
    elif beats[move2] == move1:
        winner_move, loser_move = move2, move1
    else:
        return None, "🤝 It's a draw! No move beats the other.", "draw"
    
    # Check if only one player chose the winning move
    if move_count[winner_move] == 1:
        winner_id = [uid for uid, m in moves.items() if m == winner_move][0]
        result_text = f"🏆 Player {winner_id} wins! {emoji_map[winner_move]} beats {emoji_map[loser_move]}"
        gif_key = f"{winner_move}_vs_{loser_move}"
        return winner_id, result_text, gif_key
    else:
        return None, "🤝 It's a draw! Multiple players used the winning move.", "draw"

async def determine_winner_and_notify(room_id: str, context: ContextTypes.DEFAULT_TYPE):
    """Determine the winner and notify all players with GIF animations."""
    try:
        room = game_state["rooms"][room_id]
        moves = room["moves"]
        
        if len(moves) != 3:
            logger.error(f"Not all players have moved in room {room_id}")
            return
        
        # Evaluate the game
        winner_id, result_text, gif_key = evaluate_3player_game(moves)
        
        # Update stats
        conn = None
        try:
            conn = get_db()
            c = conn.cursor()
            
            # Update winners
            if winner_id:
                c.execute('''
                    UPDATE users 
                    SET total_wins = total_wins + 1
                    WHERE telegram_id = ?
                ''', (winner_id,))
                
                # Update losers
                losers = [pid for pid in room["players"] if pid != winner_id]
                for loser_id in losers:
                    c.execute('''
                        UPDATE users 
                        SET total_losses = total_losses + 1
                        WHERE telegram_id = ?
                    ''', (loser_id,))
            
            # Update game record
            c.execute('''
                UPDATE games 
                SET player1_move = ?,
                    player2_move = ?,
                    player3_move = ?,
                    winner_id = ?
                WHERE room_id = ?
            ''', (
                moves.get(room["players"][0]),
                moves.get(room["players"][1]),
                moves.get(room["players"][2]),
                winner_id,
                room_id
            ))
            
            conn.commit()
            logger.info(f"Updated game results for room {room_id}")
        except Exception as e:
            logger.error(f"Database error updating results: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
        
        # Create rematch keyboard
        keyboard = [[InlineKeyboardButton("🔄 Play Again", callback_data=f"rematch:{room_id}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # First, send the result message to all players
        for player_id in room["players"]:
            try:
                await context.bot.send_message(
                    chat_id=player_id,
                    text=f"🎮 *Game Over!*\n\n{result_text}",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                logger.info(f"Sent result to player {player_id}")
            except Exception as e:
                logger.error(f"Error sending result to player {player_id}: {e}")
        
        # Wait a moment before showing the animation
        await asyncio.sleep(1)
        
        # Map gif_key to filename
        gif_map = {
            "rock_vs_scissors": "rock_vs_scissors.gif",
            "scissors_vs_paper": "scissors_vs_paper.gif",
            "paper_vs_rock": "paper_vs_rock.gif",
            "draw": "draw.gif"
        }
        
        gif_filename = gif_map.get(gif_key, "draw.gif")
        gif_path = os.path.join("gifs", gif_filename)
        
        # Check if GIF file exists
        if not os.path.exists(gif_path):
            logger.error(f"GIF file not found: {gif_path}")
            # Send a message about missing animation
            for player_id in room["players"]:
                try:
                    await context.bot.send_message(
                        chat_id=player_id,
                        text="🎬 *Animation Status*\n\n" +
                             "The game animation is currently unavailable.\n" +
                             "Please ensure the following GIF files are in the 'gifs' directory:\n" +
                             "• rock_vs_scissors.gif\n" +
                             "• scissors_vs_paper.gif\n" +
                             "• paper_vs_rock.gif\n" +
                             "• draw.gif",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"Error sending animation status to player {player_id}: {e}")
        else:
            # Send the GIF animation
            try:
                with open(gif_path, "rb") as gif:
                    for player_id in room["players"]:
                        try:
                            # Send the GIF animation with a caption
                            await context.bot.send_animation(
                                chat_id=player_id,
                                animation=gif,
                                caption="🎬 *Watch the battle!*",
                                parse_mode='Markdown'
                            )
                            logger.info(f"Sent animation to player {player_id}")
                        except Exception as e:
                            logger.error(f"Error sending animation to player {player_id}: {e}")
            except Exception as e:
                logger.error(f"Error reading GIF file: {e}")
                # Notify players of the error
                for player_id in room["players"]:
                    try:
                        await context.bot.send_message(
                            chat_id=player_id,
                            text="⚠️ Error loading animation. Please try again later."
                        )
                    except Exception as notify_error:
                        logger.error(f"Error sending error message to player {player_id}: {notify_error}")
        
        # Clean up game state
        for player_id in room["players"]:
            if player_id in game_state["player_rooms"]:
                del game_state["player_rooms"][player_id]
        del game_state["rooms"][room_id]
        logger.info(f"Cleaned up game state for room {room_id}")
        
    except Exception as e:
        logger.error(f"Error determining winner: {e}")
        # Notify players of error
        for player_id in room["players"]:
            try:
                await context.bot.send_message(
                    chat_id=player_id,
                    text="❌ Error processing game results. Please try /play again."
                )
            except Exception as notify_error:
                logger.error(f"Error sending error message to player {player_id}: {notify_error}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command."""
    user = update.effective_user
    
    # Register user
    await register_user(update, context)
    
    welcome_message = (
        "👋 *Welcome to Rock Paper Scissors!*\n\n"
        "🎮 *How to Play:*\n"
        "1. Use /play to start a new game\n"
        "2. Wait for an opponent\n"
        "3. Choose your move when matched\n"
        "4. See who wins!\n\n"
        "📊 Use /stats to see your game statistics\n"
        "❓ Use /help for more information\n\n"
        "Ready to play? Click the button below!"
    )
    
    keyboard = [[InlineKeyboardButton("🎮 Play Now", callback_data="play")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def register_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register a new user or update existing user's information."""
    user = update.effective_user
    logger.info(f"Processing registration for user: {user.id} ({user.username})")
    
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Check if user exists
        c.execute('SELECT * FROM users WHERE telegram_id = ?', (user.id,))
        db_user = c.fetchone()
        
        if db_user:
            # Update existing user's information
            c.execute('''
                UPDATE users 
                SET username = ?, first_name = ?, last_name = ?, last_active = CURRENT_TIMESTAMP
                WHERE telegram_id = ?
            ''', (user.username, user.first_name, user.last_name, user.id))
            logger.info(f"Updated existing user: {user.id}")
        else:
            # Create new user
            c.execute('''
                INSERT INTO users (telegram_id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
            ''', (user.id, user.username, user.first_name, user.last_name))
            logger.info(f"Successfully registered new user: {user.id} ({user.username})")
        
        conn.commit()
        
    except Exception as e:
        logger.error(f"Database error during user registration: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

async def play(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /play command - start a new game or join an existing one."""
    user = update.effective_user
    user_id = user.id
    
    logger.info(f"Play command received from user {user_id} ({user.username})")
    
    # Register user first
    try:
        await register_user(update, context)
        logger.info(f"User {user_id} registered successfully")
    except Exception as e:
        logger.error(f"Error registering user {user_id}: {e}")
        await update.message.reply_text("⚠️ Error registering user. Please try again.")
        return
    
    # Check if user is already in a game
    if user_id in game_state["player_rooms"]:
        room_id = game_state["player_rooms"][user_id]
        logger.info(f"User {user_id} is already in room {room_id}")
        if room_id in game_state["rooms"]:
            await update.message.reply_text(
                "⚠️ You're already in a game! Please finish your current game first.",
                parse_mode='Markdown'
            )
            return
    
    # Look for an available room
    available_room = None
    logger.info("Searching for available rooms...")
    for room_id, room in game_state["rooms"].items():
        logger.info(f"Checking room {room_id}: {len(room['players'])} players")
        if len(room["players"]) < 3 and room_id not in game_state["player_rooms"].get(user_id, []):
            available_room = room_id
            logger.info(f"Found available room: {room_id}")
            break
    
    if available_room:
        # Join existing room
        logger.info(f"Joining room {available_room}")
        room = game_state["rooms"][available_room]
        room["players"].append(user_id)
        game_state["player_rooms"][user_id] = available_room
        
        # Create or update game record in database
        conn = None
        try:
            conn = get_db()
            c = conn.cursor()
            
            # Check if game record exists
            c.execute('SELECT id FROM games WHERE room_id = ?', (available_room,))
            game = c.fetchone()
            
            if game:
                # Update existing game record
                player_num = len(room["players"])
                c.execute(f'''
                    UPDATE games 
                    SET player{player_num}_id = ?
                    WHERE room_id = ?
                ''', (user_id, available_room))
            else:
                # Create new game record
                c.execute('''
                    INSERT INTO games (room_id, player1_id, created_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                ''', (available_room, room["players"][0]))
            
            conn.commit()
            logger.info(f"Updated game record for room {available_room}")
        except Exception as e:
            logger.error(f"Database error updating game: {e}")
            if conn:
                conn.rollback()
        finally:
            if conn:
                conn.close()
        
        # If we have 3 players, start the game
        if len(room["players"]) == 3:
            keyboard = [
                [
                    InlineKeyboardButton("🪨 Rock", callback_data=f"move:{available_room}:rock"),
                    InlineKeyboardButton("📄 Paper", callback_data=f"move:{available_room}:paper"),
                    InlineKeyboardButton("✂️ Scissors", callback_data=f"move:{available_room}:scissors")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            match_message = (
                "🔥 *Game is starting! Let's battle!*\n\n"
                "Choose your move:"
            )
            
            # Send to all players
            for player_id in room["players"]:
                try:
                    await context.bot.send_message(
                        chat_id=player_id,
                        text=match_message,
                        reply_markup=reply_markup,
                        parse_mode='Markdown'
                    )
                    logger.info(f"Sent match message to player {player_id}")
                except Exception as e:
                    logger.error(f"Error sending match message to player {player_id}: {e}")
        else:
            # Notify waiting players
            await update.message.reply_text(
                f"🎮 *Waiting for more players...*\n\n"
                f"Current players: {len(room['players'])}/3",
                parse_mode='Markdown'
            )
    else:
        # Create new room
        room_id = f"room_{len(game_state['rooms']) + 1}"
        logger.info(f"Creating new room {room_id}")
        game_state["rooms"][room_id] = {
            "players": [user_id],
            "moves": {}
        }
        game_state["player_rooms"][user_id] = room_id
        
        await update.message.reply_text(
            "🎮 *Waiting for opponents...*\n\n"
            "I'll notify you when more players join!",
            parse_mode='Markdown'
        )
        logger.info(f"User {user_id} is waiting in room {room_id}")

async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    logger.info(f"Button callback received: {query.data}")
    
    if query.data.startswith("move:"):
        # Handle move selection
        try:
            parts = query.data.split(":")
            if len(parts) != 3:
                logger.error(f"Invalid move data format: {query.data}")
                await query.edit_message_text("❌ Invalid move data. Please try again.")
                return
                
            _, room_id, move = parts
            user_id = query.from_user.id
            logger.info(f"Move selection: user {user_id} selected {move} in room {room_id}")
            
            if room_id not in game_state["rooms"]:
                logger.error(f"Room {room_id} not found in game state")
                await query.edit_message_text("❌ This game has expired. Use /play to start a new game.")
                return
            
            room = game_state["rooms"][room_id]
            if user_id not in room["players"]:
                logger.error(f"User {user_id} not found in room {room_id}")
                await query.edit_message_text("❌ You're not a player in this game.")
                return
            
            # Save move in game state
            room["moves"][user_id] = move
            logger.info(f"Saved move {move} for user {user_id} in game state")
            
            # Update database
            conn = None
            try:
                conn = get_db()
                c = conn.cursor()
                
                # Determine if user is player1 or player2
                c.execute('SELECT player1_id, player2_id FROM games WHERE room_id = ?', (room_id,))
                result = c.fetchone()
                if result:
                    player1_id, player2_id = result
                    is_player1 = player1_id == user_id
                    move_column = "player1_move" if is_player1 else "player2_move"
                    logger.info(f"User {user_id} is player {'1' if is_player1 else '2'}")
                    
                    # Update the game record
                    c.execute(f'''
                        UPDATE games 
                        SET {move_column} = ?
                        WHERE room_id = ?
                    ''', (move, room_id))
                    conn.commit()
                    logger.info(f"Saved {move} for player {user_id} in database")
                    
                    # Check if both players have moved
                    c.execute('SELECT COUNT(*) FROM games WHERE room_id = ? AND player1_move IS NOT NULL AND player2_move IS NOT NULL', (room_id,))
                    moves_count = c.fetchone()[0]
                    logger.info(f"Total moves in room {room_id}: {moves_count}")
                    
                    if moves_count == 2:
                        logger.info(f"Both players have moved in room {room_id}, determining winner")
                        await determine_winner_and_notify(room_id, context)
                    else:
                        await query.edit_message_text(
                            f"✅ You selected: {move}\n\n"
                            "Waiting for your opponent..."
                        )
                else:
                    logger.error(f"No game record found for room {room_id}")
                    await query.edit_message_text("❌ Error: Game record not found.")
                    
            except Exception as e:
                logger.error(f"Database error handling move: {e}")
                if conn:
                    conn.rollback()
                await query.edit_message_text("❌ Error saving your move. Please try again.")
            finally:
                if conn:
                    conn.close()
        except Exception as e:
            logger.error(f"Error processing move: {e}")
            await query.edit_message_text("❌ Error processing your move. Please try again.")
    
    elif query.data.startswith("rematch:"):
        # Handle rematch request
        try:
            room_id = query.data.split(":")[1]
            user_id = query.from_user.id
            logger.info(f"Rematch requested by user {user_id} for room {room_id}")
            
            # Clean up old game state
            if room_id in game_state["rooms"]:
                for player_id in game_state["rooms"][room_id]["players"]:
                    if player_id in game_state["player_rooms"]:
                        del game_state["player_rooms"][player_id]
                del game_state["rooms"][room_id]
                logger.info(f"Cleaned up old game state for room {room_id}")
            
            # Start new game
            await play(update, context)
        except Exception as e:
            logger.error(f"Error processing rematch: {e}")
            await query.edit_message_text("❌ Error starting rematch. Please try /play instead.")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's game statistics."""
    user_id = update.effective_user.id
    
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Get user stats
        c.execute('''
            SELECT COUNT(*) FROM games 
            WHERE player1_id = ? OR player2_id = ?
        ''', (user_id, user_id))
        total_games = c.fetchone()[0]
        
        c.execute('''
            SELECT COUNT(*) FROM games 
            WHERE winner_id = ?
        ''', (user_id,))
        wins = c.fetchone()[0]
        
        c.execute('''
            SELECT COUNT(*) FROM games 
            WHERE (player1_id = ? OR player2_id = ?) 
            AND winner_id IS NULL
        ''', (user_id, user_id))
        draws = c.fetchone()[0]
        
        if total_games == 0:
            await update.message.reply_text("📊 You haven't played any games yet!")
            return
            
        losses = total_games - wins - draws
        
        stats_message = (
            "📊 *Your Game Statistics*\n\n"
            f"🎮 Total Games: {total_games}\n"
            f"🏆 Wins: {wins}\n"
            f"😢 Losses: {losses}\n"
            f"🤝 Draws: {draws}\n"
            f"📈 Win Rate: {(wins/total_games)*100:.1f}%"
        )
        
        await update.message.reply_text(stats_message, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Database error getting stats: {e}")
        await update.message.reply_text("⚠️ Error getting statistics. Please try again later.")
    finally:
        if conn:
            conn.close()

async def show_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information."""
    help_message = (
        "🎮 *Rock Paper Scissors Bot Help*\n\n"
        "*Commands:*\n"
        "• /start - Start the bot and see welcome message\n"
        "• /play - Start a new game or join an existing one\n"
        "• /stats - View your game statistics\n"
        "• /help - Show this help message\n\n"
        "*How to Play:*\n"
        "1. Use /play to start a game\n"
        "2. Wait for an opponent to join\n"
        "3. When matched, choose your move:\n"
        "   🪨 Rock beats Scissors\n"
        "   📄 Paper beats Rock\n"
        "   ✂️ Scissors beats Paper\n"
        "4. See who wins!\n\n"
        "*Tips:*\n"
        "• You can only be in one game at a time\n"
        "• Use /stats to track your progress\n"
        "• After each game, you can play again!\n\n"
        "Need more help? Contact the bot administrator."
    )
    
    await update.message.reply_text(help_message, parse_mode='Markdown')

def main():
    """Start the bot."""
    # Initialize database
    init_db()
    
    # Create the Application and pass it your bot's token
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("play", play))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("help", show_help))
    
    # Add callback query handler for buttons
    application.add_handler(CallbackQueryHandler(handle_buttons))

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
