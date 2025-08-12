"""
Finral Menu Command Plugin for Multi-Session UserBot
Responds to !menu with a detailed branded info message and link.
"""

from telethon import events

# Plugin setup function
async def setup(client, user_id):
    """Initialize the menu plugin"""

    @client.on(events.NewMessage(pattern=r'^!menu$', outgoing=True))
    async def menu_handler(event):
        """Handle !menu command"""
        try:
            # Get user info
            me = await client.get_me()

            # Prepare user details
            full_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
            username = f"@{me.username}" if me.username else "No username"
            is_bot = "Yes" if me.bot else "No"

            # Build the message
            msg = (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "⚡️ **Finral Control Panel**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"👤 **Full Name:** `{full_name}`\n"
                f"🆔 **User ID:** `{me.id}`\n"
                f"🏷 **Username:** `{username}`\n"
                f"🤖 **Bot Account:** `{is_bot}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🔗 **Menu:** [Open Menu](https://t.me/finraluserbot/menu)\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            )

            await event.reply(msg, link_preview=False)

        except Exception as e:
            await event.reply(f"❌ **Finral Error:** `{str(e)}`")

    print(f"✅ Menu plugin loaded for user {user_id}")

# Alternative initialization method (for compatibility)
async def init_plugin(client, user_id):
    await setup(client, user_id)
