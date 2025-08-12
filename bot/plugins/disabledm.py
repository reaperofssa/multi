"""
Enhanced Disable DM Plugin for Multi-Session UserBot
Usage:
    !disabledm on   -> Enable DM blocking
    !disabledm off  -> Disable DM blocking
    !disabledm      -> Show usage/help
When enabled:
    - Deletes messages from non-contacts
    - Tracks previously blocked users to prevent bypass
"""
import asyncio
from telethon import events

# Store DM block status for each user session
dm_block_status = {}
# Store blocked user IDs for each session (persistent tracking)
blocked_users = {}

async def setup(client, user_id):
    """Initialize the Disable DM plugin"""
    
    # Initialize blocked users set for this session
    if user_id not in blocked_users:
        blocked_users[user_id] = set()
    
    @client.on(events.NewMessage(pattern=r'^!disabledm(?:\s+(\w+))?$', outgoing=True))
    async def toggle_dm_block(event):
        """Toggle DM blocking or show help"""
        arg = event.pattern_match.group(1)
        
        if arg is None:
            # Show usage and current status
            status = "ENABLED" if dm_block_status.get(user_id, False) else "DISABLED"
            blocked_count = len(blocked_users.get(user_id, set()))
            await event.edit(
                "📖 **Disable DM Plugin**\n"
                "`!disabledm on`  → Enable DM blocking\n"
                "`!disabledm off` → Disable DM blocking\n"
                "`!disabledm clear` → Clear blocked users list\n"
                "`!disabledm`     → Show this help\n"
                "\nWhen enabled:\n- Deletes messages from non-contacts\n"
                "- Tracks previously blocked users\n"
                f"\n**Status:** {status}\n"
                f"**Blocked users tracked:** {blocked_count}"
            )
            return
        
        if arg.lower() == "on":
            dm_block_status[user_id] = True
            await event.edit("🛑 DM Block **ENABLED** (blocks non-contacts)")
        elif arg.lower() == "off":
            dm_block_status[user_id] = False
            await event.edit("✅ DM Block **DISABLED**")
        elif arg.lower() == "clear":
            blocked_users[user_id] = set()
            await event.edit("🗑️ Blocked users list **CLEARED**")
        else:
            await event.edit("❌ Invalid option. Use `on`, `off`, or `clear`.")
    
    @client.on(events.NewMessage(incoming=True))
    async def auto_delete_dm(event):
        """Auto delete DMs from non-contacts when enabled"""
        if not dm_block_status.get(user_id, False):
            return  # Not enabled
        
        if not event.is_private:
            return  # Only private chats
        
        sender = await event.get_sender()
        sender_id = sender.id
        
        if sender.contact:
            return  # Contact — allow
        
        # Check if we've already processed this user
        if sender_id in blocked_users[user_id]:
            # User has been blocked before - delete immediately without reply
            try:
                await client.delete_messages(event.chat_id, [event.id], revoke=True)
                print(f"[DM Block] Deleted message from previously blocked user: {sender_id}")
            except Exception as e:
                print(f"[DM Block Error] Failed to delete message: {e}")
            return
        
        # Check if this is the first interaction or if they're messaging after being blocked
        try:
            # Get recent message history
            history = await client.get_messages(event.chat_id, limit=10)
            
            # Count their messages vs our messages
            their_messages = [msg for msg in history if msg.sender_id == sender_id]
            our_messages = [msg for msg in history if msg.sender_id == user_id]
            
            # If this is their first message OR they have way more messages than us 
            # (indicating they've been messaging after being blocked)
            should_block = (
                len(their_messages) == 1 or  # First message
                (len(their_messages) > len(our_messages) + 2)  # Multiple messages with few/no replies
            )
            
            if should_block:
                # Add to blocked users list
                blocked_users[user_id].add(sender_id)
                
                # Send auto-reply
                reply = await event.respond(
                    "🚫 Sorry, my DMs are disabled for new chats. "
                    "Please contact me in a group or through a mutual contact."
                )
                
                # Wait 8 seconds before deleting everything
                await asyncio.sleep(8)
                
                # Delete their message
                await client.delete_messages(event.chat_id, [event.id], revoke=True)
                # Delete our auto-reply
                await client.delete_messages(event.chat_id, [reply.id], revoke=True)
                
                print(f"[DM Block] Blocked new user: {sender_id} (@{getattr(sender, 'username', 'no_username')})")
        
        except Exception as e:
            print(f"[DM Block Error] {e}")
    
    @client.on(events.UserUpdate)
    async def handle_user_updates(event):
        """Handle user blocks/deletions"""
        if not dm_block_status.get(user_id, False):
            return
        
        # If a user is blocked/deleted through Telegram, we keep them in our list
        # This prevents them from bypassing by getting unblocked and messaging again
        pass
    
    print(f"✅ Enhanced Disable DM plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
