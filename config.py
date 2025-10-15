import os
from dataclasses import dataclass

@dataclass
class Config:
    API_ID: int
    API_HASH: str
    BOT_TOKEN: str
    API_KEY: str  # remove.bg API Key
    MAX_FILE_SIZE: int = 10_000_000  # 10MB default
    RATE_LIMIT: int = 10  # requests per minute

def load_config():
    """Load configuration from environment variables"""
    try:
        api_id = int(os.environ.get("API_ID"))
    except (ValueError, TypeError):
        raise ValueError("API_ID must be an integer")
    
    api_hash = os.environ.get("API_HASH")
    bot_token = os.environ.get("BOT_TOKEN")
    api_key = os.environ.get("API_KEY")
    
    if not all([api_id, api_hash, bot_token, api_key]):
        raise ValueError("Missing one or more required environment variables")
    
    return Config(
        API_ID=api_id,
        API_HASH=api_hash,
        BOT_TOKEN=bot_token,
        API_KEY=api_key
    )

# Create global config object
config = load_config()
