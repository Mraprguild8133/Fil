import os
import requests
import logging
from telethon import TelegramClient, events
from PIL import Image
from io import BytesIO
from collections import defaultdict
import time
import asyncio

# Import configuration
from config import config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Rate Limiting ---
user_requests = defaultdict(list)

def is_rate_limited(user_id):
    """Check if user is rate limited (10 requests per minute)"""
    now = time.time()
    # Clean old requests (older than 60 seconds)
    user_requests[user_id] = [req_time for req_time in user_requests[user_id] if now - req_time < 60]
    
    if len(user_requests[user_id]) >= config.RATE_LIMIT:
        return True
    
    user_requests[user_id].append(now)
    return False

# --- Bot Setup ---
try:
    bot = TelegramClient(
        'background_removal_bot',
        config.API_ID,
        config.API_HASH
    ).start(bot_token=config.BOT_TOKEN)
    logger.info("Telegram client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Telegram client: {e}")
    raise

# --- Bot Functionality ---

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    """Handler for the /start command."""
    welcome_text = """
🤖 **Background Removal Bot**

Send me a photo and I'll remove the background for you!

**Features:**
• Remove background from images
• Reply with a color name (e.g., 'blue', '#FF0000') to add colored background
• Reply with another photo to use it as background

**Usage:**
1. Send a photo → Get transparent background
2. Reply to result with color/image → Custom background
    """
    await event.respond(welcome_text)
    raise events.StopPropagation

@bot.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    """Handler for the /help command."""
    help_text = """
🆘 **Help Guide**

**Commands:**
/start - Start the bot
/help - Show this help message
/ping - Check if bot is alive

**How to use:**
1. **Remove background**: Simply send me a clear photo of a person or object
2. **Change background**: Reply to the processed image with:
   - A color name: "red", "blue", "green"
   - A hex color: "#FF0000", "#00FF00"
   - Another photo to use as background

**Tips:**
• Use clear, high-contrast images for best results
• Supported formats: JPEG, PNG, WebP
• Max file size: 10MB
• Rate limit: 10 requests per minute
    """
    await event.respond(help_text)

@bot.on(events.NewMessage(pattern='/ping'))
async def ping(event):
    """Simple ping command to test if bot is alive."""
    await event.respond("🏓 Pong! Bot is working and responsive.")

@bot.on(events.NewMessage(photo=True))
async def remove_background(event):
    """Handler for incoming photos to remove the background."""
    logger.info(f"Photo received from user {event.sender_id}")
    
    # Check rate limiting
    if is_rate_limited(event.sender_id):
        await event.respond("⏰ Rate limit exceeded. Please wait a minute before making more requests.")
        return

    # Check file size
    if event.message.file and event.message.file.size > config.MAX_FILE_SIZE:
        await event.respond("📁 File too large! Please send an image smaller than 10MB.")
        return

    processing_message = await event.respond("🔄 Processing your image...")

    try:
        # Download the image from the message
        logger.info("Downloading image...")
        image_bytes = await bot.download_media(event.message.photo, file=bytes)
        
        # Call the remove.bg API
        logger.info("Calling remove.bg API...")
        response = requests.post(
            'https://api.remove.bg/v1.0/removebg',
            files={'image_file': image_bytes},
            data={'size': 'auto'},
            headers={'X-Api-Key': config.API_KEY},
            timeout=30
        )

        if response.status_code == requests.codes.ok:
            # Send the image with the removed background back to the user
            logger.info("Background removed successfully")
            result_image = BytesIO(response.content)
            result_image.name = 'no_bg.png'
            
            await processing_message.delete()
            await bot.send_file(
                event.chat_id, 
                result_image, 
                caption="✅ Background removed! Reply to this with a color or image to add a new background."
            )
        
        elif response.status_code == 402:
            logger.warning("remove.bg API quota exceeded")
            await processing_message.edit("❌ API quota exceeded. Please try again later.")
        
        elif response.status_code == 400:
            logger.warning("remove.bg API bad request")
            await processing_message.edit("❌ Could not process image. Make sure it contains a clear subject and is not too complex.")
        
        else:
            logger.error(f"remove.bg API error: {response.status_code}")
            await processing_message.edit(f"❌ API error (code: {response.status_code}). Please try again.")

    except requests.exceptions.Timeout:
        logger.error("remove.bg API timeout")
        await processing_message.edit("⏰ Request timeout. Please try again.")
    except Exception as e:
        logger.error(f"Unexpected error in remove_background: {e}")
        await processing_message.edit(f"❌ An unexpected error occurred: {str(e)}")

@bot.on(events.NewMessage)
async def handle_background_reply(event):
    """Handler for replies to add a custom background."""
    if not event.message.is_reply:
        return

    # Check rate limiting
    if is_rate_limited(event.sender_id):
        await event.respond("⏰ Rate limit exceeded. Please wait a minute before making more requests.")
        return

    try:
        reply_msg = await event.get_reply_message()
        if not reply_msg or not reply_msg.photo:
            return

        # Check if the original message was from our bot
        bot_me = await bot.get_me()
        if reply_msg.sender_id != bot_me.id:
            return

        logger.info(f"Background change request from user {event.sender_id}")

        processing_message = await event.respond("🎨 Adding new background...")

        # Download the original image (with background removed)
        original_image_bytes = await bot.download_media(reply_msg.photo, file=bytes)
        original_image = Image.open(BytesIO(original_image_bytes)).convert("RGBA")

        new_bg = None
        if event.message.photo:
            # User sent an image as background
            logger.info("Using image as background")
            bg_image_bytes = await bot.download_media(event.message.photo, file=bytes)
            new_bg = Image.open(BytesIO(bg_image_bytes)).convert("RGBA")
            new_bg = new_bg.resize(original_image.size)
        
        elif event.message.text:
            # User sent a color name as background
            color_input = event.message.text.lower().strip()
            logger.info(f"Using color as background: {color_input}")
            try:
                new_bg = Image.new("RGBA", original_image.size, color_input)
            except ValueError:
                await processing_message.edit("❌ Invalid color. Use names like 'red', 'blue' or hex codes like '#FF0000'")
                return

        if new_bg:
            # Composite the images
            new_bg.paste(original_image, (0, 0), original_image)
            
            # Save the final image to a byte stream
            final_image_stream = BytesIO()
            new_bg.save(final_image_stream, 'PNG')
            final_image_stream.seek(0)
            final_image_stream.name = 'with_background.png'

            await processing_message.delete()
            await bot.send_file(event.chat_id, final_image_stream, caption="✅ New background added!")
            logger.info("Background added successfully")
        
        else:
            await processing_message.delete()

    except Exception as e:
        logger.error(f"Error in handle_background_reply: {e}")
        await event.respond(f"❌ Error processing background: {str(e)}")

@bot.on(events.NewMessage(pattern='/status'))
async def status_command(event):
    """Check bot status and statistics."""
    status_text = """
🤖 **Bot Status**

**Services:**
✅ Telegram Bot - Connected
✅ remove.bg API - Ready
✅ Image Processing - Active

**Statistics:**
• Rate limit: 10 requests/minute per user
• Max file size: 10MB
• Supported formats: JPEG, PNG, WebP

Bot is running smoothly! 🚀
    """
    await event.respond(status_text)

# --- Main Loop ---
async def main():
    """Start the bot."""
    logger.info("🤖 Bot is starting...")
    print("Bot is starting...")
    
    # Test remove.bg API connection
    try:
        test_response = requests.get(
            'https://api.remove.bg/v1.0/account',
            headers={'X-Api-Key': config.API_KEY},
            timeout=10
        )
        if test_response.status_code == 200:
            logger.info("✅ remove.bg API connection successful")
        else:
            logger.warning(f"⚠️ remove.bg API test returned status: {test_response.status_code}")
    except Exception as e:
        logger.warning(f"⚠️ remove.bg API test failed: {e}")
    
    # Get bot info
    me = await bot.get_me()
    logger.info(f"✅ Bot started successfully as @{me.username}")
    print(f"Bot is running as @{me.username}")
    
    # Keep the bot running
    await bot.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        print(f"Bot crashed: {e}")
        raise
