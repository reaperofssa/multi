"""
Logo Generator Plugin for Multi-Session UserBot
Responds to !logo<number> <text> to generate various logo styles
"""
import aiohttp
from telethon import events
import urllib.parse

# List of 34 logo API URLs
LOGO_URLS = [
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/naruto-shippuden-logo-style-text-effect-online-808.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-text-effects-in-the-style-of-the-deadpool-logo-818.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-a-blackpink-style-logo-with-members-signatures-810.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-colorful-neon-light-text-effects-online-797.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-digital-glitch-text-effects-online-767.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-glossy-silver-3d-text-effect-online-802.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-online-typography-art-effects-with-multiple-layers-811.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/beautiful-3d-foil-balloon-effects-for-holidays-and-birthday-803.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-3d-colorful-paint-text-effect-online-801.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-a-frozen-christmas-text-effect-online-792.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-a-blue-neon-light-avatar-with-your-photo-777.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-impressive-neon-glitch-text-effects-online-768.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/write-text-on-wet-glass-online-589.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/handwritten-text-on-foggy-glass-online-680.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/multicolor-3d-paper-cut-style-text-effect-658.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/light-text-effect-futuristic-technology-style-648.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-a-watercolor-text-effect-online-655.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/write-in-sand-summer-beach-online-576.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/making-neon-light-text-effect-with-galaxy-style-521.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-the-titanium-text-effect-to-introduce-iphone-15-812.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-sunset-light-text-effects-online-807.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-colorful-angel-wing-avatars-731.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-3d-crack-text-effect-online-704.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-a-3d-shiny-metallic-text-effect-online-685.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/create-anonymous-hacker-avatars-cyan-neon-677.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/realistic-3d-sand-text-effect-online-580.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/writing-your-name-on-hot-air-balloon-506.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/paul-scholes-shirt-foot-ball-335.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/write-text-on-chocolate-186.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/caper-cut-effect-184.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/metal-star-text-online-109.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/thunder-text-effect-online-97.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/text-on-cloth-effect-62.html",
    "https://api.bk9.dev/maker/ephoto-1?text={}&url=https://en.ephoto360.com/stars-night-online-84.html",
]

async def setup(client, user_id):
    """Initialize the logo plugin"""
    
    @client.on(events.NewMessage(pattern=r'^!logo(\d+)(?:\s+(.+))?', outgoing=True))
    async def logo_handler(event):
        match = event.pattern_match
        logo_num = int(match.group(1))
        text = match.group(2)
        
        if not text:
            await event.reply(f"❌ Please provide text after `!logo{logo_num}`.")
            return

        if logo_num < 1 or logo_num > len(LOGO_URLS):
            await event.reply(f"⚠️ Invalid logo number. Use `!logo1` to `!logo{len(LOGO_URLS)}`.")
            return

        # Show generating message (this will be edited later)
        status_msg = await event.reply(f"🎨 Generating logo {logo_num}...")

        try:
            # API request
            encoded_text = urllib.parse.quote(text.strip())
            url = LOGO_URLS[logo_num - 1].format(encoded_text)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=30) as resp:
                    if resp.status != 200:
                        await status_msg.edit("❌ API request failed.")
                        return
                    
                    data = await resp.json()
                    if not data.get("status") or "BK9" not in data:
                        await status_msg.edit("❌ Failed to generate logo. Please try again.")
                        return
                    
                    image_url = data["BK9"]

            # Delete status message
            await status_msg.delete()

            # Send image directly
            await event.reply(
                file=image_url, 
                message=f"✅ Logo {logo_num} generated for: `{text}`"
            )

        except:
            # Silently fail without sending errors to chat
            try:
                await status_msg.delete()
            except:
                pass

    print(f"✅ Logo plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
