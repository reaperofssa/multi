"""
Flash Speed Plugin for Multi-Session UserBot
Responds to !flash command with speed measurement
"""

import time
from telethon import events
import asyncio

# Plugin setup function
async def setup(client, user_id):
    """Initialize the flash plugin"""
    
    @client.on(events.NewMessage(pattern=r'^!flash', outgoing=True))
    async def flash_handler(event):
        """Handle !flash command"""
        try:
            # Record start time
            start_time = time.time()
            
            # Reply to the command message
            sent_msg = await event.reply("⚡️ Calculating speed...")
            
            # Calculate response time
            end_time = time.time()
            response_time_ms = round((end_time - start_time) * 1000)
            
            # Edit the reply with the speed result and bot name
            await sent_msg.edit(f"⚡️ **Finral** Speed {response_time_ms} Ms")
            
        except Exception as e:
            await event.reply(f"❌ **Finral** Error: {str(e)}")
    
    print(f"✅ Flash plugin loaded for user {user_id}")

# Alternative initialization method (for compatibility)
async def init_plugin(client, user_id):
    """Alternative plugin initialization"""
    await setup(client, user_id)
