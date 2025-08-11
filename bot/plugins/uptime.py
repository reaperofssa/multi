# plugins/uptime.py
# Perfect Uptime plugin for Multi-Session UserBot by Reiker

from telethon import events
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

async def setup(client, user_id):
    """Setup plugin handlers for the client"""
    
    # Get the current user's Telegram ID for validation
    me = await client.get_me()
    telegram_user_id = me.id
    
    @client.on(events.NewMessage(pattern=r'^!uptime$', outgoing=True))
    async def uptime_handler(event):
        """Uptime command - shows how long the bot has been running"""
        if event.sender_id != telegram_user_id:
            return
        
        try:
            # Import here to avoid circular imports
            import __main__
            
            # Get bot start time from main module
            if hasattr(__main__, 'bot_start_time') and __main__.bot_start_time:
                start_time = __main__.bot_start_time
            else:
                # Fallback: estimate based on when this session was created
                start_time = datetime.now()
                logger.warning(f"Could not get bot start time for user {user_id}, using current time")
            
            now = datetime.now()
            uptime_delta = now - start_time
            
            # Break down uptime into days, hours, minutes, seconds
            days = uptime_delta.days
            hours, remainder = divmod(uptime_delta.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            # Format uptime string elegantly
            uptime_parts = []
            if days > 0:
                uptime_parts.append(f"{days}d")
            if hours > 0:
                uptime_parts.append(f"{hours}h")
            if minutes > 0:
                uptime_parts.append(f"{minutes}m")
            if seconds > 0 or not uptime_parts:  # Show seconds if it's the only unit or very short uptime
                uptime_parts.append(f"{seconds}s")
            
            uptime_str = " ".join(uptime_parts)
            
            # Calculate some additional stats
            total_seconds = int(uptime_delta.total_seconds())
            
            uptime_msg = f"""⏳ **Bot Uptime Report**

🚀 **Started:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}
⏱️ **Running for:** {uptime_str}
🕐 **Current time:** {now.strftime('%Y-%m-%d %H:%M:%S')}

📊 **Statistics:**
• Total seconds: {total_seconds:,}
• Total minutes: {total_seconds//60:,}
• Total hours: {total_seconds//3600:,}

🤖 **Session:** {me.first_name}'s UserBot
🔢 **Session ID:** {user_id}

✨ **Finral Multi Session**"""
            
            await event.respond(uptime_msg)
            logger.info(f"User {user_id} (TG: {event.sender_id}) checked uptime: {uptime_str}")
            
        except Exception as e:
            logger.error(f"Error in uptime command for user {user_id}: {e}")
            await event.respond(f"❌ Error calculating uptime: {str(e)}")
    
    @client.on(events.NewMessage(pattern=r'^!botinfo$', outgoing=True))
    async def botinfo_handler(event):
        """Bot info command - shows detailed bot information"""
        if event.sender_id != telegram_user_id:
            return
        
        try:
            import __main__
            
            # Get various bot stats
            if hasattr(__main__, 'bot_start_time') and __main__.bot_start_time:
                start_time = __main__.bot_start_time
                uptime_delta = datetime.now() - start_time
                uptime_str = f"{uptime_delta.days}d {uptime_delta.seconds//3600}h {(uptime_delta.seconds%3600)//60}m"
            else:
                uptime_str = "Unknown"
            
            # Get session count if available
            session_count = "Unknown"
            if hasattr(__main__, 'user_sessions'):
                session_count = len(__main__.user_sessions)
            
            # Get bot pause status
            bot_status = "Unknown"
            if hasattr(__main__, 'bot_paused'):
                bot_status = "Paused" if __main__.bot_paused else "Active"
            
            botinfo_msg = f"""🧃 **Finral UserBot Info**

📋 **Bot Details:**
• Name: Multi-Session UserBot
• Created by: Reiker 🚀
• Version: 1.0
• Status: {bot_status}

📊 **Statistics:**
• Uptime: {uptime_str}
• Total sessions: {session_count}
• Your session ID: {user_id}

👤 **Your Account:**
• Name: {me.first_name} {me.last_name or ''}
• Username: @{me.username or 'None'}
• Telegram ID: {telegram_user_id}

🎯 **Features:**
• Multi-session support
• Plugin system
• Session isolation
• Command validation

💡 **Commands:** Use !help to see available commands"""
            
            await event.respond(botinfo_msg)
            logger.info(f"User {user_id} (TG: {event.sender_id}) checked bot info")
            
        except Exception as e:
            logger.error(f"Error in botinfo command for user {user_id}: {e}")
            await event.respond(f"❌ Error getting bot info: {str(e)}")
    
    logger.info(f"Uptime plugin loaded for user {user_id} (Telegram ID: {telegram_user_id})")
