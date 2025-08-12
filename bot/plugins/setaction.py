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

# Map string shortcuts to Telethon action objects
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

async def setup(client, user_id):

    # Command to set an action
    @client.on(events.NewMessage(pattern=r'^!setaction(?:\s+(\S+))?', outgoing=True))
    async def setaction_handler(event):
        try:
            action_str = event.pattern_match.group(1)
            if not action_str:
                await event.reply("❌ Please provide an action. Example: `!setaction typing`")
                return

            action = ACTION_MAP.get(action_str.lower())
            if not action:
                await event.reply(f"❌ Unknown action `{action_str}`")
                return

            await client(SetTypingRequest(
                peer=event.chat_id,
                action=action
            ))

            await event.reply(f"✅ Action `{action_str}` triggered.")

        except Exception as e:
            await event.reply(f"⚠️ Error: {str(e)}")

    # Command to cancel action
    @client.on(events.NewMessage(pattern=r'^!cancelaction$', outgoing=True))
    async def cancelaction_handler(event):
        try:
            await client(SetTypingRequest(
                peer=event.chat_id,
                action=SendMessageCancelAction()
            ))
            await event.reply("✅ Action cancelled.")
        except Exception as e:
            await event.reply(f"⚠️ Error: {str(e)}")

    print(f"✅ SetAction + CancelAction plugin loaded for user {user_id}")
