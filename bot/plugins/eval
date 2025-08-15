import io
import sys
import traceback
from contextlib import redirect_stdout
from telethon import events

async def setup(client, user_id):
    """Initialize the Eval plugin"""

    @client.on(events.NewMessage(pattern=r"^!eval(?:\s+([\s\S]+))?", outgoing=True))
    async def eval_handler(event):
        code = event.pattern_match.group(1)

        if not code and event.is_reply:
            reply = await event.get_reply_message()
            code = reply.raw_text

        if not code:
            await event.reply("❌ No code provided.")
            return

        # Security check (optional)
        # You can restrict !eval to yourself
        if event.sender_id != user_id:
            await event.reply("❌ Permission denied.")
            return

        # Prepare environment
        env = {
            "client": client,   # your active logged-in Telethon client
            "event": event,
            "user_id": user_id
        }

        output = io.StringIO()
        try:
            with redirect_stdout(output):
                # Allow async code
                exec(
                    f"async def __user_eval_func():\n"
                    + "\n".join(f"    {line}" for line in code.split("\n")),
                    env
                )
                result = await env["__user_eval_func"]()
        except Exception:
            result = traceback.format_exc()

        stdout_content = output.getvalue()
        output_text = ""
        if stdout_content:
            output_text += f"**Output:**\n`{stdout_content}`\n"
        if result:
            output_text += f"**Result:**\n`{result}`"

        if not output_text:
            output_text = "✅ No output."

        await event.reply(output_text[:4000])

    print(f"✅ Eval plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
