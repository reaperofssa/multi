"""
AI Chat Plugin for Multi-Session UserBot
Responds to !ai <query> or !ai as a reply to a message
"""

import requests
from telethon import events
import urllib.parse

async def setup(client, user_id):
    """Initialize the AI plugin"""

    @client.on(events.NewMessage(pattern=r'^!ai(?:\s+(.+))?', outgoing=True))
    async def ai_handler(event):
        try:
            query = event.pattern_match.group(1)

            # If no query, check if replying to a message
            if not query and event.is_reply:
                reply_msg = await event.get_reply_message()
                query = reply_msg.text

            if not query:
                await event.reply("❌ Please provide a query or reply to a message.")
                return

            # Show thinking message (this will be edited later)
            thinking_msg = await event.reply("🤖 Thinking...")

            # API request
            encoded_query = urllib.parse.quote(query)
            url = f"https://apis.davidcyriltech.my.id/ai/chatbot?query={encoded_query}"
            response = requests.get(url, timeout=15)

            # Validate response
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    ai_text = data.get("result", "No response")
                    await thinking_msg.edit(ai_text)
                    return

            # If something went wrong, just delete the thinking message
            await thinking_msg.delete()

        except:
            # Silently fail without sending errors to chat
            try:
                await thinking_msg.delete()
            except:
                pass

    print(f"✅ AI plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
