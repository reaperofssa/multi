from telethon import events
import aiohttp
import asyncio

async def setup_tiktok(client):
    @client.on(events.NewMessage(pattern=r'^!tt(?:\s+(\S+))?', outgoing=True))
    async def tiktok_stalk(event):
        username = event.pattern_match.group(1)

        if not username:
            await event.reply("❌ Usage: `!tt <username>`")
            return

        api_url = f"https://apis.davidcyriltech.my.id/tiktokStalk?q={username}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(api_url) as resp:
                    if resp.status != 200:
                        await event.reply(f"⚠️ Failed to fetch data. HTTP {resp.status}")
                        return

                    data = await resp.json()

            if not data.get("status") or "data" not in data:
                await event.reply("❌ No data found for that username.")
                return

            user = data["data"]["user"]
            stats = data["data"]["stats"]

            nickname = user.get("nickname", "N/A")
            uniqueId = user.get("uniqueId", "N/A")
            bio = user.get("signature", "")
            if len(bio) > 250:
                bio = bio[:250] + "..."
            followers = stats.get("followerCount", 0)
            following = stats.get("followingCount", 0)
            likes = stats.get("heartCount", 0)
            videos = stats.get("videoCount", 0)
            link = user.get("bioLink", {}).get("link", None)
            verified = "✅ Yes" if user.get("verified", False) else "❌ No"
            pfp = user.get("avatarLarger")

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

            # Send as reply to the original message
            if pfp:
                await client.send_file(event.chat_id, pfp, caption=caption, reply_to=event.id)
            else:
                await event.reply(caption)

        except Exception as e:
            await event.reply(f"⚠️ Error: `{e}`")

# Example init
# await setup_tiktok(client)
