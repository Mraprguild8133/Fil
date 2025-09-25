import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot token from BotFather
    BOT_TOKEN = os.getenv('8431294116:AAHXFoaxtXwU96YrCngeY_x_clkLQgYsw0A')
    
    # Database configuration
    DATABASE_NAME = 'file_bot.db'
    
    # Storage configuration
    STORAGE_DIR = 'storage'
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    
    # Allowed file types
    ALLOWED_EXTENSIONS = {
        'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp'],
        'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
        'archives': ['.zip', '.rar', '.7z'],
        'audio': ['.mp3', '.wav', '.ogg'],
        'video': ['.mp4', '.avi', '.mkv']
    }
    
    @classmethod
    def validate_config(cls):
        """Validate that all required configuration is present"""
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN environment variable is not set!")
        
        # Validate BOT_TOKEN format (basic check)
        if not cls.BOT_TOKEN.startswith('') or ':' not in cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN format appears to be invalid!")
        
        return True
