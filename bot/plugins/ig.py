import requests
from telethon import events

@client.on(events.NewMessage(pattern=r"^!ig\s+(\S+)$", outgoing=True))
async def ig_stalk(event):
    username = event.pattern_match.group(1)
    await event.edit(f"🔍 Fetching Instagram profile for **{username}**...")

    try:
        res = requests.get(f"https://apis.davidcyriltech.my.id/igstalk?username={username}")
        data = res.json()

        if "pp" not in data or not data["pp"]:
            await event.edit("❌ Profile not found or private.")
            return

        # Truncate bio to 200 chars
        bio = data.get("desk", "")
        if len(bio) > 200:
            bio = bio[:200] + "..."

        caption = (
            f"📸 **Instagram Profile**\n"
            f"👤 **Username:** {data['usrname']}\n"
            f"📝 **Bio:** {bio}\n\n"
            f"📌 **Posts:** {data['status']['post']}\n"
            f"👥 **Followers:** {data['status']['follower']}\n"
            f"🔗 **Following:** {data['status']['following']}"
        )

        # Send the image as a reply to the command
        await client.send_file(
            event.chat_id,
            data["pp"],
            caption=caption,
            reply_to=event.id
        )

        # Restore the original !ig message
        await event.edit(f"!ig {username}")

    except Exception as e:
        await event.edit(f"⚠️ Error: {e}")
