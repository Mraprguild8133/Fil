import asyncio
import os
import logging
from typing import Optional
from io import BytesIO

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from pyrogram.errors import FloodWait
import removebg
from PIL import Image
import requests

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
REMOVE_BG_API_KEY = os.getenv("API_KEY")

# Initialize clients
app = Client("bg_remover_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
rmbg = removebg.RemoveBg(REMOVE_BG_API_KEY, "error.log")

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

# Store user sessions
user_sessions = {}

@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    """Start command handler"""
    welcome_text = """
🤖 **Background Remover Bot**

Send me an image and I'll remove its background instantly!

**Features:**
• Ultra-fast processing
• Multiple background options
• High-quality results
• Support for various image formats

Simply send an image to get started!
    """
    await message.reply_text(welcome_text)

@app.on_message(filters.photo | filters.document)
async def handle_image(client: Client, message: Message):
    """Handle incoming images"""
    try:
        # Send processing message
        processing_msg = await message.reply_text("🔄 **Processing your image...**")
        
        # Download the image
        image_path = await message.download()
        
        # Store user session
        user_sessions[message.from_user.id] = {
            "image_path": image_path,
            "processing_msg": processing_msg
        }
        
        # Show background options
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚪ White", callback_data="bg_white"),
             InlineKeyboardButton("⚫ Black", callback_data="bg_black")],
            [InlineKeyboardButton("🔲 Transparent", callback_data="bg_transparent"),
             InlineKeyboardButton("🔘 Gray", callback_data="bg_gray")],
            [InlineKeyboardButton("🔴 Red", callback_data="bg_red"),
             InlineKeyboardButton("🔵 Blue", callback_data="bg_blue")],
            [InlineKeyboardButton("🟢 Green", callback_data="bg_green")]
        ])
        
        await processing_msg.edit_text(
            "🎨 **Choose background color:**",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error handling image: {e}")
        await message.reply_text("❌ Error processing image. Please try again.")

@app.on_callback_query(filters.regex(r"^bg_"))
async def handle_background_selection(client: Client, callback_query: CallbackQuery):
    """Handle background color selection"""
    user_id = callback_query.from_user.id
    
    if user_id not in user_sessions:
        await callback_query.answer("Session expired. Please send image again.", show_alert=True)
        return
    
    try:
        # Get selected background
        bg_color = callback_query.data.replace("bg_", "")
        bg_name = BACKGROUND_OPTIONS.get(bg_color, "Transparent")
        
        # Update processing message
        await callback_query.message.edit_text(f"🔄 Removing background with {bg_name} background...")
        
        # Process image
        image_path = user_sessions[user_id]["image_path"]
        output_image = await process_image_background(image_path, bg_color)
        
        if output_image:
            # Send the processed image
            await callback_query.message.reply_document(
                document=output_image,
                caption=f"✅ **Background removed successfully!**\n🎨 Background: {bg_name}",
                file_name=f"no_bg_{bg_color}.png"
            )
            
            # Delete processing message
            await callback_query.message.delete()
        else:
            await callback_query.message.edit_text("❌ Error processing image. Please try again.")
        
        # Cleanup
        cleanup_user_session(user_id)
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Error in background selection: {e}")
        await callback_query.message.edit_text("❌ Error processing image. Please try again.")
        cleanup_user_session(user_id)

async def process_image_background(image_path: str, bg_color: str) -> Optional[BytesIO]:
    """Process image with selected background color"""
    try:
        # Convert bg_color to remove.bg format
        bg_map = {
            "white": "white",
            "black": "black", 
            "transparent": None,
            "gray": "gray",
            "red": "ff0000",
            "blue": "0000ff",
            "green": "00ff00"
        }
        
        bg_color_param = bg_map.get(bg_color)
        
        # Use remove.bg API
        if bg_color_param:
            result = rmbg.remove_background_from_img_file(
                image_path,
                bg_color=bg_color_param
            )
        else:
            result = rmbg.remove_background_from_img_file(image_path)
        
        # Convert to BytesIO for Telegram
        output = BytesIO()
        output.name = f"no_bg_{bg_color}.png"
        
        if hasattr(result, 'save'):
            # If it's a PIL Image
            result.save(output, format='PNG')
        else:
            # If it's bytes
            output.write(result)
        
        output.seek(0)
        return output
        
    except removebg.RemoveBgValidationError as e:
        logger.error(f"Remove.bg validation error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing image: {e}")
        return None

def cleanup_user_session(user_id: int):
    """Clean up user session and temporary files"""
    try:
        if user_id in user_sessions:
            session_data = user_sessions[user_id]
            # Remove temporary file
            if os.path.exists(session_data["image_path"]):
                os.remove(session_data["image_path"])
            # Remove session
            del user_sessions[user_id]
    except Exception as e:
        logger.error(f"Error cleaning up session: {e}")

@app.on_message(filters.command("help"))
async def help_command(client: Client, message: Message):
    """Help command handler"""
    help_text = """
📖 **How to use this bot:**

1. **Send an image** - Upload any image (as photo or document)
2. **Choose background** - Select from available background colors
3. **Download result** - Get your image with background removed

**Supported formats:** JPG, PNG, WebP
**Max file size:** 20MB

**Commands:**
/start - Start the bot
/help - Show this help message
/stats - Show bot statistics

**Note:** For best results, use images with clear subject boundaries.
    """
    await message.reply_text(help_text)

@app.on_message(filters.command("stats"))
async def stats_command(client: Client, message: Message):
    """Statistics command handler"""
    stats_text = f"""
📊 **Bot Statistics**

**Active sessions:** {len(user_sessions)}
**Background options:** {len(BACKGROUND_OPTIONS)}

**Bot Status:** ✅ Operational
**Processing Speed:** ⚡ Instant
**Quality:** 🏆 High

Powered by remove.bg API
    """
    await message.reply_text(stats_text)

# Error handler
@app.on_error()
async def error_handler(_, update, error):
    """Global error handler"""
    logger.error(f"Error in update {update}: {error}")
    
    if isinstance(error, FloodWait):
        wait_time = error.x
        logger.warning(f"Flood wait for {wait_time} seconds")
        await asyncio.sleep(wait_time)

if __name__ == "__main__":
    logger.info("Starting Background Remover Bot...")
    app.run()
