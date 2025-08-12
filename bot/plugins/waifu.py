from telethon import events
import aiohttp

async def setup_waifu(client):
    @client.on(events.NewMessage(pattern=r'^!waifu$', outgoing=True))
    async def waifu_cmd(event):
        api_url = "https://apis.davidcyriltech.my.id/random/waifu"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as resp:
                    if resp.status != 200:
                        await event.reply(f"⚠️ Failed to fetch waifu. HTTP {resp.status}")
                        return
                    # API returns an image directly
                    image_bytes = await resp.read()

            # Send as a reply to the command message
            await client.send_file(event.chat_id, image_bytes, reply_to=event.id)

        except Exception as e:
            await event.reply(f"⚠️ Error: `{e}`")
