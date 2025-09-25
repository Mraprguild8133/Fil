import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Bot token from BotFather
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    
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
