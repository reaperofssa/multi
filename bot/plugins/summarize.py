"""
Summarize Plugin for Multi-Session UserBot
Responds to !summarize <text> or !summarize as a reply to a message
Uses the same AI API as !ai
"""

import requests
from telethon import events
import urllib.parse

async def setup(client, user_id):
    """Initialize the summarize plugin"""

    @client.on(events.NewMessage(pattern=r'^!summarize(?:\s+(.+))?', outgoing=True))
    async def summarize_handler(event):
        try:
            query = event.pattern_match.group(1)

            # If no query, check if replying to a message
            if not query and event.is_reply:
                reply_msg = await event.get_reply_message()
                query = reply_msg.text

            if not query:
                await event.reply("❌ Please provide text to summarize or reply to a message.")
                return

            # Show thinking message
            thinking_msg = await event.reply("📝 Summarizing...")

            # Prepare summarization query for the AI
            summarize_prompt = f"Summarize this text in a concise way:\n{query}"
            encoded_query = urllib.parse.quote(summarize_prompt)

            # API call
            url = f"https://apis.davidcyriltech.my.id/ai/chatbot?query={encoded_query}"
            response = requests.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    summary = data.get("result", "No response")
                    await thinking_msg.edit(summary)
                    return

            # If failed, remove thinking message silently
            await thinking_msg.delete()

        except:
            try:
                await thinking_msg.delete()
            except:
                pass

    print(f"✅ Summarize plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
