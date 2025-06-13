from telegram import Bot
from sqlalchemy.orm import Session
from models import User, Room, Game, GameHistory
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

class GameNotifier:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def send_room_notification(self, room: Room, message: str) -> None:
        """Send a notification to all players in a room."""
        try:
            for player in room.players:
                await self.bot.send_message(
                    chat_id=player.telegram_id,
                    text=message
                )
        except Exception as e:
            logger.error(f"Error sending room notification: {e}")

    async def notify_game_start(self, game: Game, room: Room) -> None:
        """Notify players when a game starts."""
        message = (
            f"🎮 Game Started! 🎮\n\n"
            f"Room: {room.name}\n"
            f"Game ID: {game.id}\n"
            f"Game Type: {game.game_type}\n"
            f"Players:\n" + "\n".join([f"• {player.first_name}" for player in game.participants])
        )
        await self.send_room_notification(room, message)

    async def notify_game_end(self, game: Game, room: Room, results: List[GameHistory]) -> None:
        """Notify players when a game ends."""
        message = (
            f"🏁 Game Ended! 🏁\n\n"
            f"Room: {room.name}\n"
            f"Game ID: {game.id}\n"
            f"Game Type: {game.game_type}\n\n"
            f"Results:\n" + "\n".join([
                f"• {result.user.first_name}: {result.result} "
                f"(Bet: {result.bet_amount:.2f}, Win: {result.win_amount:.2f})"
                for result in results
            ])
        )
        await self.send_room_notification(room, message)

    async def notify_player_joined(self, room: Room, user: User) -> None:
        """Notify when a player joins the room."""
        message = (
            f"👋 {user.first_name} joined the room!\n"
            f"Current players: {len(room.players)}/{room.max_players}"
        )
        await self.send_room_notification(room, message)

    async def notify_player_left(self, room: Room, user: User) -> None:
        """Notify when a player leaves the room."""
        message = (
            f"👋 {user.first_name} left the room.\n"
            f"Current players: {len(room.players)}/{room.max_players}"
        )
        await self.send_room_notification(room, message)

    async def notify_game_action(self, game: Game, room: Room, action: str, user: Optional[User] = None) -> None:
        """Notify about game actions (bets, turns, etc.)."""
        message = f"🎲 {action}"
        if user:
            message = f"🎲 {user.first_name}: {action}"
        await self.send_room_notification(room, message)

    async def notify_balance_update(self, user: User, amount: float, is_deposit: bool) -> None:
        """Notify user about balance updates."""
        action = "deposited" if is_deposit else "withdrawn"
        message = (
            f"💰 Balance Update\n\n"
            f"You {action}: {amount:.2f}\n"
            f"New balance: {user.balance:.2f}"
        )
        try:
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message
            )
        except Exception as e:
            logger.error(f"Error sending balance notification: {e}") 