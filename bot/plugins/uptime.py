"""
Enhanced Uptime Plugin for Multi-Session UserBot
Responds to !uptime command with bot uptime, ping speed, and session info
"""

import time
import platform
import psutil
from telethon import events

# Store bot start time
start_time = time.time()

# Plugin setup function
async def setup(client, user_id):
    """Initialize the uptime plugin"""
    
    @client.on(events.NewMessage(pattern=r'^!uptime', outgoing=True))
    async def uptime_handler(event):
        """Handle !uptime command"""
        try:
            # Measure response speed
            ping_start = time.time()
            # We'll just simulate a quick send/edit for speed calc
            ping_msg = await event.respond("Calculating...")
            ping_end = time.time()
            ping_ms = round((ping_end - ping_start) * 1000)

            # Calculate uptime
            uptime_seconds = int(time.time() - start_time)
            days, remainder = divmod(uptime_seconds, 86400)
            hours, remainder = divmod(remainder, 3600)
            minutes, seconds = divmod(remainder, 60)
            uptime_str = (
                f"{days}d {hours}h {minutes}m {seconds}s"
                if days > 0 else
                f"{hours}h {minutes}m {seconds}s"
            )

            # Get system info
            cpu_percent = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            mem_percent = mem.percent
            python_ver = platform.python_version()
            sys_name = platform.system()
            sys_release = platform.release()

            # Create formatted message
            msg = (
                f"**⛈️ Finral Status**\n"
                f"⏳ **Uptime:** {uptime_str}\n"
                f"⚡ **Ping:** {ping_ms} ms\n"
                f"💻 **System:** {sys_name} {sys_release}\n"
                f"🐍 **Python:** {python_ver}\n"
                f"🖥 **CPU Usage:** {cpu_percent}%\n"
                f"📦 **RAM Usage:** {mem_percent}%"
            )

            # Edit the original ping message to show the result
            await ping_msg.edit(msg)

        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")
    
    print(f"✅ Enhanced uptime plugin loaded for user {user_id}")

# Alternative initialization method (for compatibility)
async def init_plugin(client, user_id):
    """Alternative plugin initialization"""
    await setup(client, user_id)
