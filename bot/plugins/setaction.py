import asyncio
from telethon import events
from telethon.tl.functions.messages import SetTypingRequest
from telethon.tl.types import (
    SendMessageTypingAction,
    SendMessageUploadPhotoAction,
    SendMessageUploadVideoAction,
    SendMessageUploadDocumentAction,
    SendMessageRecordAudioAction,
    SendMessageUploadAudioAction,
    SendMessageRecordVideoAction,
    SendMessageRecordRoundAction,
    SendMessageUploadRoundAction,
    SendMessageChooseContactAction,
    SendMessageGeoLocationAction,
    SendMessageGamePlayAction,
    SendMessageCancelAction
)

ACTION_MAP = {
    'typing': SendMessageTypingAction(),
    'photo': SendMessageUploadPhotoAction(progress=0),
    'video': SendMessageUploadVideoAction(progress=0),
    'document': SendMessageUploadDocumentAction(progress=0),
    'file': SendMessageUploadDocumentAction(progress=0),
    'record-audio': SendMessageRecordAudioAction(),
    'record-voice': SendMessageRecordAudioAction(),
    'audio': SendMessageUploadAudioAction(progress=0),
    'voice': SendMessageUploadAudioAction(progress=0),
    'song': SendMessageUploadAudioAction(progress=0),
    'record-video': SendMessageRecordVideoAction(),
    'record-round': SendMessageRecordRoundAction(),
    'round': SendMessageUploadRoundAction(progress=0),
    'contact': SendMessageChooseContactAction(),
    'location': SendMessageGeoLocationAction(),
    'game': SendMessageGamePlayAction(),
    'cancel': SendMessageCancelAction()
}

# Store running action tasks
running_action_tasks = {}

async def setup(client, user_id):

    @client.on(events.NewMessage(pattern=r'^!setaction(?:\s+(\S+))?', outgoing=True))
    async def setaction_handler(event):
        action_str = event.pattern_match.group(1)
        if not action_str:
            await event.reply("❌ Please provide an action. Example: `!setaction typing`")
            return

        action = ACTION_MAP.get(action_str.lower())
        if not action:
            await event.reply(f"❌ Unknown action `{action_str}`")
            return

        chat_id = event.chat_id

        # Cancel any previous action in this chat
        if chat_id in running_action_tasks:
            running_action_tasks[chat_id].cancel()

        async def send_action():
            try:
                while True:
                    await client(SetTypingRequest(peer=chat_id, action=action))
                    await asyncio.sleep(4)  # Refresh every few seconds
            except asyncio.CancelledError:
                pass

        # Start loop
        task = asyncio.create_task(send_action())
        running_action_tasks[chat_id] = task

        await event.reply(f"✅ Action `{action_str}` started and will keep showing.")

    @client.on(events.NewMessage(pattern=r'^!cancelaction$', outgoing=True))
    async def cancelaction_handler(event):
        chat_id = event.chat_id
        if chat_id in running_action_tasks:
            running_action_tasks[chat_id].cancel()
            del running_action_tasks[chat_id]

        await client(SetTypingRequest(peer=chat_id, action=SendMessageCancelAction()))
        await event.reply("✅ Action cancelled.")

    print(f"✅ SetAction + CancelAction plugin loaded for user {user_id}")
