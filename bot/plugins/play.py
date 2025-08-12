import requests
import urllib.parse
import tempfile
import subprocess
from telethon import events
import os

async def setup(client, user_id):
    """Initialize the play plugin"""

    @client.on(events.NewMessage(pattern=r'^!play(?:\s+(.+))?', outgoing=True))
    async def play_handler(event):
        try:
            query = event.pattern_match.group(1)

            if not query:
                await event.reply("❌ Please provide a song name after `!play`.")
                return

            searching_msg = await event.reply("🎵 Searching...")

            encoded_query = urllib.parse.quote(query)
            url = f"https://apis.davidcyriltech.my.id/play?query={encoded_query}"

            response = requests.get(url, timeout=20)
            if response.status_code != 200:
                await searching_msg.edit("❌ API request failed.")
                return

            data = response.json()
            if not data.get("status") or "result" not in data:
                await searching_msg.edit("❌ Song not found.")
                return

            song = data["result"]
            download_url = song["download_url"]

            await searching_msg.edit(f"⬇️ Downloading **{song['title']}**...")

            # Download MP3
            audio_data = requests.get(download_url, stream=True, timeout=30)
            if audio_data.status_code != 200:
                await searching_msg.edit("❌ Failed to download audio.")
                return

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
                for chunk in audio_data.iter_content(1024):
                    tmp_mp3.write(chunk)
                mp3_path = tmp_mp3.name

            # Check file size before conversion
            if os.path.getsize(mp3_path) == 0:
                await searching_msg.edit("❌ Downloaded file is empty.")
                return

            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_ogg:
                ogg_path = tmp_ogg.name

            # Try libopus first, fall back to libvorbis if missing
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", mp3_path,
                "-c:a", "libopus", "-b:a", "64k",
                ogg_path
            ]

            process = subprocess.run(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            if process.returncode != 0:
                error_msg = process.stderr.decode(errors="ignore")
                if "Unknown encoder 'libopus'" in error_msg:
                    # Retry with libvorbis
                    ffmpeg_cmd[4] = "libvorbis"
                    process = subprocess.run(
                        ffmpeg_cmd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    if process.returncode != 0:
                        raise RuntimeError(process.stderr.decode(errors="ignore"))
                else:
                    raise RuntimeError(error_msg)

            await searching_msg.delete()

            # Send as Telegram voice note
            await event.client.send_file(
                event.chat_id,
                file=ogg_path,
                voice=True,
                caption=f"🎶 {song['title']} ({song['duration']})\n🔗 [YouTube]({song['video_url']})",
                parse_mode="md"
            )

        except Exception as e:
            await event.reply(f"⚠️ Error: {str(e)}")

    print(f"✅ Play plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
