"""
Flash Speed Plugin for Multi-Session UserBot
Responds to !flash command with speed measurement and formats speed as a blockquote
"""

import time
from telethon import events
from telethon.extensions import markdown
from telethon import types
from telethon.tl.types import (
    MessageEntityCustomEmoji,
    MessageEntitySpoiler,
    MessageEntityTextUrl,
    MessageEntityBlockquote,
    MessageEntityItalic,
    MessageEntityUnderline,
    MessageEntityCode,
    MessageEntityStrike,
    MessageEntityBold,
    MessageEntityPre,
)

class AaycoBot:
    @staticmethod
    def parse(text):
        text, entities = markdown.parse(text)
        for i, e in enumerate(entities):
            if isinstance(e, MessageEntityTextUrl) and e.url.startswith('tg://emoji?id='):
                entities[i] = MessageEntityCustomEmoji(e.offset, e.length, int(e.url.split('=')[1]))
            elif isinstance(e, MessageEntityTextUrl) and e.url == 'spoiler':
                entities[i] = types.MessageEntitySpoiler(e.offset, e.length)
            elif isinstance(e, MessageEntityTextUrl) and e.url == 'quote':
                entities[i] = types.MessageEntityBlockquote(e.offset, e.length)
            elif isinstance(e, MessageEntityTextUrl) and e.url == 'italic':
                entities[i] = types.MessageEntityItalic(e.offset, e.length)
            elif isinstance(e, MessageEntityTextUrl) and e.url == 'underline':
                entities[i] = types.MessageEntityUnderline(e.offset, e.length)
            elif isinstance(e, MessageEntityTextUrl) and e.url == 'code':
                entities[i] = types.MessageEntityCode(e.offset, e.length)
            elif isinstance(e, MessageEntityTextUrl) and e.url == 'strike':
                entities[i] = types.MessageEntityStrike(e.offset, e.length)
            elif isinstance(e, MessageEntityTextUrl) and e.url == 'bold':
                entities[i] = types.MessageEntityBold(e.offset, e.length)
            elif isinstance(e, MessageEntityTextUrl) and e.url.startswith('pre:'):
                entities[i] = MessageEntityPre(e.offset, e.length, str(e.url.split(':')[1]))
        return text, entities

    @staticmethod
    def unparse(text, entities):
        for i, e in enumerate(entities or []):
            if isinstance(e, MessageEntityCustomEmoji):
                entities[i] = MessageEntityTextUrl(e.offset, e.length, f'tg://emoji?id={e.document_id}')
            elif isinstance(e, types.MessageEntitySpoiler):
                entities[i] = types.MessageEntityTextUrl(e.offset, e.length, 'spoiler')
            elif isinstance(e, MessageEntityBlockquote):
                entities[i] = types.MessageEntityTextUrl(e.offset, e.length, 'quote')
            elif isinstance(e, MessageEntityItalic):
                entities[i] = types.MessageEntityTextUrl(e.offset, e.length, 'italic')
            elif isinstance(e, MessageEntityUnderline):
                entities[i] = types.MessageEntityTextUrl(e.offset, e.length, 'underline')
            elif isinstance(e, MessageEntityCode):
                entities[i] = types.MessageEntityTextUrl(e.offset, e.length, 'code')
            elif isinstance(e, MessageEntityStrike):
                entities[i] = types.MessageEntityTextUrl(e.offset, e.length, 'strike')
            elif isinstance(e, MessageEntityBold):
                entities[i] = types.MessageEntityTextUrl(e.offset, e.length, 'bold')
            elif isinstance(e, MessageEntityPre):
                entities[i] = MessageEntityTextUrl(e.offset, e.length, f'pre:{e.language}')
        return markdown.unparse(text, entities)

# Plugin setup function
async def setup(client, user_id):
    """Initialize the flash plugin"""

    # Set custom parse mode to enable your markdown entities
    client.parse_mode = AaycoBot()

    @client.on(events.NewMessage(pattern=r'^!flash', outgoing=True))
    async def flash_handler(event):
        """Handle !flash command"""
        try:
            start_time = time.time()

            sent_msg = await event.reply("⚡️ Calculating speed...")

            end_time = time.time()
            response_time_ms = round((end_time - start_time) * 1000)

            # Use your custom markdown to make the speed a blockquote
            text = f"⚡️ **Finral** Speed [{response_time_ms} ms](quote)"

            await sent_msg.edit(text)

        except Exception as e:
            await event.reply(f"❌ **Finral** Error: {str(e)}")

    print(f"✅ Flash plugin loaded for user {user_id}")

# Alternative initialization method (for compatibility)
async def init_plugin(client, user_id):
    """Alternative plugin initialization"""
    await setup(client, user_id)
