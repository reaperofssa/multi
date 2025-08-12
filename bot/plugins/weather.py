"""
Finral Weather Command Plugin for Multi-Session UserBot
Responds to !weather <location> with current weather details.
"""

from telethon import events
import aiohttp
import urllib.parse

# Plugin setup function
async def setup(client, user_id):
    """Initialize the weather plugin"""

    @client.on(events.NewMessage(pattern=r'^!weather (.+)$', outgoing=True))
    async def weather_handler(event):
        """Handle !weather command"""
        try:
            location = event.pattern_match.group(1).strip()

            # Reply under the command message
            reply_msg = await event.reply(f"⛅ Fetching weather for `{location}`...")

            encoded_location = urllib.parse.quote(location)
            url = f"https://wttr.in/{encoded_location}?format=j1"

            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await reply_msg.edit("❌ Failed to fetch weather.")
                        return
                    data = await resp.json()

            # Extract current condition
            current = data["current_condition"][0]
            temp_c = current["temp_C"]
            temp_f = current["temp_F"]
            desc = current["weatherDesc"][0]["value"]
            humidity = current["humidity"]
            feels_like_c = current["FeelsLikeC"]
            wind_speed = current["windspeedKmph"]

            msg = (
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🌍 **Weather in {location.title()}**\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n"
                f"🌡 Temperature: `{temp_c}°C / {temp_f}°F`\n"
                f"💧 Humidity: `{humidity}%`\n"
                f"🌬 Wind: `{wind_speed} km/h`\n"
                f"🤔 Feels like: `{feels_like_c}°C`\n"
                f"🌤 Condition: `{desc}`\n"
                "━━━━━━━━━━━━━━━━━━━━━━"
            )

            await reply_msg.edit(msg)

        except Exception as e:
            await event.reply(f"❌ Error: `{str(e)}`")

    print(f"✅ Weather plugin loaded for user {user_id}")

# Alternative initialization method (for compatibility)
async def init_plugin(client, user_id):
    await setup(client, user_id)
