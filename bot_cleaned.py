import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from models import User, UserRole
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command."""
    user = update.effective_user
    db = SessionLocal()
    
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        if existing_user:
            await update.message.reply_text(
                f"Welcome back, {user.first_name}! You're already registered."
            )
        else:
            # Generate username if not provided
            username = user.username or f"user_{user.id}"
            
            # Create new user
            new_user = User(
                telegram_id=user.id,
                username=username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            
            db.add(new_user)
            db.commit()
            
            await update.message.reply_text(
                f"Welcome {user.first_name}! You have been successfully registered.\n"
                f"Your username is: {username}"
            )
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(
            "Sorry, there was an error processing your registration. Please try again later."
        )
    finally:
        db.close()

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(os.getenv('TELEGRAM_BOT_TOKEN')).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main() 