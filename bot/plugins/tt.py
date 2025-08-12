"""
TikTok Stalk Plugin for Multi-Session UserBot
Responds to !tt <username> to get TikTok profile information
"""
import aiohttp
from telethon import events

async def setup(client, user_id):
    """Initialize the TikTok stalk plugin"""
    
    @client.on(events.NewMessage(pattern=r'^!tt(?:\s+(\S+))?', outgoing=True))
    async def tiktok_handler(event):
        username = event.pattern_match.group(1)
        if not username:
            await event.reply("❌ Usage: `!tt <username>`")
            return

        # Show searching message (this will be edited later)
        status_msg = await event.reply(f"🔍 Fetching TikTok profile for @{username}...")

        try:
            # API request
            api_url = f"https://apis.davidcyriltech.my.id/tiktokStalk?q={username}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, timeout=20) as resp:
                    if resp.status != 200:
                        await status_msg.edit(f"⚠️ Failed to fetch data. HTTP {resp.status}")
                        return
                    
                    data = await resp.json()

            # Validate response
            if not data.get("status") or "data" not in data:
                await status_msg.edit("❌ No data found for that username.")
                return

            user = data["data"]["user"]
            stats = data["data"]["stats"]

            # Extract user information
            nickname = user.get("nickname", "N/A")
            uniqueId = user.get("uniqueId", "N/A")
            bio = user.get("signature", "")
            
            # Truncate bio if too long
            if len(bio) > 250:
                bio = bio[:250] + "..."

            followers = stats.get("followerCount", 0)
            following = stats.get("followingCount", 0)
            likes = stats.get("heartCount", 0)
            videos = stats.get("videoCount", 0)
            link = user.get("bioLink", {}).get("link", None)
            verified = "✅ Yes" if user.get("verified", False) else "❌ No"
            pfp = user.get("avatarLarger")

            # Create caption
            caption = (
                f"🎵 **TikTok Profile**\n"
                f"👤 **Nickname:** {nickname}\n"
                f"🔖 **Username:** @{uniqueId}\n"
                f"📝 **Bio:** {bio}\n"
                f"{f'🌐 **Link:** {link}\n' if link else ''}"
                f"📌 **Followers:** {followers:,}\n"
                f"🔗 **Following:** {following:,}\n"
                f"❤️ **Likes:** {likes:,}\n"
                f"🎥 **Videos:** {videos:,}\n"
                f"✔️ **Verified:** {verified}"
            )

            # Delete status message
            await status_msg.delete()

            # Send profile with photo or just text
            if pfp:
                await event.client.send_file(
                    event.chat_id, 
                    pfp, 
                    caption=caption, 
                    reply_to=event.id
                )
            else:
                await event.reply(caption)

        except:
            # Silently fail without sending errors to chat
            try:
                await status_msg.delete()
            except:
                pass

    print(f"✅ TikTok stalk plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
