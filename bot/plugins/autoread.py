from telethon import events

# Keep session state for auto-read per user
AUTOREAD_CHAT_STATE = {}

async def setup(client, user_id):
    """Initialize the Auto-Read Chat plugin"""

    # Default state per user
    if user_id not in AUTOREAD_CHAT_STATE:
        AUTOREAD_CHAT_STATE[user_id] = False

    @client.on(events.NewMessage(pattern=r'^!autoreadchats\s+(on|off)', outgoing=True))
    async def autoread_chats_toggle(event):
        arg = event.pattern_match.group(1).lower()
        if arg == "on":
            AUTOREAD_CHAT_STATE[user_id] = True
            await event.reply("✅ Auto-read chats enabled for this session.")
        elif arg == "off":
            AUTOREAD_CHAT_STATE[user_id] = False
            await event.reply("❌ Auto-read chats disabled for this session.")

    @client.on(events.NewMessage)
    async def auto_read_chats(event):
        if AUTOREAD_CHAT_STATE.get(user_id):
            try:
                await client.send_read_acknowledge(event.chat_id)
            except:
                pass  # ignore errors for channels, bots, etc.

    print(f"✅ Auto-Read Chat plugin loaded for user {user_id}")
