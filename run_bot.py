import os
from dotenv import load_dotenv
from bot import main

# Load from .env if you want
load_dotenv()

# Or directly set the token like this
os.environ['TELEGRAM_BOT_TOKEN'] = '7832695308:AAHlQ3bXJT5rbIeP8OzoujBB2M9ZZBuEB-U'

if __name__ == '__main__':
    main()
