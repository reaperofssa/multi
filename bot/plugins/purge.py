from telethon import events

async def setup(client, user_id):

    @client.on(events.NewMessage(pattern=r'^!purge$', outgoing=True))
    async def purge_warning(event):
        await event.reply(
            "⚠️ This will delete your last 100 messages in this chat.\n"
            "If you’re sure, type:\n`!purge yes delete`"
        )

    @client.on(events.NewMessage(pattern=r'^!purge\s+yes\s+delete$', outgoing=True))
    async def purge_handler(event):
        chat_id = event.chat_id
        deleted_count = 0

        await event.delete()  # remove the command message

        async for msg in client.iter_messages(chat_id, from_user='me', limit=100):
            try:
                await msg.delete()
                deleted_count += 1
            except Exception as e:
                print(f"Error deleting: {e}")

        await client.send_message(chat_id, f"✅ Deleted {deleted_count} messages.")

    print(f"✅ Purge plugin loaded for user {user_id}")
