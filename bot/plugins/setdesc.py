"""
Finral Set Description Plugin for Multi-Session UserBot
Usage:
    !setdesc <your new bio>
    OR
    Reply to a message with !setdesc to use that message as your bio.
"""

from telethon import events
from telethon.tl.functions.account import UpdateProfileRequest

# Plugin setup function
async def setup(client, user_id):
    """Initialize the set description plugin"""

    @client.on(events.NewMessage(pattern=r'^!setdesc(?:\s+(.+))?$', outgoing=True))
    async def setdesc_handler(event):
        """Handle !setdesc command"""
        try:
            new_bio = event.pattern_match.group(1)

            # If no bio in command, check if it's a reply
            if not new_bio and event.is_reply:
                reply = await event.get_reply_message()
                new_bio = reply.message

            # Validate bio
            if not new_bio:
                await event.reply("❌ Please provide a bio or reply to a message.")
                return

            if len(new_bio) > 70:  # Telegram bio limit
                await event.reply("❌ Bio too long. Max 70 characters allowed.")
                return

            # Update profile bio
            await client(UpdateProfileRequest(about=new_bio))
            await event.reply(f"✅ Bio updated to:\n`{new_bio}`")

        except Exception as e:
            await event.reply(f"❌ Error: `{str(e)}`")

    print(f"✅ Set Description plugin loaded for user {user_id}")

# Alternative initialization method (for compatibility)
async def init_plugin(client, user_id):
    await setup(client, user_id)
