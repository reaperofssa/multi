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

# Validate BOT_TOKEN
if not BOT_TOKEN:
    print("❌ Error: BOT_TOKEN not found in environment variables")
    print("Please create a .env file with BOT_TOKEN=your_token_here")
    sys.exit(1)

# Files
USERS_FILE = "users.json"
PLUGINS_DIR = "plugins"

# Global storage
user_sessions = {}
pending_connections = {}
bot_paused = False
bot_start_time = None  # Will be set when bot starts

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
            try:
                plugin_name = os.path.basename(plugin_file)[:-3]  # Remove .py
                spec = importlib.util.spec_from_file_location(plugin_name, plugin_file)
                plugin = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(plugin)
                
                # Initialize plugin with client and user validation
                if hasattr(plugin, 'setup'):
                    await plugin.setup(self.client, self.user_id)
                    logger.info(f"Loaded plugin {plugin_name} for user {self.user_id}")
                elif hasattr(plugin, 'init_plugin'):
                    # Alternative plugin initialization method
                    await plugin.init_plugin(self.client, self.user_id)
                    logger.info(f"Loaded plugin {plugin_name} for user {self.user_id}")
            except Exception as e:
                logger.error(f"Error loading plugin {plugin_file}: {e}")
    
    async def disconnect(self):
        """Disconnect user's client"""
        if self.client:
            await self.client.disconnect()
        self.is_active = False

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
    
    welcome_msg = """🤖 **Multi-Session UserBot by Reiker**

📝 **Available Commands:**
• `/connect` - Connect your Telegram account
• `/replace` - Replace your current session
• `/delete` - Delete your connection
• `/health` - Check your connection status
• `/pause` - Pause bot responses
• `/restart` - Restart bot responses

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
        
        health_msg = f"""✅ **Connection Status: {'Healthy' if session.is_active else 'Inactive'}**

👤 **Account:** {me.username or me.first_name}
🆔 **User ID:** {me.id}
📱 **API ID:** {session.api_id}

📊 **Status:**
• Connection: {'Active' if session.is_active else 'Inactive'}
• Bot Status: {'Paused' if bot_paused else 'Active'}
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
        
    help_msg = """🤖 **Multi-Session UserBot by Reiker - Help**

🔧 **Setup Commands:**
• `/connect` - Connect your Telegram account
• `/replace` - Replace current connection
• `/delete` - Delete your connection
• `/health` - Check connection status and ping

⚡ **Control Commands:**
• `/pause` - Pause all bot responses
• `/restart` - Resume bot responses

🎯 **UserBot Features:**
• Send `!ping` from your connected account to get `pong` response
• Multi-session support (multiple users can connect)
• Plugin system for custom commands
• Real-time connection monitoring

🔌 **Plugin System:**
• Place Python files in `/plugins` folder
• Plugins are automatically loaded for each session
• Each plugin can add custom commands and handlers

💡 **Tips:**
• 🔒 Bot only works in private messages
• Must join required channel to use bot
• Use `/health` to check connection and test ping
• Session files from @tgpairbot work perfectly
• Bot responses can be paused/resumed globally

Created by Reiker 🚀"""
    
    await send_long_message(update, context, help_msg)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle connection process messages and file uploads"""
    if not is_private_chat(update):
        return  # Ignore in groups/channels
    
    # Check force join for connection process
    if not await check_force_join(update, context):
        await update.message.reply_text(
            f"🔒 **Access Required**\n\n"
            f"To use this bot, you must first join our channel:\n"
            f"👉 {FORCE_JOIN_CHANNEL}",
            parse_mode='Markdown'
        )
        return
        
    user_id = update.effective_user.id
    
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
    print("🚀 Starting Multi-Session UserBot by Reiker...")
    
    # Create plugins directory if not exists
    if not os.path.exists(PLUGINS_DIR):
        os.makedirs(PLUGINS_DIR)
        print(f"📁 Created plugins directory: {PLUGINS_DIR}")
    
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
