import requests
import urllib.parse
import tempfile
import subprocess
from telethon import events

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

            # Download the song
            audio_data = requests.get(download_url, stream=True, timeout=30)
            if audio_data.status_code != 200:
                await searching_msg.edit("❌ Failed to download audio.")
                return

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_mp3:
                for chunk in audio_data.iter_content(1024):
                    tmp_mp3.write(chunk)
                mp3_path = tmp_mp3.name

            # Convert to .ogg with opus codec
            with tempfile.NamedTemporaryFile(delete=False, suffix=".ogg") as tmp_ogg:
                ogg_path = tmp_ogg.name

            subprocess.run([
                "ffmpeg", "-i", mp3_path,
                "-c:a", "libopus", "-b:a", "64k",
                ogg_path
            ], check=True)

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
