from urllib.parse import urlparse, parse_qs
from telethon import events
from telethon.tl.functions.messages import RequestAppWebViewRequest
from telethon.tl.types import InputBotAppShortName

async def setup(client, user_id):
    """Initialize the resolve plugin"""

    @client.on(events.NewMessage(pattern=r'^!resolve(?:\s+(\S+))?(?:\s+(https?://\S+))?', outgoing=True))
    async def resolve_handler(event):
        try:
            args = event.raw_text.split(maxsplit=2)

            if len(args) == 1:
                await event.edit("❌ Usage: `!resolve [chat_id|me] <url>`")
                return

            # If second arg looks like a URL, use "me" as default target_chat
            if args[1].startswith("http"):
                target_chat = "me"
                deep_link = args[1]
            else:
                if len(args) < 3:
                    await event.edit("❌ Invalid format. Need chat_id and URL.")
                    return
                target_chat = args[1]
                deep_link = args[2]

            # Parse deep link
            parsed = urlparse(deep_link)
            path_parts = parsed.path.strip('/').split('/')

            if len(path_parts) == 0 or not path_parts[0]:
                await event.edit("❌ Invalid deep link format: missing bot username")
                return

            bot_username = path_parts[0]
            app_shortname = path_parts[1] if len(path_parts) > 1 else ""  # empty string if missing

            start_param = parse_qs(parsed.query).get("startapp", [""])[0]

            # Convert chat ID if not "me"
            if target_chat != "me":
                try:
                    target_chat = await client.get_input_entity(int(target_chat))
                except ValueError:
                    target_chat = await client.get_input_entity(target_chat)

            app_info = await client(
                RequestAppWebViewRequest(
                    target_chat,
                    InputBotAppShortName(
                        await client.get_input_entity(bot_username),
                        app_shortname
                    ),
                    "android",
                    start_param=start_param
                )
            )

            full_url = app_info.url
            short_url = full_url if len(full_url) <= 80 else full_url[:80] + "..."

            msg = (
                "✅ **Resolved Mini App Link**\n"
                f"**Bot:** `{bot_username}`\n"
                f"**Short Name:** `{app_shortname or '[default]'}`\n"
                f"**Start Param:** `{start_param}`\n\n"
                f"**Real URL:** `{short_url}`\n"
                f"[🌐 Full URL]({full_url})"
            )
            await event.edit(msg, link_preview=False)

        except Exception as e:
            await event.edit(f"❌ Error: `{str(e)}`")

    print(f"✅ Resolve plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
