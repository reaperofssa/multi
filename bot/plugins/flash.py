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
            
            # Send initial message to measure response time
            sent_msg = await event.respond("⚡️ Calculating speed...")
            
            # Calculate response time
            end_time = time.time()
            response_time_ms = round((end_time - start_time) * 1000)
            
            # Edit the message with the speed result
            await sent_msg.edit(f"⚡️ Speed {response_time_ms} Ms")
            
        except Exception as e:
            await event.respond(f"❌ Error: {str(e)}")
    
    print(f"✅ Flash plugin loaded for user {user_id}")

# Alternative initialization method (for compatibility)
async def init_plugin(client, user_id):
    """Alternative plugin initialization"""
    await setup(client, user_id)
