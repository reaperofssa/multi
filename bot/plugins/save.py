import re
import os
from telethon import events, functions, types

async def setup(client, user_id):
    """Initialize the Save Story plugin"""

    @client.on(events.NewMessage(pattern=r'^!save(?:\s+(.+))?', outgoing=True))
    async def save_story_handler(event):
        try:
            arg = event.pattern_match.group(1)
            peer = None
            story_id = None

            # Case 1: Replying to a story
            if event.is_reply and not arg:
                reply_msg = await event.get_reply_message()
                
                # Check if the reply is a story reply
                if isinstance(reply_msg.reply_to, types.MessageReplyStoryHeader):
                    story_header = reply_msg.reply_to
                    story_id = story_header.story_id
                    peer = await client.get_input_entity(story_header.peer)
                else:
                    await event.reply("❌ That’s not a story reply.")
                    return

            # Case 2: Story link provided
            elif arg:
                match = re.match(r'https://t\.me/([^/]+)/s/(\d+)', arg.strip())
                if match:
                    username = match.group(1)
                    story_id = int(match.group(2))
                    peer = await client.get_input_entity(username)
                else:
                    await event.reply("❌ Invalid story link format.")
                    return

            if not peer or not story_id:
                await event.reply("❌ Could not determine story target.")
                return

            # Fetch story by ID
            stories = await client(functions.stories.GetStoriesByIDRequest(
                peer=peer,
                id=[story_id]
            ))

            if stories.stories:
                story = stories.stories[0]
                filename = f"story_{story.id}"

                # Download the story
                saved_file = await client.download_media(story.media, file=filename)

                if not saved_file or not os.path.exists(saved_file):
                    await event.reply("❌ Failed to download story.")
                    return

                # Send as video if it's a video
                mime_type = getattr(story.media.document, 'mime_type', '') if hasattr(story.media, 'document') else ''
                if "video" in mime_type:
                    await client.send_file(event.chat_id, saved_file, video_note=False)
                else:
                    await client.send_file(event.chat_id, saved_file)

                # Clean up
                try:
                    os.remove(saved_file)
                except:
                    pass
            else:
                await event.reply("❌ Story not found or no access.")

        except Exception as e:
            await event.reply(f"⚠ Failed: `{str(e)}`")

    print(f"✅ Save Story plugin loaded for user {user_id}")
