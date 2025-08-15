"""
Quote Plugin for Multi-Session UserBot
Responds to !quote <message> or !quote r (reply to a message)
Generates quote images and sends them as stickers
"""
import requests
from telethon import events
from telethon.tl.types import DocumentAttributeSticker
import urllib.parse
import io
import secrets
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def setup(client, user_id):
    """Initialize the Quote plugin"""
    
    @client.on(events.NewMessage(pattern=r'^!quote(?:\s+(.+))?', outgoing=True))
    async def quote_handler(event):
        generating_msg = None
        try:
            query = event.pattern_match.group(1)
            
            # Check if it's !quote r (reply mode)
            if query and query.strip().lower() == 'r':
                if not event.is_reply:
                    await event.reply("❌ Use !quote r as a reply to a message.")
                    return
                
                # Get the message you replied to (Message B)
                message_b = await event.get_reply_message()
                if not message_b or not message_b.text:
                    await event.reply("❌ The replied message has no text.")
                    return
                
                # Check if Message B is also a reply (to get Message A)
                if not message_b.is_reply:
                    await event.reply("❌ The message you replied to is not a reply to another message.")
                    return
                
                # Get Message A (the original message that Message B replied to)
                message_a = await message_b.get_reply_message()
                if not message_a or not message_a.text:
                    await event.reply("❌ Could not find the original message or it has no text.")
                    return
                
                # Get Message B user's first name (this will be the "username" in the API)
                message_b_user = message_b.sender
                message_b_username = "Unknown"
                if message_b_user:
                    if hasattr(message_b_user, 'first_name') and message_b_user.first_name:
                        message_b_username = message_b_user.first_name
                    elif hasattr(message_b_user, 'title') and message_b_user.title:
                        message_b_username = message_b_user.title
                
                # Get Message A user's first name (this will be the "repliedusername" in the API)
                message_a_user = message_a.sender
                message_a_username = "Unknown"
                if message_a_user:
                    if hasattr(message_a_user, 'first_name') and message_a_user.first_name:
                        message_a_username = message_a_user.first_name
                    elif hasattr(message_a_user, 'title') and message_a_user.title:
                        message_a_username = message_a_user.title
                
                # Truncate Message A to 29 chars + "…"
                message_a_text = message_a.text
                if len(message_a_text) > 29:
                    truncated_message_a = message_a_text[:29] + "…"
                else:
                    truncated_message_a = message_a_text
                
                # Build URL for reply quote (first API)
                # message = Message B, replyto = Message A (truncated)
                encoded_message = urllib.parse.quote(message_b.text)
                encoded_username = urllib.parse.quote(message_b_username)
                encoded_replyto = urllib.parse.quote(truncated_message_a)
                encoded_replied_username = urllib.parse.quote(message_a_username)
                
                url = f"https://reikerxx-quote.hf.space/chat?message={encoded_message}&username={encoded_username}&replyto={encoded_replyto}&repliedusername={encoded_replied_username}"
                
            else:
                # Normal quote mode
                if not query:
                    if event.is_reply:
                        reply_msg = await event.get_reply_message()
                        query = reply_msg.text if reply_msg else None
                    else:
                        await event.reply("❌ Please provide a message or reply to a message.")
                        return
                
                if not query:
                    await event.reply("❌ No text found to quote.")
                    return
                
                # Get user's first name
                user = await client.get_me()
                username = user.first_name or "User"
                
                # Build URL for normal quote (second API)
                encoded_message = urllib.parse.quote(query)
                encoded_username = urllib.parse.quote(username)
                
                url = f"https://reikerxx-quote.hf.space/chat?message={encoded_message}&username={encoded_username}"
            
            # Show generating message
            generating_msg = await event.reply("🖼️ Generating quote...")
            logger.info(f"Making request to: {url}")
            
            # Make API request to get the image
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, timeout=30, headers=headers)
            logger.info(f"API Response status: {response.status_code}")
            logger.info(f"Content-Type: {response.headers.get('content-type', 'unknown')}")
            logger.info(f"Content-Length: {len(response.content)} bytes")
            
            if response.status_code == 200 and len(response.content) > 0:
                # Check if it's actually an image
                content_type = response.headers.get('content-type', '').lower()
                if not any(img_type in content_type for img_type in ['image/', 'application/octet-stream']):
                    logger.warning(f"Unexpected content type: {content_type}")
                    logger.warning(f"Response content preview: {response.content[:200]}")
                
                # Generate random hex filename to avoid conflicts
                random_hex = secrets.token_hex(8)
                
                # Create a file-like object from the image data
                image_bytes = io.BytesIO(response.content)
                image_bytes.name = f"quote_{random_hex}.webp"
                image_bytes.seek(0)  # Reset pointer to beginning
                
                try:
                    # Try sending as sticker first
                    await client.send_file(
                        event.chat_id,
                        image_bytes,
                        reply_to=event.id,
                        attributes=[DocumentAttributeSticker(
                            alt="Quote",
                            stickerset=None
                        )]
                    )
                    logger.info("Successfully sent as sticker")
                    
                except Exception as sticker_error:
                    logger.warning(f"Failed to send as sticker: {sticker_error}")
                    
                    # Fallback: try sending as regular image
                    image_bytes.seek(0)  # Reset pointer
                    try:
                        await client.send_file(
                            event.chat_id,
                            image_bytes,
                            reply_to=event.id,
                            caption="📝 Quote"
                        )
                        logger.info("Successfully sent as regular image")
                        
                    except Exception as image_error:
                        logger.error(f"Failed to send as image too: {image_error}")
                        await event.reply("❌ Failed to send the quote image.")
                        return
                
                # Delete the generating message
                if generating_msg:
                    await generating_msg.delete()
                return
            
            else:
                logger.error(f"API request failed with status {response.status_code}")
                logger.error(f"Response content: {response.content[:500]}")
                await event.reply(f"❌ Quote generation failed. API returned status {response.status_code}")
            
            # If we get here, something went wrong
            if generating_msg:
                await generating_msg.delete()
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            if generating_msg:
                try:
                    await generating_msg.delete()
                except:
                    pass
            await event.reply("❌ Network error while generating quote.")
            
        except Exception as e:
            logger.error(f"Unexpected error in quote_handler: {e}", exc_info=True)
            # Show error in chat for debugging
            await event.reply(f"❌ Error: {str(e)}")
            if generating_msg:
                try:
                    await generating_msg.delete()
                except:
                    pass

    print(f"✅ Quote plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
