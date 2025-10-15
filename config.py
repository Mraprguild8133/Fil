import os
import logging

logger = logging.getLogger(__name__)

class Config:
    def __init__(self):
        self.API_ID = self._get_api_id()
        self.API_HASH = self._get_env_var("API_HASH")
        self.BOT_TOKEN = self._get_env_var("BOT_TOKEN")
        self.API_KEY = self._get_env_var("API_KEY")  # remove.bg API Key
        self.MAX_FILE_SIZE = 10_000_000  # 10MB
        self.RATE_LIMIT = 10  # requests per minute
        
        logger.info("Configuration loaded successfully")
        logger.info(f"API_ID: {self.API_ID}")
        logger.info(f"API_HASH: {self.API_HASH[:10]}...")
        logger.info(f"BOT_TOKEN: {self.BOT_TOKEN[:10]}...")
        logger.info(f"API_KEY: {self.API_KEY[:10]}...")

    def _get_api_id(self):
        """Get and validate API_ID"""
        api_id = os.environ.get("API_ID")
        if not api_id:
            raise ValueError("API_ID environment variable is required")
        
        try:
            return int(api_id)
        except ValueError:
            raise ValueError("API_ID must be a valid integer")

    def _get_env_var(self, var_name):
        """Get environment variable with validation"""
        value = os.environ.get(var_name)
        if not value:
            raise ValueError(f"{var_name} environment variable is required")
        return value

# Create global config instance
try:
    config = Config()
except Exception as e:
    logger.error(f"Failed to load configuration: {e}")
    raise
