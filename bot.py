import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from config import Config
from database import Database
from file_manager import FileManager

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class TelegramFileBot:
    def __init__(self):
        self.db = Database()
        self.file_manager = FileManager()
        
        # Validate configuration
        Config.validate_config()
        
        # Create application
        self.application = Application.builder().token(Config.BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("help", self.help))
        self.application.add_handler(CommandHandler("myfiles", self.my_files))
        self.application.add_handler(CommandHandler("stats", self.stats))
        
        # Message handlers
        self.application.add_handler(MessageHandler(
            filters.Document.ALL | filters.PHOTO | filters.VIDEO | filters.AUDIO, 
            self.handle_file
        ))
        
        # Callback query handler for inline buttons
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # Text message handler for file descriptions
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, self.handle_text
        ))
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send welcome message when the command /start is issued."""
        try:
            user = update.effective_user
            self.db.add_user(user.id, user.username, user.first_name, user.last_name)
            
            welcome_text = f"""
👋 Hello {user.first_name}! Welcome to File Storage Bot!

📁 I can help you store and manage your files. Here's what I can do:

• 📤 Upload files (documents, images, videos, audio)
• 📥 Download your stored files
• 📊 View your storage statistics
• 🗑️ Delete files you no longer need

To get started, just send me any file!

Commands:
/start - Start the bot
/help - Show help message
/myfiles - List your stored files
/stats - Show your storage statistics
            """
            
            await update.message.reply_text(welcome_text)
        except Exception as e:
            logger.error(f"Error in start command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Send help message."""
        try:
            help_text = """
📖 **Help Guide**

**Uploading Files:**
Simply send me any file (document, image, video, or audio) and I'll store it for you.

**Managing Files:**
Use /myfiles to see all your stored files and manage them.

**File Types Supported:**
- Images: JPG, PNG, GIF, BMP
- Documents: PDF, DOC, DOCX, TXT
- Archives: ZIP, RAR, 7Z
- Audio: MP3, WAV, OGG
- Video: MP4, AVI, MKV

**Commands:**
/start - Start the bot
/help - Show this help message
/myfiles - List your stored files
/stats - Show storage statistics

**Note:** Maximum file size is 50MB.
            """
            await update.message.reply_text(help_text)
        except Exception as e:
            logger.error(f"Error in help command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_file(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming files."""
        try:
            user = update.effective_user
            
            # Store user in database
            self.db.add_user(user.id, user.username, user.first_name, user.last_name)
            
            # Determine file type and get file object
            if update.message.document:
                file = update.message.document
                file_name = file.file_name
            elif update.message.photo:
                file = update.message.photo[-1]  # Highest resolution
                file_name = f"photo_{file.file_id}.jpg"
            elif update.message.video:
                file = update.message.video
                file_name = f"video_{file.file_id}.mp4"
            elif update.message.audio:
                file = update.message.audio
                file_name = f"audio_{file.file_id}.mp3"
            else:
                await update.message.reply_text("❌ Unsupported file type.")
                return
            
            # Check file size
            if file.file_size > Config.MAX_FILE_SIZE:
                await update.message.reply_text(
                    f"❌ File too large. Maximum size is {self.file_manager.format_file_size(Config.MAX_FILE_SIZE)}"
                )
                return
            
            # Check if file type is allowed
            is_allowed, file_category = self.file_manager.is_file_allowed(file_name)
            if not is_allowed:
                await update.message.reply_text("❌ This file type is not supported.")
                return
            
            # Store description context for next message
            context.user_data['waiting_for_description'] = True
            context.user_data['pending_file'] = {
                'file_id': file.file_id,
                'file_name': file_name,
                'file_type': file.mime_type if hasattr(file, 'mime_type') else file_category,
                'file_size': file.file_size
            }
            
            keyboard = [[InlineKeyboardButton("Skip Description", callback_data="skip_description")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📝 Would you like to add a description for this file? "
                "Send me a text message or click 'Skip Description'.",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Error handling file: {e}")
            await update.message.reply_text("❌ An error occurred while processing your file.")
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (for file descriptions)."""
        try:
            user_data = context.user_data
            
            if user_data.get('waiting_for_description'):
                description = update.message.text
                pending_file = user_data['pending_file']
                
                # Add file to database
                file_db_id = self.db.add_file(
                    update.effective_user.id,
                    pending_file['file_id'],
                    pending_file['file_name'],
                    pending_file['file_type'],
                    pending_file['file_size'],
                    description
                )
                
                if file_db_id:
                    # Clear context
                    user_data['waiting_for_description'] = False
                    user_data['pending_file'] = None
                    
                    await update.message.reply_text(
                        f"✅ File stored successfully! (ID: {file_db_id})\n"
                        f"📝 Description: {description}"
                    )
                else:
                    await update.message.reply_text("❌ Failed to store file. Please try again.")
        except Exception as e:
            logger.error(f"Error handling text: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button clicks."""
        try:
            query = update.callback_query
            await query.answer()
            
            data = query.data
            user_id = query.from_user.id
            
            if data == "skip_description":
                user_data = context.user_data
                pending_file = user_data['pending_file']
                
                file_db_id = self.db.add_file(
                    user_id,
                    pending_file['file_id'],
                    pending_file['file_name'],
                    pending_file['file_type'],
                    pending_file['file_size']
                )
                
                if file_db_id:
                    user_data['waiting_for_description'] = False
                    user_data['pending_file'] = None
                    await query.edit_message_text(f"✅ File stored successfully! (ID: {file_db_id})")
                else:
                    await query.edit_message_text("❌ Failed to store file. Please try again.")
            
            elif data.startswith("view_files_"):
                page = int(data.split("_")[2])
                await self.show_user_files(query, user_id, page)
            
            elif data.startswith("delete_"):
                file_id = int(data.split("_")[1])
                if self.db.delete_file(file_id, user_id):
                    await query.edit_message_text("✅ File deleted successfully!")
                else:
                    await query.edit_message_text("❌ Failed to delete file.")
            
            elif data.startswith("download_"):
                file_id = int(data.split("_")[1])
                file_data = self.db.get_file(file_id, user_id)
                
                if file_data:
                    file_id, file_name, file_type = file_data
                    await context.bot.send_document(
                        chat_id=query.message.chat_id,
                        document=file_id,
                        caption=f"📄 {file_name}"
                    )
                else:
                    await query.edit_message_text("❌ File not found.")
        except Exception as e:
            logger.error(f"Error in button handler: {e}")
            try:
                await query.edit_message_text("❌ An error occurred. Please try again.")
            except:
                pass
    
    async def my_files(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user's stored files."""
        try:
            user_id = update.effective_user.id
            await self.show_user_files(update.message, user_id, page=1)
        except Exception as e:
            logger.error(f"Error in my_files command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def show_user_files(self, message, user_id, page=1):
        """Display user's files with pagination."""
        try:
            files = self.db.get_user_files(user_id)
            
            if not files:
                if hasattr(message, 'reply_text'):
                    await message.reply_text("📭 You haven't stored any files yet.")
                else:
                    await message.edit_message_text("📭 You haven't stored any files yet.")
                return
            
            items_per_page = 5
            total_pages = (len(files) + items_per_page - 1) // items_per_page
            start_idx = (page - 1) * items_per_page
            end_idx = start_idx + items_per_page
            
            current_files = files[start_idx:end_idx]
            
            text = f"📁 Your Stored Files (Page {page}/{total_pages}):\n\n"
            
            for file_id, file_name, file_type, file_size, upload_date, description in current_files:
                text += f"🆔 {file_id}\n"
                text += f"📄 {file_name}\n"
                text += f"📊 {self.file_manager.format_file_size(file_size)}\n"
                text += f"📅 {upload_date.split()[0]}\n"  # Show only date
                if description:
                    text += f"📝 {description}\n"
                text += "\n"
            
            # Create navigation buttons
            keyboard = []
            row_buttons = []
            
            for file_id, file_name, _, _, _, _ in current_files:
                row_buttons.append(InlineKeyboardButton(
                    f"📥 {file_id}", 
                    callback_data=f"download_{file_id}"
                ))
                row_buttons.append(InlineKeyboardButton(
                    f"🗑️ {file_id}", 
                    callback_data=f"delete_{file_id}"
                ))
                if len(row_buttons) >= 2:  # Two buttons per row
                    keyboard.append(row_buttons)
                    row_buttons = []
            
            # Add navigation buttons
            nav_buttons = []
            if page > 1:
                nav_buttons.append(InlineKeyboardButton(
                    "⬅️ Previous", 
                    callback_data=f"view_files_{page-1}"
                ))
            if page < total_pages:
                nav_buttons.append(InlineKeyboardButton(
                    "Next ➡️", 
                    callback_data=f"view_files_{page+1}"
                ))
            
            if nav_buttons:
                keyboard.append(nav_buttons)
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            if hasattr(message, 'reply_text'):
                await message.reply_text(text, reply_markup=reply_markup)
            else:
                await message.edit_message_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error showing user files: {e}")
            if hasattr(message, 'reply_text'):
                await message.reply_text("❌ An error occurred while loading your files.")
            else:
                await message.edit_message_text("❌ An error occurred while loading your files.")
    
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user storage statistics."""
        try:
            user_id = update.effective_user.id
            file_count, total_size = self.db.get_file_stats(user_id)
            
            if file_count is None:
                file_count = 0
                total_size = 0
            
            stats_text = f"""
📊 **Your Storage Statistics**

📁 Total Files: {file_count}
💾 Total Size: {self.file_manager.format_file_size(total_size or 0)}
📏 Max File Size: {self.file_manager.format_file_size(Config.MAX_FILE_SIZE)}

💡 Tips:
- You can store various file types
- Maximum file size is 50MB
- Use /myfiles to manage your files
            """
            
            await update.message.reply_text(stats_text)
        except Exception as e:
            logger.error(f"Error in stats command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    def run(self):
        """Start the bot with better error handling."""
        logger.info("🤖 File Storage Bot is starting...")
        
        try:
            # Test database connection
            self.db.get_connection().close()
            logger.info("✅ Database connection successful!")
            
            # Start the bot
            self.application.run_polling(
                drop_pending_updates=True,
                allowed_updates=Update.ALL_TYPES,
                timeout=30
            )
        except Exception as e:
            logger.error(f"❌ Error starting bot: {e}")
            raise
