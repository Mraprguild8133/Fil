import os
import logging
from io import BytesIO
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
REMOVE_BG_API_KEY = os.getenv("API_KEY")

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Store user sessions
user_sessions = {}

# Background options
BACKGROUND_OPTIONS = {
    "white": "⚪ White",
    "black": "⚫ Black", 
    "transparent": "🔲 Transparent",
    "gray": "🔘 Gray",
    "red": "🔴 Red",
    "blue": "🔵 Blue",
    "green": "🟢 Green"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send welcome message when the command /start is issued."""
    welcome_text = """
🤖 **Background Remover Bot**

Send me an image and I'll remove its background instantly!

**Features:**
• Ultra-fast processing ⚡
• Multiple background colors 🎨
• High-quality results 🏆
• Support for various formats

Simply send an image to get started!
    """
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send help message when the command /help is issued."""
    help_text = """
📖 **How to use this bot:**

1. **Send an image** - Upload any image (as photo or document)
2. **Choose background** - Select from available background colors
3. **Download result** - Get your image with background removed

**Supported formats:** JPG, PNG, WebP, BMP
**Max file size:** 10MB

**Commands:**
/start - Start the bot
/help - Show this help message

**Note:** For best results, use images with clear subject boundaries.
    """
    await update.message.reply_text(help_text)

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming images."""
    try:
        user_id = update.effective_user.id
        
        # Check if message contains photo
        if update.message.photo:
            # Get the highest quality photo
            photo_file = await update.message.photo[-1].get_file()
        elif update.message.document:
            # Check if document is an image
            mime_type = update.message.document.mime_type
            if mime_type and mime_type.startswith('image/'):
                photo_file = await update.message.document.get_file()
            else:
                await update.message.reply_text("❌ Please send an image file (JPEG, PNG, etc.)")
                return
        else:
            await update.message.reply_text("❌ Please send an image")
            return

        # Send processing message
        processing_msg = await update.message.reply_text("📥 **Downloading image...**")

        # Download image to memory
        image_bytes = BytesIO()
        await photo_file.download_to_memory(image_bytes)
        image_bytes.seek(0)

        # Store user session
        user_sessions[user_id] = {
            "image_bytes": image_bytes,
            "file_name": f"image_{user_id}.jpg"
        }

        # Create background selection keyboard
        keyboard = [
            [
                InlineKeyboardButton("⚪ White", callback_data="white"),
                InlineKeyboardButton("⚫ Black", callback_data="black")
            ],
            [
                InlineKeyboardButton("🔲 Transparent", callback_data="transparent"),
                InlineKeyboardButton("🔘 Gray", callback_data="gray")
            ],
            [
                InlineKeyboardButton("🔴 Red", callback_data="red"),
                InlineKeyboardButton("🔵 Blue", callback_data="blue")
            ],
            [
                InlineKeyboardButton("🟢 Green", callback_data="green")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await processing_msg.edit_text(
            "🎨 **Select background color:**",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error handling image: {e}")
        await update.message.reply_text("❌ Error processing image. Please try again.")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle background color selection."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    bg_color = query.data

    if user_id not in user_sessions:
        await query.edit_message_text("❌ Session expired. Please send a new image.")
        return

    try:
        await query.edit_message_text(f"🔄 Removing background with {BACKGROUND_OPTIONS[bg_color]}...")

        # Process image with remove.bg
        image_bytes = user_sessions[user_id]["image_bytes"]
        result_bytes = await remove_background(image_bytes, bg_color)

        if result_bytes:
            # Send the processed image
            await query.message.reply_document(
                document=result_bytes,
                filename=f"no_bg_{bg_color}.png",
                caption=f"✅ **Background removed successfully!**\n🎨 Background: {BACKGROUND_OPTIONS[bg_color]}"
            )
            
            # Delete the selection message
            await query.delete_message()
        else:
            await query.edit_message_text("❌ Failed to remove background. Please try another image or check your API key.")

        # Cleanup
        if user_id in user_sessions:
            user_sessions[user_id]["image_bytes"].close()
            del user_sessions[user_id]

    except Exception as e:
        logger.error(f"Error in button handler: {e}")
        await query.edit_message_text("❌ Error processing image. Please try again.")
        
        # Cleanup on error
        if user_id in user_sessions:
            user_sessions[user_id]["image_bytes"].close()
            del user_sessions[user_id]

async def remove_background(image_bytes: BytesIO, bg_color: str) -> BytesIO:
    """Remove background using remove.bg API."""
    try:
        # Map color names to remove.bg format
        color_map = {
            "white": "white",
            "black": "black",
            "gray": "gray",
            "red": "ff0000",
            "blue": "0000ff",
            "green": "00ff00",
            "transparent": None
        }

        bg_color_param = color_map.get(bg_color)

        # Prepare API request
        url = "https://api.remove.bg/v1.0/removebg"
        
        # Reset stream position
        image_bytes.seek(0)
        
        files = {'image_file': image_bytes}
        data = {'size': 'auto'}
        
        if bg_color_param:
            data['bg_color'] = bg_color_param

        headers = {'X-Api-Key': REMOVE_BG_API_KEY}

        # Make API request
        response = requests.post(url, files=files, data=data, headers=headers, timeout=30)

        if response.status_code == 200:
            # Create BytesIO object from response content
            result_bytes = BytesIO(response.content)
            result_bytes.name = f"no_bg_{bg_color}.png"
            return result_bytes
        else:
            logger.error(f"Remove.bg API error: {response.status_code} - {response.text}")
            if response.status_code == 402:
                logger.error("Remove.bg API quota exceeded")
            elif response.status_code == 400:
                logger.error("Remove.bg API bad request - check image format")
            elif response.status_code == 403:
                logger.error("Remove.bg API unauthorized - check API key")
            return None

    except requests.exceptions.Timeout:
        logger.error("Remove.bg API request timed out")
        return None
    except Exception as e:
        logger.error(f"Remove background error: {e}")
        return None

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors and handle them gracefully."""
    logger.error(f"Exception while handling an update: {context.error}")
    
    # Notify user about error
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred while processing your request. Please try again."
        )

def main() -> None:
    """Start the bot."""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image))
    application.add_handler(CallbackQueryHandler(handle_button))
    
    # Add error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    print("🤖 Bot is starting...")
    print("⚡ Background Remover Bot is now running!")
    print("📍 Send /start to begin")
    
    # Run the bot until you press Ctrl-C
    application.run_polling()

if __name__ == "__main__":
    main()
