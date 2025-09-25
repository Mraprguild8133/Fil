
#!/usr/bin/env python3
import os
import logging
from bot import TelegramFileBot

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Main entry point for the application."""
    logger.info("🚀 Starting Telegram File Storage Bot...")
    
    # Check if BOT_TOKEN is set
    bot_token = os.getenv('BOT_TOKEN')
    if not bot_token:
        logger.error("❌ ERROR: BOT_TOKEN environment variable is not set!")
        logger.error("💡 Please set BOT_TOKEN in your Render environment variables.")
        return
    
    logger.info(f"✅ BOT_TOKEN found: {bot_token[:10]}...")
    
    try:
        bot = TelegramFileBot()
        logger.info("🤖 Bot initialized successfully!")
        bot.run()
    except Exception as e:
        logger.error(f"❌ Error starting bot: {e}")
        logger.error("💡 Make sure your BOT_TOKEN is correct and internet connection is available.")

if __name__ == '__main__':
    main()
