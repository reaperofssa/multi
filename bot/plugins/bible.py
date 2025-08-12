"""
Finral Bible Command Plugin for Multi-Session UserBot
Usage:
    !bible Genesis 1:6
Fetches the specified Bible verse from bible-api.com
"""

from telethon import events
import aiohttp
import urllib.parse

# Plugin setup function
async def setup(client, user_id):
    """Initialize the Bible plugin"""

    @client.on(events.NewMessage(pattern=r'^!bible (.+)$', outgoing=True))
    async def bible_handler(event):
        """Handle !bible command"""
        try:
            query = event.pattern_match.group(1).strip()
            encoded_query = urllib.parse.quote(query)

            await event.edit(f"📖 Fetching verse: `{query}`...")

            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://bible-api.com/{encoded_query}") as resp:
                    if resp.status != 200:
                        await event.edit("❌ Verse not found or API error.")
                        return
                    data = await resp.json()

            reference = data.get("reference", "Unknown Reference")
            text = data.get("text", "No text found").strip()
            translation = data.get("translation_name", "Unknown Translation")

            verse_msg = (
                "```\n"
                f"{reference}\n"
                "------------------------------\n"
                f"{text}\n"
                f"({translation})\n"
                "```"
            )

            await event.edit(verse_msg)

        except Exception as e:
            await event.edit(f"❌ Error: `{str(e)}`")

    print(f"✅ Bible plugin loaded for user {user_id}")

# Alternative initialization method
async def init_plugin(client, user_id):
    await setup(client, user_id)
