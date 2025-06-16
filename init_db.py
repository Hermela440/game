from models_new import Base
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///bot.db')

def init_db():
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Drop all tables
    Base.metadata.drop_all(engine)
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    print("Database initialized successfully!")

if __name__ == "__main__":
    init_db() 