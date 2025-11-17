from telethon import events

async def setup(client, user_id):
    """Copy/Re-send replied message without forward tag"""

    @client.on(events.NewMessage(pattern=r'^/copy$', outgoing=True))
    async def copy_handler(event):
        if not event.is_reply:
            return await event.reply("❌ Reply to a message to copy it.")

        replied = await event.get_reply_message()

        try:
            # If message has media (photo/video/document/audio/etc)
            if replied.media:
                await client.send_file(
                    event.chat_id,
                    file=replied.media,
                    caption=replied.raw_text or ""
                )
            else:
                # Text-only message
                await client.send_message(
                    event.chat_id,
                    replied.raw_text,
                    formatting_entities=replied.entities
                )

        except Exception as e:
            await event.reply(f"⚠️ Failed to copy message.\n`{e}`")

    print(f"✅ Copy plugin loaded for user {user_id}")


async def init_plugin(client, user_id):
    await setup(client, user_id)
