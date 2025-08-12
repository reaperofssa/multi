import requests
import urllib.parse
import tempfile
import subprocess
from telethon import events
import os
import asyncio
import secrets
from pydub import AudioSegment
import struct
from telethon.tl.types import DocumentAttributeAudio

async def setup(client, user_id):
    """Initialize the play plugin"""

    def generate_waveform(audio_path):
        """Generate proper waveform data for voice note to avoid dots (...)"""
        try:
            audio = AudioSegment.from_file(audio_path).normalize().set_channels(1)
            if audio.frame_rate < 22050:
                audio = audio.set_frame_rate(22050)

            raw_data = audio.raw_data
            if audio.sample_width == 1:
                samples = struct.unpack(f'{len(raw_data)}B', raw_data)
                samples = [(s - 128) * 256 for s in samples]
            elif audio.sample_width == 2:
                samples = struct.unpack(f'{len(raw_data)//2}h', raw_data)
            elif audio.sample_width == 4:
                samples = struct.unpack(f'{len(raw_data)//4}i', raw_data)
                samples = [s // 65536 for s in samples]
            else:
                samples = struct.unpack(f'{len(raw_data)//2}h', raw_data)

            segment_count = 100
            segment_size = max(1, len(samples) // segment_count)
            waveform_data = []

            for i in range(0, len(samples), segment_size):
                segment = samples[i:i + segment_size]
                rms = (sum(s * s for s in segment) / len(segment)) ** 0.5 if segment else 0
                waveform_data.append(int(rms))

            if len(waveform_data) > 100:
                waveform_data = waveform_data[:100]
            elif len(waveform_data) < 100:
                waveform_data.extend([waveform_data[-1] if waveform_data else 0] * (100 - len(waveform_data)))

            if waveform_data and max(waveform_data) > 0:
                max_val = max(waveform_data)
                min_amp = 3
                waveform_data = [max(min_amp, int(amp * 31 / max_val)) for amp in waveform_data]
            else:
                import random
                waveform_data = [random.randint(5, 25) for _ in range(100)]

            return bytes([max(1, min(31, val)) for val in waveform_data])
        except:
            import random
            return bytes([random.randint(5, 25) for _ in range(100)])

    @client.on(events.NewMessage(pattern=r'^!play(?:\s+(.+))?', outgoing=True))
    async def play_handler(event):
        try:
            query = event.pattern_match.group(1)
            if not query:
                await event.reply("❌ Please provide a song name after `!play`.")
                return

            searching_msg = await event.reply("🎵 Searching...")
            url = f"https://apis.davidcyriltech.my.id/play?query={urllib.parse.quote(query)}"
            r = requests.get(url, timeout=20)

            if r.status_code != 200 or not r.json().get("status"):
                await searching_msg.edit("❌ Song not found.")
                return

            song = r.json()["result"]
            mp3_path = f"/tmp/{secrets.token_hex(8)}.mp3"
            ogg_path = f"/tmp/{secrets.token_hex(8)}.ogg"

            audio_r = requests.get(song["download_url"], stream=True, timeout=30)
            with open(mp3_path, "wb") as f:
                for chunk in audio_r.iter_content(1024):
                    f.write(chunk)

            await searching_msg.edit(f"🔄 Converting **{song['title']}** to voice note...")

            subprocess.run(
                ["ffmpeg", "-y", "-i", mp3_path, "-c:a", "libopus", "-b:a", "64k", "-ar", "48000", ogg_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            waveform = generate_waveform(mp3_path)
            duration = int(AudioSegment.from_file(mp3_path).duration_seconds)

            await searching_msg.delete()

            # ✅ Send voice note as reply to the command message
            await event.reply(
                f"🎶 **{song['title']}** ({song['duration']})\n🔗 [YouTube]({song['video_url']})",
                file=ogg_path,
                voice=True,
                attributes=[DocumentAttributeAudio(duration=duration, voice=True, waveform=waveform)],
                parse_mode="md"
            )

        finally:
            for path in (mp3_path, ogg_path):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except:
                    pass

    print(f"✅ Play plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
