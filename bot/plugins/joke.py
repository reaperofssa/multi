"""
Finral Joke Command Plugin for Multi-Session UserBot
Responds to !joke with a random joke from a public API.
"""

from telethon import events
import aiohttp

# Plugin setup function
async def setup(client, user_id):
    """Initialize the joke plugin"""

    @client.on(events.NewMessage(pattern=r'^!joke$', outgoing=True))
    async def joke_handler(event):
        """Handle !joke command"""
        try:
            await event.edit("🤣 Fetching a joke...")

            # Fetch joke from API
            async with aiohttp.ClientSession() as session:
                async with session.get("https://official-joke-api.appspot.com/random_joke") as resp:
                    if resp.status != 200:
                        await event.edit("❌ Failed to fetch joke. Try again later.")
                        return
                    data = await resp.json()

            setup_line = data.get("setup", "No setup")
            punch_line = data.get("punchline", "No punchline")

            joke_msg = (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                "😂 **Random Joke**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"📝 {setup_line}\n"
                f"💡 {punch_line}\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            )

            await event.edit(joke_msg)

        except Exception as e:
            await event.edit(f"❌ Error: `{str(e)}`")

    print(f"✅ Joke plugin loaded for user {user_id}")

# Alternative initialization method (for compatibility)
async def init_plugin(client, user_id):
    await setup(client, user_id)
