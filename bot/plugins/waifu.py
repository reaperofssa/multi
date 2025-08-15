"""
Waifu Plugin for Multi-Session UserBot
Responds to !waifu to get random waifu image
"""
import aiohttp
from telethon import events

async def setup(client, user_id):
    """Initialize the waifu plugin"""
    
    @client.on(events.NewMessage(pattern=r'^!waifu$', outgoing=True))
    async def waifu_handler(event):
        # Show searching message
        status_msg = await event.reply("🌸 Getting random waifu...")

        try:
            # API request
            api_url = "https://apis.davidcyriltech.my.id/random/waifu"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=20) as resp:
                    if resp.status != 200:
                        await status_msg.edit(f"⚠️ Failed to fetch waifu. HTTP {resp.status}")
                        return
                    
                    # API returns an image directly
                    image_bytes = await resp.read()

            # Delete status message
            await status_msg.delete()

            # Send image as photo
            await event.client.send_file(
                event.chat_id, 
                image_bytes, 
                reply_to=event.id,
                force_document=False  # ensures it's sent as an image
            )

        except:
            # Silently fail without sending errors to chat
            try:
                await status_msg.delete()
            except:
                pass

    print(f"✅ Waifu plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
