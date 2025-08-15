"""
Anime Download Plugin for Multi-Session UserBot
Responds to !anidl <anime_id>|episode and !anidl search <anime_name>
"""
import requests
from telethon import events
import json
import logging
import re

# Set up logging for debugging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def resolve_pahe_link(pahe_url):
    """Resolve Pahe download link to direct MP4 link, fallback to original if fails"""
    try:
        resolve_url = f"https://thdump-api.hf.space/resolvex?url={pahe_url}"
        response = requests.get(resolve_url, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            mp4_link = data.get('mp4Link', '')
            if mp4_link and mp4_link.strip():  # Check if mp4Link is not empty
                logger.info(f"✅ Successfully resolved Pahe link: {pahe_url} -> {mp4_link}")
                return mp4_link
            else:
                logger.warning(f"⚠️ Empty mp4Link in response for: {pahe_url}")
        else:
            logger.warning(f"⚠️ API returned status {response.status_code} for: {pahe_url}")
        
        # Fallback to original Pahe link
        logger.info(f"🔄 Falling back to original Pahe link: {pahe_url}")
        return pahe_url
        
    except requests.exceptions.Timeout:
        logger.warning(f"⏱️ Timeout resolving Pahe link, using original: {pahe_url}")
        return pahe_url
    except requests.exceptions.RequestException as e:
        logger.warning(f"🌐 Network error resolving Pahe link {pahe_url}: {e}, using original")
        return pahe_url
    except json.JSONDecodeError as e:
        logger.warning(f"📄 JSON decode error for Pahe link {pahe_url}: {e}, using original")
        return pahe_url
    except Exception as e:
        logger.error(f"❌ Unexpected error resolving Pahe link {pahe_url}: {e}, using original")
        return pahe_url

def is_pahe_link(url):
    """Check if URL is a Pahe download link"""
    return 'pahe.win' in url or 'pahe.li' in url

async def process_download_links(links_dict, link_type):
    """Process and resolve download links"""
    processed_links = {}
    
    for quality, url in links_dict.items():
        if '_download' in quality:  # Only process download links
            if is_pahe_link(url):
                resolved_url = await resolve_pahe_link(url)
                processed_links[quality] = resolved_url
            else:
                processed_links[quality] = url
    
    return processed_links

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
                        result_text = "🔍 **ANIME SEARCH RESULTS**\n"
                        result_text += "━" * 30 + "\n\n"
                        
                        for anime in search_results[:10]:  # Limit to top 10 results
                            title = anime.get('title', 'Unknown')
                            link = anime.get('link', '')
                            similarity = anime.get('similarity', 0)
                            
                            # Extract anime ID from link (remove /anime/ prefix)
                            anime_id = link.replace('/anime/', '') if link.startswith('/anime/') else link
                            
                            # Format with similarity percentage
                            similarity_percent = int(similarity * 100)
                            result_text += f"📺 **{title}** `({similarity_percent}%)`\n"
                            result_text += f"📋 `!anidl {anime_id}|1`\n"
                            result_text += "─" * 25 + "\n"
                        
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
                        
                        # Update fetching message to show resolving links
                        await fetching_msg.edit("🔗 Resolving download links...")
                        
                        # Format caption with download links
                        caption = f"📺 **EPISODE {episode_num}**\n"
                        caption += "━" * 30 + "\n\n"
                        
                        has_content = False
                        
                        # Sub links
                        sub_links = links.get('sub', {})
                        if sub_links:
                            # Process and resolve download links
                            sub_download_links = await process_download_links(sub_links, 'sub')
                            
                            if sub_download_links:
                                has_content = True
                                caption += "🔤 **SUBTITLED VERSION**\n"
                                caption += "─" * 20 + "\n"
                                
                                for quality in ['360p_download', '720p_download', '1080p_download']:
                                    if quality in sub_download_links:
                                        quality_label = quality.replace('_download', '').upper()
                                        caption += f"⬇️ [{quality_label}]({sub_download_links[quality]})\n"
                                
                                caption += "\n"
                        
                        # Dub links
                        dub_links = links.get('dub', {})
                        if dub_links:
                            # Process and resolve download links
                            dub_download_links = await process_download_links(dub_links, 'dub')
                            
                            if dub_download_links:
                                has_content = True
                                caption += "🎤 **DUBBED VERSION**\n"
                                caption += "─" * 18 + "\n"
                                
                                for quality in ['360p_download', '720p_download', '1080p_download']:
                                    if quality in dub_download_links:
                                        quality_label = quality.replace('_download', '').upper()
                                        caption += f"⬇️ [{quality_label}]({dub_download_links[quality]})\n"
                                
                                caption += "\n"
                        
                        if not has_content:
                            caption += "❌ No download links available for this episode.\n\n"
                        
                        # Add footer
                        caption += "━" * 30 + "\n"
                        caption += "💡 *Click links to download directly*"
                        
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
