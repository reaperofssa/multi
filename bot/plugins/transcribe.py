import aiohttp
import os
from telethon import events, functions
from telethon.errors import RpcError


async def setup(client, user_id):
    """Initialize the Transcribe plugin"""

    @client.on(events.NewMessage(pattern=r'^!transcribe(?:\s+(.+))?', outgoing=True))
    async def transcribe_handler(event):
        arg = event.pattern_match.group(1)
        peer = None
        msg_id = None
        target_msg = None

        try:
            # --- Identify the message ---
            if event.is_reply and not arg:
                reply_msg = await event.get_reply_message()

                # Validate it's audio/video note
                if not (
                    (hasattr(reply_msg, "voice") or getattr(reply_msg, "voice", None)) or
                    (hasattr(reply_msg, "video_note") or getattr(reply_msg, "video_note", None)) or
                    (reply_msg.media and "audio" in str(reply_msg.media).lower())
                ):
                    await event.reply("❌ That’s not a voice message or video note.")
                    return

                peer = await client.get_input_entity(reply_msg.sender_id)
                msg_id = reply_msg.id
                target_msg = reply_msg

            elif arg:
                try:
                    chat, msg_id_str = arg.split()
                    peer = await client.get_input_entity(chat)
                    msg_id = int(msg_id_str)
                    target_msg = await client.get_messages(chat, ids=msg_id)
                except ValueError:
                    await event.reply("❌ Usage: `!transcribe <chat> <msg_id>` or reply to a voice/video note.")
                    return
            else:
                await event.reply("❌ Reply to a voice/video note or give chat & message ID.")
                return

            # --- Try Telegram Premium transcription ---
            try:
                result = await client(functions.messages.TranscribeAudioRequest(
                    peer=peer,
                    msg_id=msg_id
                ))

                if getattr(result, "text", None):
                    await event.reply(f"📝 **Transcription:**\n{result.text}")
                    return
                else:
                    await event.reply("⚠ No transcription returned. Trying free API...")
            except RpcError as e:
                if "USER_PREMIUM_REQUIRED" in str(e):
                    await event.reply("⚠ Premium required. Using free API...")
                else:
                    await event.reply(f"⚠ Telegram error: `{e}`\nUsing free API...")

            # --- Fallback: Public Whisper API (keyless) ---
            file_path = await target_msg.download_media()
            if not file_path:
                await event.reply("❌ Failed to download audio.")
                return

            await event.reply("⏳ Transcribing with free API...")

            async with aiohttp.ClientSession() as session:
                with open(file_path, "rb") as f:
                    form = aiohttp.FormData()
                    form.add_field("audio_file", f, filename="audio.ogg", content_type="audio/ogg")

                    # Example public Whisper endpoint (keyless)
                    async with session.post("https://whisper.lablab.ai/asr", data=form) as resp:
                        if resp.status != 200:
                            await event.reply(f"❌ Free API error: {await resp.text()}")
                            return
                        data = await resp.json()

            text = data.get("text", "").strip()
            if text:
                await event.reply(f"📝 **Transcription (Free API):**\n{text}")
            else:
                await event.reply("⚠ No transcription returned from free API.")

        except Exception as e:
            await event.reply(f"⚠ Failed: `{e}`")

    print(f"✅ Transcribe plugin loaded for user {user_id}")


async def init_plugin(client, user_id):
    await setup(client, user_id)
