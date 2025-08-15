"""
Anime Download Plugin for Multi-Session UserBot
Responds to !anidl <anime_id>|episode and !anidl search <anime_name>
"""
import requests
from telethon import events
import json
import logging

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def setup(client, user_id):
    """Initialize the Anime Download plugin"""
    
    @client.on(events.NewMessage(pattern=r'^!anidl\s+(.+)', outgoing=True))
    async def anidl_handler(event):
        try:
            query = event.pattern_match.group(1).strip()
            
            # Check if it's a search command
            if query.lower().startswith('search '):
                search_query = query[7:].strip()  # Remove "search " prefix
                
                if not search_query:
                    await event.reply("❌ Please provide an anime name to search.")
                    return
                
                # Show searching message
                searching_msg = await event.reply("🔍 Searching for anime...")
                
                try:
                    # Make search API request
                    search_url = f"https://reikernx-ani.hf.space/search?q={search_query}"
                    response = requests.get(search_url, timeout=30)
                    
                    if response.status_code == 200:
                        search_results = response.json()
                        
                        if not search_results:
                            await searching_msg.edit("❌ No anime found with that name.")
                            return
                        
                        # Format search results for easy copying
                        result_text = "📺 **Anime Search Results:**\n\n"
                        
                        for anime in search_results[:10]:  # Limit to top 10 results
                            title = anime.get('title', 'Unknown')
                            link = anime.get('link', '')
                            similarity = anime.get('similarity', 0)
                            
                            # Extract anime ID from link (remove /anime/ prefix)
                            anime_id = link.replace('/anime/', '') if link.startswith('/anime/') else link
                            
                            # Format with similarity percentage
                            similarity_percent = int(similarity * 100)
                            result_text += f"**{title}** ({similarity_percent}%)\n"
                            result_text += f"`!anidl {anime_id}|1`\n\n"
                        
                        result_text = result_text.rstrip()  # Remove trailing newlines
                        
                        await searching_msg.edit(result_text)
                        
                    else:
                        logger.error(f"Search API failed with status {response.status_code}")
                        await searching_msg.edit(f"❌ Search failed. API returned status {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"Search request error: {e}")
                    await searching_msg.edit("❌ Network error while searching.")
                    
            else:
                # It's a download command
                if '|' not in query:
                    await event.reply("❌ Invalid format. Use: `!anidl <anime_id>|<episode>`")
                    return
                
                try:
                    anime_id, episode = query.split('|', 1)
                    anime_id = anime_id.strip()
                    episode = episode.strip()
                    
                    if not anime_id or not episode:
                        await event.reply("❌ Both anime ID and episode number are required.")
                        return
                    
                    # Validate episode is a number
                    try:
                        episode_num = int(episode)
                    except ValueError:
                        await event.reply("❌ Episode must be a number.")
                        return
                    
                except ValueError:
                    await event.reply("❌ Invalid format. Use: `!anidl <anime_id>|<episode>`")
                    return
                
                # Show fetching message
                fetching_msg = await event.reply("⬇️ Fetching episode data...")
                
                try:
                    # Make episode API request
                    episode_url = f"https://reikernx-ani.hf.space/api/episode?id={anime_id}&episode={episode_num}"
                    response = requests.get(episode_url, timeout=30)
                    
                    logger.info(f"Episode API URL: {episode_url}")
                    logger.info(f"Episode API Response status: {response.status_code}")
                    
                    if response.status_code == 200:
                        episode_data = response.json()
                        
                        # Extract data
                        snapshot = episode_data.get('snapshot', '')
                        play_url = episode_data.get('playUrl', '')
                        links = episode_data.get('links', {})
                        
                        # Format caption with download links
                        caption = f"📺 **Episode {episode_num}**\n\n"
                        
                        if play_url:
                            caption += f"🎬 **Play URL:** [Watch Online]({play_url})\n\n"
                        
                        # Sub links
                        sub_links = links.get('sub', {})
                        if sub_links:
                            caption += "🔤 **Subtitled:**\n"
                            
                            # Streaming links
                            if any(k in sub_links for k in ['360p', '720p', '1080p']):
                                caption += "📺 *Streaming:*\n"
                                for quality in ['360p', '720p', '1080p']:
                                    if quality in sub_links:
                                        caption += f"• [{quality}]({sub_links[quality]})\n"
                                caption += "\n"
                            
                            # Download links
                            if any(k in sub_links for k in ['360p_download', '720p_download', '1080p_download']):
                                caption += "⬇️ *Download:*\n"
                                for quality in ['360p_download', '720p_download', '1080p_download']:
                                    if quality in sub_links:
                                        quality_label = quality.replace('_download', '')
                                        caption += f"• [{quality_label}]({sub_links[quality]})\n"
                                caption += "\n"
                        
                        # Dub links
                        dub_links = links.get('dub', {})
                        if dub_links:
                            caption += "🎤 **Dubbed:**\n"
                            
                            # Streaming links
                            if any(k in dub_links for k in ['360p', '720p', '1080p']):
                                caption += "📺 *Streaming:*\n"
                                for quality in ['360p', '720p', '1080p']:
                                    if quality in dub_links:
                                        caption += f"• [{quality}]({dub_links[quality]})\n"
                                caption += "\n"
                            
                            # Download links
                            if any(k in dub_links for k in ['360p_download', '720p_download', '1080p_download']):
                                caption += "⬇️ *Download:*\n"
                                for quality in ['360p_download', '720p_download', '1080p_download']:
                                    if quality in dub_links:
                                        quality_label = quality.replace('_download', '')
                                        caption += f"• [{quality_label}]({dub_links[quality]})\n"
                                caption += "\n"
                        
                        # Clean up trailing newlines
                        caption = caption.rstrip()
                        
                        # Send snapshot image with caption
                        if snapshot:
                            try:
                                await client.send_file(
                                    event.chat_id,
                                    snapshot,
                                    caption=caption,
                                    reply_to=event.id
                                )
                                await fetching_msg.delete()
                                return
                                
                            except Exception as img_error:
                                logger.warning(f"Failed to send snapshot image: {img_error}")
                                # Fallback to text message
                                caption = f"📺 **Episode {episode_num}**\n\n" + caption
                                await fetching_msg.edit(caption)
                                return
                        else:
                            # No snapshot, send as text
                            await fetching_msg.edit(caption)
                            return
                    
                    else:
                        logger.error(f"Episode API failed with status {response.status_code}")
                        logger.error(f"Response content: {response.text[:500]}")
                        await fetching_msg.edit(f"❌ Episode not found. API returned status {response.status_code}")
                        
                except requests.exceptions.RequestException as e:
                    logger.error(f"Episode request error: {e}")
                    await fetching_msg.edit("❌ Network error while fetching episode data.")
                    
        except Exception as e:
            logger.error(f"Unexpected error in anidl_handler: {e}", exc_info=True)
            await event.reply(f"❌ Error: {str(e)}")

    print(f"✅ Anime Download plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
