"""
Quote Plugin for Multi-Session UserBot
Responds to !quote command with a random quote from ZenQuotes API
"""

import requests
from telethon import events

# Plugin setup function
async def setup(client, user_id):
    """Initialize the quote plugin"""

    @client.on(events.NewMessage(pattern=r'^!quote', outgoing=True))
    async def quote_handler(event):
        """Handle !quote command"""
        try:
            # Reply to indicate fetching
            sent_msg = await event.reply("💬 Fetching quote...")

            # Fetch quote from ZenQuotes API
            response = requests.get("https://zenquotes.io/api/random", timeout=10)
            if response.status_code != 200:
                await sent_msg.edit("❌ Error: Failed to fetch quote.")
                return

            data = response.json()
            quote_text = data[0]["q"]
            quote_author = data[0]["a"]

            # Edit the message with the quote
            await sent_msg.edit(f"💬 **{quote_text}**\n— *{quote_author}*")

        except Exception as e:
            await event.reply(f"❌ Error: {str(e)}")

    print(f"✅ Quote plugin loaded for user {user_id}")

# Alternative initialization method (for compatibility)
async def init_plugin(client, user_id):
    """Alternative plugin initialization"""
    await setup(client, user_id)
