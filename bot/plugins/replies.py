"""
Finral Replies Command Plugin for Multi-Session UserBot
Usage:
    !replies   → Gets last 10 messages replying to you in current chat
    !replies (reply to user) → Gets last 10 messages replying to you from that user
"""

from telethon import events
import os

async def setup(client, user_id):
    """Initialize the replies plugin"""

    async def fetch_replies(chat, target_id, limit=10, from_user=None):
        """Fetch last N messages replying to target_id in chat"""
        replies = []
        async for msg in client.iter_messages(chat, limit=200):
            if msg.reply_to and msg.reply_to.reply_to_msg_id:
                try:
                    replied_msg = await msg.get_reply_message()
                    if replied_msg and replied_msg.sender_id == target_id:
                        if from_user and msg.sender_id != from_user:
                            continue
                        replies.append(f"[{msg.sender_id}] {msg.text or '<no text>'}")
                        if len(replies) >= limit:
                            break
                except:
                    pass
        return replies

    @client.on(events.NewMessage(pattern=r'^!replies$', outgoing=True))
    async def replies_handler(event):
        """Handle !replies command"""
        try:
            me = await client.get_me()
            chat_id = event.chat_id
            target_user = None

            if event.is_reply:
                reply = await event.get_reply_message()
                target_user = reply.sender_id
                await event.edit(f"📥 Fetching last 10 replies from `{target_user}` to you...")
            else:
                await event.edit(f"📥 Fetching last 10 replies to you in this chat...")

            replies = await fetch_replies(chat_id, me.id, from_user=target_user)

            if not replies:
                await event.edit("❌ No replies found.")
                return

            file_name = f"replies_{target_user or chat_id}.txt"
            with open(file_name, "w", encoding="utf-8") as f:
                f.write("\n".join(replies))

            await client.send_file(chat_id, file_name, caption=f"📄 Last {len(replies)} replies")
            os.remove(file_name)
            await event.delete()

        except Exception as e:
            await event.edit(f"❌ Error: `{str(e)}`")

    print(f"✅ Replies plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
