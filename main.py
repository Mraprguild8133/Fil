import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, REMOVE_BG_API_KEY, REMOVE_BG_URL
import io
import os

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BackgroundRemoverBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Set up command and message handlers"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(MessageHandler(filters.PHOTO, self.handle_photo))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message when command /start is issued"""
        welcome_text = """
🤖 **Background Remover Bot**

Send me an image and I'll remove its background for you!

**Features:**
• Remove background from any image
• Support for PNG, JPG, JPEG formats
• High-quality background removal

**How to use:**
1. Send me an image
2. Wait for processing
3. Download your background-free image!

Use /help for more information.
        """
        await update.message.reply_text(welcome_text, parse_mode='Markdown')
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send help message when command /help is issued"""
        help_text = """
🆘 **Help Guide**

**Commands:**
/start - Start the bot
/help - Show this help message

**How to remove background:**
1. Simply send any image to this chat
2. The bot will automatically process it
3. You'll receive the image with transparent background

**Supported formats:**
• JPEG, JPG, PNG
• Maximum file size: 20MB

**Note:** For best results, use images with clear subject boundaries.
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages"""
        await update.message.reply_text(
            "📸 Please send me an image to remove its background!\n"
            "Use /help for instructions."
        )
    
    async def handle_photo(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming photos"""
        try:
            # Send processing message
            processing_msg = await update.message.reply_text("🔄 Processing your image...")
            
            # Get the highest quality photo
            photo_file = await update.message.photo[-1].get_file()
            
            # Download photo
            photo_bytes = await photo_file.download_as_bytearray()
            
            # Remove background
            result_image = await self.remove_background(photo_bytes)
            
            if result_image:
                # Send the processed image
                await update.message.reply_document(
                    document=io.BytesIO(result_image),
                    filename="background_removed.png",
                    caption="✅ Background removed successfully!"
                )
                await processing_msg.delete()
            else:
                await processing_msg.edit_text("❌ Failed to remove background. Please try again with a different image.")
        
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            await update.message.reply_text("❌ An error occurred while processing your image. Please try again.")
    
    async def remove_background(self, image_bytes: bytearray) -> bytes:
        """Remove background using remove.bg API"""
        try:
            headers = {
                'X-Api-Key': REMOVE_BG_API_KEY,
            }
            
            # Convert bytearray to bytes for requests
            image_bytes = bytes(image_bytes)
            
            files = {
                'image_file': ('image.jpg', image_bytes, 'image/jpeg')
            }
            
            data = {
                'size': 'auto'
            }
            
            logger.info("Sending request to remove.bg API...")
            
            response = requests.post(
                REMOVE_BG_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=60
            )
            
            logger.info(f"API Response Status: {response.status_code}")
            
            if response.status_code == 200:
                logger.info("Background removed successfully!")
                return response.content
            else:
                logger.error(f"Remove.bg API error: {response.status_code} - {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in remove_background: {e}")
            return None
    
    def run(self):
        """Start the bot"""
        logger.info("Bot is starting...")
        
        # Validate API keys
        if not BOT_TOKEN or not REMOVE_BG_API_KEY:
            logger.error("Missing API keys! Please check your .env file")
            return
        
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    bot = BackgroundRemoverBot()
    bot.run()
