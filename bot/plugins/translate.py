"""
Translate Plugin for Multi-Session UserBot
Responds to !translate <text> or !translate as a reply to a message
Auto-detects language and translates to English using Google Translate API
"""

import requests
from telethon import events
import urllib.parse

async def setup(client, user_id):
    """Initialize the translate plugin"""

    @client.on(events.NewMessage(pattern=r'^!translate(?:\s+(.+))?', outgoing=True))
    async def translate_handler(event):
        try:
            query = event.pattern_match.group(1)

            # If no query, check if replying to a message
            if not query and event.is_reply:
                reply_msg = await event.get_reply_message()
                query = reply_msg.text

            if not query:
                await event.reply("❌ Please provide text or reply to a message to translate.")
                return

            # Show translating message
            translating_msg = await event.reply("🌐 Translating...")

            # Prepare Google Translate request
            encoded_text = urllib.parse.quote(query)
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={encoded_text}"

            response = requests.get(url, timeout=15)

            if response.status_code == 200:
                data = response.json()
                translated_text = "".join([item[0] for item in data[0]])
                detected_lang = data[2]

                await translating_msg.edit(f"**Translated from {detected_lang.upper()} → EN:**\n{translated_text}")
                return

            # If failed, remove translating message silently
            await translating_msg.delete()

        except:
            try:
                await translating_msg.delete()
            except:
                pass

    print(f"✅ Translate plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
