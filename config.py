import os
from dotenv import load_dotenv

load_dotenv()

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
REMOVE_BG_API_KEY = os.getenv('REMOVE_BG_API_KEY')

# Remove.bg API endpoint - CORRECTED
REMOVE_BG_URL = "https://api.remove.bg/v1.0/removebg"

# Validate configuration
def validate_config():
    missing_vars = []
    
    if not BOT_TOKEN:
        missing_vars.append('BOT_TOKEN')
    
    if not REMOVE_BG_API_KEY:
        missing_vars.append('REMOVE_BG_API_KEY')
    
    if missing_vars:
        raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")
    
    print("✅ Configuration validated successfully!")

if __name__ == '__main__':
    validate_config()
