"""
Instagram Stalk Plugin for Multi-Session UserBot
Responds to !ig <username> to get Instagram profile information
"""
import requests
from telethon import events

async def setup(client, user_id):
    """Initialize the Instagram stalk plugin"""
    
    @client.on(events.NewMessage(pattern=r'^!ig(?:\s+(\S+))?', outgoing=True))
    async def instagram_handler(event):
        username = event.pattern_match.group(1)
        if not username:
            await event.reply("❌ Usage: `!ig <username>`")
            return

        # Show searching message (this will be edited later)
        status_msg = await event.reply(f"🔍 Fetching Instagram profile for @{username}...")

        try:
            # API request
            response = requests.get(f"https://apis.davidcyriltech.my.id/igstalk?username={username}", timeout=20)
            
            # Validate response
            if response.status_code != 200:
                await status_msg.edit("❌ API request failed.")
                return

            data = response.json()
            
            if "pp" not in data or not data["pp"]:
                await status_msg.edit("❌ Profile not found or private.")
                return

            # Extract profile information
            username_display = data.get('usrname', username)
            bio = data.get('desk', '')
            
            # Truncate bio to 200 chars
            if len(bio) > 200:
                bio = bio[:200] + "..."

            posts = data.get('status', {}).get('post', 0)
            followers = data.get('status', {}).get('follower', 0)
            following = data.get('status', {}).get('following', 0)
            profile_pic = data["pp"]

            # Create caption
            caption = (
                f"📸 **Instagram Profile**\n"
                f"👤 **Username:** {username_display}\n"
                f"📝 **Bio:** {bio}\n\n"
                f"📌 **Posts:** {posts}\n"
                f"👥 **Followers:** {followers}\n"
                f"🔗 **Following:** {following}"
            )

            # Delete status message
            await status_msg.delete()

            # Send profile picture with info
            await event.client.send_file(
                event.chat_id,
                profile_pic,
                caption=caption,
                reply_to=event.id
            )

        except:
            # Silently fail without sending errors to chat
            try:
                await status_msg.delete()
            except:
                pass

    print(f"✅ Instagram stalk plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
