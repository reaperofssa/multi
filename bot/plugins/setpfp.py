"""
Finral Set Profile Picture Plugin for Multi-Session UserBot
Usage:
    Reply to an image with !setpfp to set it as your profile picture.
"""

import os
import secrets
from telethon import events
from telethon.tl.functions.photos import UploadProfilePhotoRequest

# Plugin setup function
async def setup(client, user_id):
    """Initialize the set profile picture plugin"""

    @client.on(events.NewMessage(pattern=r'^!setpfp$', outgoing=True))
    async def setpfp_handler(event):
        """Handle !setpfp command"""
        try:
            # Ensure it's a reply
            if not event.is_reply:
                await event.reply("❌ Reply to an image to set as profile picture.")
                return

            reply = await event.get_reply_message()

            # Ensure the replied message has a photo
            if not reply.photo:
                await event.reply("❌ Replied message must contain a photo.")
                return

            # Generate random hex filename
            random_filename = f"{secrets.token_hex(8)}.jpg"
            temp_path = os.path.join("/tmp", random_filename)

            # Download the photo
            await event.reply("📥 Downloading photo...")
            await reply.download_media(file=temp_path)

            # Upload the profile photo
            await event.reply("📤 Uploading as profile picture...")
            await client(UploadProfilePhotoRequest(file=temp_path))

            # Cleanup temp file
            try:
                os.remove(temp_path)
            except:
                pass

            await event.reply("✅ Profile picture updated successfully!")

        except Exception as e:
            await event.reply(f"❌ Error: `{str(e)}`")

    print(f"✅ Set PFP plugin loaded for user {user_id}")

# Alternative initialization method (for compatibility)
async def init_plugin(client, user_id):
    await setup(client, user_id)
