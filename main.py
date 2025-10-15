import os
import logging
import asyncio
from io import BytesIO
import requests
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration from environment variables
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
REMOVE_BG_API_KEY = os.getenv("API_KEY")

# Initialize Pyrogram client
app = Client("bg_remover", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Store user data temporarily
user_data = {}

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    await message.reply_text(
        "🤖 **Background Remover Bot**\n\n"
        "Send me an image and I'll remove its background instantly!\n\n"
        "**Features:**\n"
        "• Ultra-fast processing\n"
        "• Multiple background colors\n"
        "• High-quality results\n\n"
        "Just send me an image to begin!"
    )

@app.on_message(filters.photo | (filters.document & filters.mime_type("image/")))
async def handle_image(client, message: Message):
    try:
        user_id = message.from_user.id
        
        # Send processing message
        processing_msg = await message.reply_text("📥 **Downloading image...**")
        
        # Download the image
        image_path = await message.download()
        
        # Store image path
        user_data[user_id] = {"image_path": image_path}
        
        # Create background selection keyboard
        keyboard = InlineKeyboardMarkup([
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
        ])
        
        await processing_msg.edit_text(
            "🎨 **Select background color:**",
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.reply_text("❌ Error processing image. Please try again.")

@app.on_callback_query()
async def handle_callback(client, callback_query):
    try:
        user_id = callback_query.from_user.id
        bg_color = callback_query.data
        
        if user_id not in user_data:
            await callback_query.answer("Session expired. Please send image again.", show_alert=True)
            return
        
        await callback_query.message.edit_text("🔄 **Removing background...**")
        
        # Process image with remove.bg API
        result = await remove_background(user_data[user_id]["image_path"], bg_color)
        
        if result:
            # Send the result
            await callback_query.message.reply_document(
                document=result,
                caption=f"✅ **Background removed!**\n🎨 Color: {bg_color.title()}",
                file_name=f"no_bg_{bg_color}.png"
            )
            await callback_query.message.delete()
        else:
            await callback_query.message.edit_text("❌ Failed to remove background. Please try another image.")
        
        # Cleanup
        if os.path.exists(user_data[user_id]["image_path"]):
            os.remove(user_data[user_id]["image_path"])
        del user_data[user_id]
        
        await callback_query.answer()
        
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await callback_query.message.edit_text("❌ Error processing image.")

async def remove_background(image_path: str, bg_color: str) -> BytesIO:
    """Remove background using remove.bg API"""
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
        
        with open(image_path, 'rb') as image_file:
            files = {'image_file': image_file}
            data = {'size': 'auto'}
            
            if bg_color_param:
                data['bg_color'] = bg_color_param
            
            headers = {'X-Api-Key': REMOVE_BG_API_KEY}
            
            # Make API request
            response = requests.post(url, files=files, data=data, headers=headers)
            
            if response.status_code == 200:
                # Create BytesIO object from response content
                result = BytesIO(response.content)
                result.name = f"no_bg_{bg_color}.png"
                return result
            else:
                logger.error(f"Remove.bg API error: {response.status_code} - {response.text}")
                return None
                
    except Exception as e:
        logger.error(f"Remove background error: {e}")
        return None

@app.on_message(filters.command("help"))
async def help_command(client, message: Message):
    await message.reply_text(
        "📖 **Help Guide**\n\n"
        "1. Send an image (as photo or file)\n"
        "2. Choose your preferred background color\n"
        "3. Download the processed image\n\n"
        "**Supported formats:** JPG, PNG, WebP\n"
        "**Max size:** 12MB\n\n"
        "Commands:\n"
        "/start - Start bot\n"
        "/help - Show this message"
    )

if __name__ == "__main__":
    print("🚀 Starting Background Remover Bot...")
    app.run()
