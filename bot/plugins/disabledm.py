"""
Finral Disable DM Plugin for Multi-Session UserBot
Usage:
    !disabledm on   -> Enable DM blocking
    !disabledm off  -> Disable DM blocking
    !disabledm      -> Show usage/help
When enabled:
    - Deletes messages from non-contacts ONLY if it's their first time messaging you
"""

from telethon import events

# Store DM block status for each user session
dm_block_status = {}

async def setup(client, user_id):
    """Initialize the Disable DM plugin"""

    @client.on(events.NewMessage(pattern=r'^!disabledm(?:\s+(\w+))?$', outgoing=True))
    async def toggle_dm_block(event):
        """Toggle DM blocking or show help"""
        arg = event.pattern_match.group(1)
        
        if arg is None:
            # Show usage
            await event.edit(
                "📖 **Disable DM Plugin**\n"
                "`!disabledm on`  → Enable DM blocking\n"
                "`!disabledm off` → Disable DM blocking\n"
                "`!disabledm`     → Show this help\n"
                "\nWhen enabled:\n- Deletes messages from non-contacts "
                "ONLY if it's their first time messaging you."
            )
            return

        if arg.lower() == "on":
            dm_block_status[user_id] = True
            await event.edit("🛑 DM Block **ENABLED** (new chats only)")
        elif arg.lower() == "off":
            dm_block_status[user_id] = False
            await event.edit("✅ DM Block **DISABLED**")
        else:
            await event.edit("❌ Invalid option. Use `on` or `off`.")

    @client.on(events.NewMessage(incoming=True))
    async def auto_delete_new_dm(event):
        """Auto delete new first-time DMs from non-contacts when enabled"""
        if not dm_block_status.get(user_id, False):
            return  # Not enabled

        if not event.is_private:
            return  # Only private chats

        sender = await event.get_sender()
        if sender.contact:
            return  # Contact — allow

        # Check if this is the first message from this person
        history = await client.get_messages(event.chat_id, limit=2)
        if len(history) == 1:  # This is the only message
            try:
                await event.delete()  # Delete for you
                await client.delete_messages(event.chat_id, [event.id], revoke=True)  # Delete for both sides
            except Exception as e:
                print(f"[DM Block Error] {e}")

    print(f"✅ Disable DM plugin loaded for user {user_id}")

# Alternative initialization method
async def init_plugin(client, user_id):
    await setup(client, user_id)
