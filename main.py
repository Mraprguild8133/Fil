import os
import logging
from io import BytesIO
import asyncio
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
REMOVE_BG_API_KEY = os.getenv("API_KEY")

# Validate required environment variables
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is required")
if not REMOVE_BG_API_KEY:
    raise ValueError("API_KEY environment variable is required")

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store user sessions
user_sessions = {}

# Background options with emojis
BACKGROUND_OPTIONS = {
    "white": {"name": "⚪ White", "color": "white"},
    "black": {"name": "⚫ Black", "color": "black"},
    "transparent": {"name": "🔲 Transparent", "color": None},
    "gray": {"name": "🔘 Gray", "color": "gray"},
    "red": {"name": "🔴 Red", "color": "ff0000"},
    "blue": {"name": "🔵 Blue", "color": "0000ff"},
    "green": {"name": "🟢 Green", "color": "00ff00"},
    "purple": {"name": "🟣 Purple", "color": "800080"},
    "yellow": {"name": "🟡 Yellow", "color": "ffff00"},
    "orange": {"name": "🟠 Orange", "color": "ffa500"}
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message when the command /start is issued."""
    welcome_text = """
🎨 *Background Remover Bot*

*Remove image backgrounds instantly with AI!*

✨ *Features:*
• Lightning-fast processing ⚡
• Multiple background colors
• High-quality AI removal
• Support for all image formats
• Preserves image quality

*How to use:*
1. Send me an image
2. Choose your background color
3. Download your processed image

*Supported formats:* JPEG, PNG, WebP, BMP, TIFF
*Max file size:* 20MB

Ready to start? Just send me an image! 📸
    """
    await update.message.reply_text(welcome_text, parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message when the command /help is issued."""
    help_text = """
📖 *Bot Help Guide*

*Available Commands:*
/start - Start the bot and see welcome message
/help - Show this help message
/stats - Show bot statistics

*How to Remove Backgrounds:*
1. *Send an image* - As a photo or file upload
2. *Select background* - Choose from color options
3. *Download* - Get your processed image instantly

*Tips for Best Results:*
• Use clear, high-contrast images
• Ensure subject has clear edges
• Avoid complex backgrounds for better results
• Supported formats: JPG, PNG, WebP, BMP

*Need Help?*
If you encounter any issues:
• Check your image format and size
• Ensure good internet connection
• Try with a different image
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show bot statistics."""
    stats_text = f"""
📊 *Bot Statistics*

*Active Sessions:* {len(user_sessions)}
*Background Options:* {len(BACKGROUND_OPTIONS)}
*Status:* ✅ Operational

*Processing Speed:* ⚡ Instant
*Image Quality:* 🏆 High Quality
*Uptime:* 24/7

Powered by Remove.bg AI Technology
    """
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming images."""
    try:
        user_id = update.effective_user.id
        message = update.message
        
        # Check file size (max 20MB)
        if (message.document and message.document.file_size > 20 * 1024 * 1024) or \
           (message.photo and message.photo[-1].file_size > 20 * 1024 * 1024):
            await message.reply_text("❌ *File too large!* Please send images smaller than 20MB.", parse_mode='Markdown')
            return

        # Send processing message
        processing_msg = await message.reply_text("📥 *Downloading your image...*", parse_mode='Markdown')

        # Download image
        if message.photo:
            # Get the highest quality photo
            photo_file = await message.photo[-1].get_file()
        elif message.document and message.document.mime_type and message.document.mime_type.startswith('image/'):
            photo_file = await message.document.get_file()
        else:
            await processing_msg.edit_text("❌ *Unsupported file type!* Please send a valid image file.", parse_mode='Markdown')
            return

        # Download image to memory
        image_bytes = BytesIO()
        await photo_file.download_to_memory(image_bytes)
        image_bytes.seek(0)

        # Store user session with timestamp for cleanup
        user_sessions[user_id] = {
            "image_bytes": image_bytes,
            "file_name": f"image_{user_id}_{update.update_id}.jpg",
            "timestamp": asyncio.get_event_loop().time()
        }

        # Create background selection keyboard
        keyboard = []
        bg_options = list(BACKGROUND_OPTIONS.items())
        
        # Create 2 buttons per row
        for i in range(0, len(bg_options), 2):
            row = []
            for j in range(2):
                if i + j < len(bg_options):
                    bg_key, bg_data = bg_options[i + j]
                    row.append(InlineKeyboardButton(bg_data["name"], callback_data=bg_key))
            keyboard.append(row)

        reply_markup = InlineKeyboardMarkup(keyboard)

        await processing_msg.edit_text(
            "🎨 *Choose your background color:*\n\n"
            "• *Colored backgrounds* replace the transparent areas\n"
            "• *Transparent* keeps alpha channel for PNG\n"
            "• All options maintain high quality",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    except Exception as e:
        logger.error(f"Error handling image: {e}")
        await update.message.reply_text("❌ *Error processing image!* Please try again with a different image.", parse_mode='Markdown')

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle background color selection."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    bg_color = query.data

    if user_id not in user_sessions:
        await query.edit_message_text("❌ *Session expired!* Please send a new image.", parse_mode='Markdown')
        return

    try:
        bg_data = BACKGROUND_OPTIONS.get(bg_color)
        if not bg_data:
            await query.edit_message_text("❌ Invalid background selection.")
            return

        await query.edit_message_text(
            f"🔄 *Processing with {bg_data['name']} background...*\n\n"
            f"• AI background removal in progress\n"
            f"• This usually takes 2-5 seconds\n"
            f"• Please wait...",
            parse_mode='Markdown'
        )

        # Process image with remove.bg
        image_bytes = user_sessions[user_id]["image_bytes"]
        result_bytes = await remove_background_async(image_bytes, bg_data["color"])

        if result_bytes:
            # Get file size info
            file_size = len(result_bytes.getvalue()) / 1024  # Size in KB
            
            # Send the processed image
            await query.message.reply_document(
                document=result_bytes,
                filename=f"no_background_{bg_color}.png",
                caption=(
                    f"✅ *Background Removal Complete!*\n\n"
                    f"• 🎨 Background: {bg_data['name']}\n"
                    f"• 📁 Format: PNG (Transparent)\n"
                    f"• 💾 Size: {file_size:.1f}KB\n"
                    f"• ⚡ Quality: High\n\n"
                    f"*Need another background?* Send a new image! 📸"
                ),
                parse_mode='Markdown'
            )
            
            # Delete the processing message
            await query.delete_message()
            
            logger.info(f"Successfully processed image for user {user_id} with background {bg_color}")
        else:
            await query.edit_message_text(
                "❌ *Failed to remove background!*\n\n"
                "Possible reasons:\n"
                "• API quota exceeded\n"
                "• Image format not supported\n"
                "• Poor image quality\n"
                "• Network issue\n\n"
                "Please try again with a different image.",
                parse_mode='Markdown'
            )

    except Exception as e:
        logger.error(f"Error in button handler: {e}")
        await query.edit_message_text(
            "❌ *Processing error!* Please try again with a different image.",
            parse_mode='Markdown'
        )
    finally:
        # Cleanup
        await cleanup_user_session(user_id)

async def remove_background_async(image_bytes: BytesIO, bg_color: str) -> BytesIO:
    """Remove background using remove.bg API asynchronously."""
    try:
        # Reset stream position
        image_bytes.seek(0)
        
        # Prepare API request data
        data = aiohttp.FormData()
        data.add_field('image_file', image_bytes, filename='image.jpg')
        data.add_field('size', 'auto')
        
        if bg_color:
            data.add_field('bg_color', bg_color)

        headers = {'X-Api-Key': REMOVE_BG_API_KEY}

        # Make async API request
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as session:
            async with session.post(
                'https://api.remove.bg/v1.0/removebg',
                data=data,
                headers=headers
            ) as response:
                
                if response.status == 200:
                    result_data = await response.read()
                    result_bytes = BytesIO(result_data)
                    result_bytes.name = "no_background.png"
                    return result_bytes
                else:
                    error_text = await response.text()
                    logger.error(f"Remove.bg API error {response.status}: {error_text}")
                    return None

    except asyncio.TimeoutError:
        logger.error("Remove.bg API request timed out")
        return None
    except Exception as e:
        logger.error(f"Remove background error: {e}")
        return None

async def cleanup_user_session(user_id: int) -> None:
    """Clean up user session and resources."""
    try:
        if user_id in user_sessions:
            session_data = user_sessions[user_id]
            if 'image_bytes' in session_data:
                session_data['image_bytes'].close()
            del user_sessions[user_id]
    except Exception as e:
        logger.error(f"Error cleaning up session for user {user_id}: {e}")

async def cleanup_old_sessions():
    """Periodically clean up old sessions."""
    while True:
        try:
            current_time = asyncio.get_event_loop().time()
            expired_users = []
            
            for user_id, session_data in user_sessions.items():
                if current_time - session_data['timestamp'] > 3600:  # 1 hour
                    expired_users.append(user_id)
            
            for user_id in expired_users:
                await cleanup_user_session(user_id)
                
            if expired_users:
                logger.info(f"Cleaned up {len(expired_users)} expired sessions")
                
        except Exception as e:
            logger.error(f"Error in session cleanup: {e}")
        
        await asyncio.sleep(300)  # Run every 5 minutes

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and handle them gracefully."""
    logger.error(f"Exception while handling an update: {context.error}", exc_info=context.error)
    
    # Notify user about error
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ *An unexpected error occurred!*\n\n"
                "Please try again or send /help for assistance.",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Error sending error message: {e}")

def main() -> None:
    """Start the bot."""
    try:
        # Create the Application
        application = Application.builder().token(BOT_TOKEN).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(MessageHandler(filters.PHOTO | (filters.Document.IMAGE & ~filters.COMMAND), handle_image))
        application.add_handler(CallbackQueryHandler(handle_button))
        
        # Add error handler
        application.add_error_handler(error_handler)

        # Start session cleanup task
        loop = asyncio.get_event_loop()
        loop.create_task(cleanup_old_sessions())

        # Start the Bot
        logger.info("🤖 Starting Background Remover Bot...")
        print("🎨 Background Remover Bot")
        print("⚡ Version: Latest")
        print("📅 Using python-telegram-bot latest")
        print("🚀 Bot is now running! Press Ctrl+C to stop")
        print("📍 Send /start to begin")
        
        # Run the bot until you press Ctrl-C
        application.run_polling(drop_pending_updates=True)

    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == "__main__":
    main()
