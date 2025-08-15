from telethon import events, functions
from telethon.errors import RpcError

async def setup(client, user_id):
    """Initialize the Common Chats plugin"""

    @client.on(events.NewMessage(pattern=r'^!common(?:\s+(.+))?', outgoing=True))
    async def common_chats_handler(event):
        arg = event.pattern_match.group(1)
        target = None

        try:
            # Case 1: Reply to a user
            if event.is_reply and not arg:
                reply_msg = await event.get_reply_message()
                target = await client.get_input_entity(reply_msg.sender_id)

            # Case 2: Username or ID provided
            elif arg:
                target = await client.get_input_entity(arg)

            else:
                await event.reply("❌ Reply to a user or provide their username/ID.")
                return

            # Fetch common chats
            result = await client(functions.messages.GetCommonChatsRequest(
                user_id=target,
                max_id=0,
                limit=100
            ))

            if result.chats:
                chat_names = [chat.title for chat in result.chats if hasattr(chat, 'title')]
                msg = "🤝 **Common Chats:**\n" + "\n".join(f"- {name}" for name in chat_names)
            else:
                msg = "ℹ No common chats found."

            await event.reply(msg)

        except RpcError as e:
            await event.reply(f"⚠ Telegram error: `{e}`")
        except Exception as e:
            await event.reply(f"⚠ Failed: `{e}`")

    print(f"✅ Common Chats plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
