"""
Uptime Plugin for Multi-Session UserBot
Responds to !uptime command with bot uptime and system information
"""

import time
import platform
import psutil
import os
from datetime import datetime, timedelta
from telethon import events

# Store session start time for each user
session_start_times = {}

def get_system_info():
    """Get system information"""
    try:
        # Get system info
        system = platform.system()
        machine = platform.machine()
        python_version = platform.python_version()
        
        # Get CPU info
        cpu_count = psutil.cpu_count()
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Get memory info
        memory = psutil.virtual_memory()
        memory_total = round(memory.total / (1024**3), 1)  # GB
        memory_used = round(memory.used / (1024**3), 1)   # GB
        memory_percent = memory.percent
        
        # Get disk info
        disk = psutil.disk_usage('/')
        disk_total = round(disk.total / (1024**3), 1)  # GB
        disk_used = round(disk.used / (1024**3), 1)   # GB
        disk_percent = round((disk.used / disk.total) * 100, 1)
        
        return {
            'system': system,
            'machine': machine,
            'python_version': python_version,
            'cpu_count': cpu_count,
            'cpu_percent': cpu_percent,
            'memory_total': memory_total,
            'memory_used': memory_used,
            'memory_percent': memory_percent,
            'disk_total': disk_total,
            'disk_used': disk_used,
            'disk_percent': disk_percent
        }
    except Exception as e:
        return None

def format_uptime(seconds):
    """Format uptime in a readable format"""
    if seconds < 60:
        return f"{int(seconds)} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    elif seconds < 86400:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{hours}h {minutes}m"
    else:
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        return f"{days}d {hours}h {minutes}m"

# Plugin setup function
async def setup(client, user_id):
    """Initialize the uptime plugin"""
    
    # Record session start time for this user
    session_start_times[user_id] = time.time()
    
    @client.on(events.NewMessage(pattern=r'^!uptime', outgoing=True))
    async def uptime_handler(event):
        """Handle !uptime command"""
        try:
            # Calculate uptime
            current_time = time.time()
            start_time = session_start_times.get(user_id, current_time)
            uptime_seconds = current_time - start_time
            
            # Format uptime
            uptime_str = format_uptime(uptime_seconds)
            
            # Get current datetime
            current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Get system information
            sys_info = get_system_info()
            
            if sys_info:
                # Create detailed uptime message with system info
                uptime_message = f"""🕐 **Finral** Status Report

⏰ **Session Uptime:** {uptime_str}
📅 **Current Time:** {current_datetime}
🟢 **Status:** Online

🖥️ **System Info:**
• **OS:** {sys_info['system']} {sys_info['machine']}
• **Python:** v{sys_info['python_version']}

💾 **Resources:**
• **CPU:** {sys_info['cpu_count']} cores ({sys_info['cpu_percent']}%)
• **RAM:** {sys_info['memory_used']}GB / {sys_info['memory_total']}GB ({sys_info['memory_percent']}%)
• **Disk:** {sys_info['disk_used']}GB / {sys_info['disk_total']}GB ({sys_info['disk_percent']}%)"""
            else:
                # Fallback message if system info fails
                uptime_message = f"""🕐 **Finral** Status Report

⏰ **Session Uptime:** {uptime_str}
📅 **Current Time:** {current_datetime}
🟢 **Status:** Online

⚠️ System info unavailable"""
            
            # Reply to the command message
            await event.reply(uptime_message)
            
        except Exception as e:
            await event.reply(f"❌ **Finral** Error: {str(e)}")
    
    print(f"✅ Uptime plugin loaded for user {user_id}")

# Alternative initialization method (for compatibility)
async def init_plugin(client, user_id):
    """Alternative plugin initialization"""
    await setup(client, user_id)
