"""
Finral Anime Info Plugin for Multi-Session UserBot
Usage:
    !infoani <anime name>
Example:
    !infoani Naruto
"""

import requests
from telethon import events

API_BASE = "https://api.animethemes.moe/anime/"

def truncate_text(text, max_length=300):
    """Truncate text with ellipsis if too long."""
    return text if len(text) <= max_length else text[:max_length].rstrip() + "..."

# Plugin setup function
async def setup(client, user_id):
    """Initialize the anime info plugin"""

    @client.on(events.NewMessage(pattern=r'^!infoani\s+(.+)$', outgoing=True))
    async def infoani_handler(event):
        """Handle !infoani command"""
        try:
            anime_name = event.pattern_match.group(1).strip()
            await event.reply(f"🔍 Searching for anime **{anime_name}**...")

            # API request
            res = requests.get(API_BASE + anime_name)
            if res.status_code != 200:
                await event.reply("❌ Could not fetch anime info. Check the name.")
                return

            data = res.json().get("anime", {})
            if not data:
                await event.reply("❌ No data found for that anime.")
                return

            # Extract info
            name = data.get("name", "Unknown")
            media_format = data.get("media_format", "Unknown")
            season = data.get("season", "Unknown")
            year = data.get("year", "Unknown")
            synopsis = truncate_text(data.get("synopsis", "No synopsis available."))

            # Build response
            msg = (
                f"🎬 **{name}**\n"
                f"📺 **Format:** {media_format}\n"
                f"📅 **Season:** {season} {year}\n"
                f"📝 **Synopsis:** {synopsis}"
            )

            await event.reply(msg)

        except Exception as e:
            await event.reply(f"❌ Error: `{str(e)}`")

    print(f"✅ Anime Info plugin loaded for user {user_id}")

# Alternative initialization method (for compatibility)
async def init_plugin(client, user_id):
    await setup(client, user_id)
