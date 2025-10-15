import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
REMOVE_BG_API_KEY = os.getenv('REMOVE_BG_API_KEY')

# Remove.bg API endpoint
REMOVE_BG_URL = "https://api.remove.bg/v1.0/removebg"    

# Create global config instance
try:
    config = Config()
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    raise
