import requests
import urllib.parse
import tempfile
import subprocess
from telethon import events
import os
import asyncio
import secrets
from pydub import AudioSegment
import wave
import struct

async def setup(client, user_id):
    """Initialize the play plugin"""
    
    def generate_waveform(audio_path):
        """Generate proper waveform data for voice note to avoid dots (...)"""
        try:
            # Load audio with pydub and ensure good quality
            audio = AudioSegment.from_file(audio_path)
            
            # Normalize audio level first to ensure good amplitude
            audio = audio.normalize()
            
            # Convert to mono if stereo
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Ensure sample rate is adequate for waveform generation
            if audio.frame_rate < 22050:
                audio = audio.set_frame_rate(22050)
            
            # Get raw audio data
            raw_data = audio.raw_data
            
            # Convert to samples based on sample width
            if audio.sample_width == 1:
                # 8-bit unsigned
                samples = struct.unpack(f'{len(raw_data)}B', raw_data)
                samples = [(s - 128) * 256 for s in samples]  # Convert to signed 16-bit range
            elif audio.sample_width == 2:
                # 16-bit signed
                samples = struct.unpack(f'{len(raw_data)//2}h', raw_data)
            elif audio.sample_width == 4:
                # 32-bit signed
                samples = struct.unpack(f'{len(raw_data)//4}i', raw_data)
                samples = [s // 65536 for s in samples]  # Convert to 16-bit range
            else:
                # Fallback for other formats
                samples = struct.unpack(f'{len(raw_data)//2}h', raw_data)
            
            # Generate waveform with proper segmentation
            # Use 100 segments for good visual representation
            segment_count = 100
            segment_size = max(1, len(samples) // segment_count)
            
            waveform_data = []
            
            for i in range(0, len(samples), segment_size):
                segment = samples[i:i + segment_size]
                if segment:
                    # Calculate RMS (Root Mean Square) for better amplitude representation
                    rms = (sum(s * s for s in segment) / len(segment)) ** 0.5
                    amplitude = int(rms)
                else:
                    amplitude = 0
                
                waveform_data.append(amplitude)
            
            # Ensure we have exactly 100 points
            if len(waveform_data) > 100:
                waveform_data = waveform_data[:100]
            elif len(waveform_data) < 100:
                # Pad with last value or zero
                last_val = waveform_data[-1] if waveform_data else 0
                waveform_data.extend([last_val] * (100 - len(waveform_data)))
            
            # Normalize to 0-31 range (Telegram's waveform format)
            if waveform_data and max(waveform_data) > 0:
                max_val = max(waveform_data)
                # Ensure minimum amplitude to avoid dots
                min_amplitude = 3  # Minimum amplitude to show waveform
                waveform_data = [max(min_amplitude, int(amp * 31 / max_val)) for amp in waveform_data]
            else:
                # Generate a realistic waveform pattern if audio is silent
                import random
                waveform_data = [random.randint(5, 25) for _ in range(100)]
            
            # Ensure all values are in valid range
            waveform_data = [max(1, min(31, val)) for val in waveform_data]
            
            return bytes(waveform_data)
            
        except Exception as e:
            print(f"Waveform generation error: {e}")
            # Generate a varied realistic waveform as fallback
            import random
            random.seed(42)  # Consistent fallback pattern
            fallback_waveform = []
            for i in range(100):
                # Create a natural-looking waveform pattern
                base = 15 + int(10 * (0.5 + 0.3 * (i % 20) / 20))
                variation = random.randint(-5, 5)
                amplitude = max(3, min(31, base + variation))
                fallback_waveform.append(amplitude)
            
            return bytes(fallback_waveform)

    @client.on(events.NewMessage(pattern=r'^!play(?:\s+(.+))?', outgoing=True))
    async def play_handler(event):
        query = event.pattern_match.group(1)
        if not query:
            await event.reply("❌ Please provide a song name after `!play`.")
            return

        # Show searching message (this will be edited later)
        status_msg = await event.reply("🎵 Searching...")

        try:

            # API request
            encoded_query = urllib.parse.quote(query)
            url = f"https://apis.davidcyriltech.my.id/play?query={encoded_query}"
            response = requests.get(url, timeout=20)

            # Validate response
            if response.status_code != 200:
                await status_msg.edit("❌ API request failed.")
                return

            data = response.json()
            if not data.get("status") or "result" not in data:
                await status_msg.edit("❌ Song not found.")
                return

            song = data["result"]
            download_url = song["download_url"]

            # Update status with song info
            await status_msg.edit(f"🎶 **{song['title']}** ({song['duration']})\n👤 {song.get('artist', 'Unknown Artist')}\n⬇️ Downloading...")

            # Download MP3
            audio_data = requests.get(download_url, stream=True, timeout=30)
            if audio_data.status_code != 200:
                await status_msg.edit("❌ Failed to download audio.")
                return

            # Generate random hex filename
            random_hex = secrets.token_hex(8)
            
            # Create temporary files with random hex names
            mp3_path = f"/tmp/{random_hex}.mp3"
            ogg_path = f"/tmp/{random_hex}.ogg"
            
            # Save MP3 file
            with open(mp3_path, 'wb') as tmp_mp3:
                for chunk in audio_data.iter_content(1024):
                    tmp_mp3.write(chunk)

            # Check file size before conversion
            if os.path.getsize(mp3_path) == 0:
                await status_msg.edit("❌ Downloaded file is empty.")
                os.unlink(mp3_path)
                return

            # Update status
            await status_msg.edit(f"🎶 **{song['title']}** ({song['duration']})\n👤 {song.get('artist', 'Unknown Artist')}\n🔄 Converting to voice note...")

            # Convert to OGG with opus codec for voice note
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", mp3_path,
                "-c:a", "libopus", "-b:a", "64k",
                "-ar", "48000",  # Standard sample rate for voice notes
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
                        await status_msg.edit("❌ Audio conversion failed.")
                        os.unlink(mp3_path)
                        return
                else:
                    await status_msg.edit("❌ Audio conversion failed.")
                    os.unlink(mp3_path)
                    return

            # Generate waveform
            waveform = generate_waveform(mp3_path)
            
            # Get audio duration in seconds
            try:
                audio = AudioSegment.from_file(mp3_path)
                duration = int(audio.duration_seconds)
            except:
                duration = 0

            # Delete status message
            await status_msg.delete()

            # Send caption first
            caption_text = f"🎶 **{song['title']}** ({song['duration']})\n🔗 [YouTube]({song['video_url']})"
            caption_msg = await event.reply(caption_text, parse_mode="md")

            # Send voice note as reply to original command (without caption since voice notes can't have captions)
            with open(ogg_path, 'rb') as voice_file:
                await event.client.send_file(
                    event.chat_id,
                    voice_file,
                    voice=True,
                    reply_to=event.id
                )

            # Clean up temporary files
            os.unlink(mp3_path)
            os.unlink(ogg_path)

            # Delete caption after 20 seconds
            async def delete_caption():
                await asyncio.sleep(20)
                try:
                    await caption_msg.delete()
                except:
                    pass  # Message might already be deleted
            
            # Schedule caption deletion
            asyncio.create_task(delete_caption())

        except:
            # Silently fail without sending errors to chat
            try:
                await status_msg.delete()
            except:
                pass

    print(f"✅ Play plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
