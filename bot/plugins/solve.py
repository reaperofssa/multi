"""
Wordle Solver Plugin for Multi-Session UserBot
Responds to !solve as a reply to a Wordle game message
"""
import requests
from telethon import events
import urllib.parse
import json
import re

async def setup(client, user_id):
    """Initialize the Wordle Solver plugin"""
    
    @client.on(events.NewMessage(pattern=r'^!solve', outgoing=True))
    async def solve_handler(event):
        try:
            # Must be a reply
            if not event.is_reply:
                await event.reply("❌ Please reply to a Wordle game message with !solve")
                return
            
            # Get the replied message
            reply_msg = await event.get_reply_message()
            game_text = reply_msg.text
            
            if not game_text:
                await event.reply("❌ No text found in the replied message.")
                return
            
            # Show thinking message
            thinking_msg = await event.reply("🧩 Analyzing Wordle game...")
            
            # Parse the Wordle game
            lines = game_text.strip().split('\n')
            guesses = []
            
            for line in lines:
                # Extract word from end of line (after the emoji boxes)
                parts = line.split()
                if parts:
                    word = parts[-1].strip()
                    # Check if it's a valid 5-letter word (all caps, letters only)
                    if len(word) == 5 and word.isalpha() and word.isupper():
                        # Extract emoji boxes from the beginning
                        emoji_part = line[:line.rfind(word)].strip()
                        guesses.append({
                            "word": word,
                            "result": emoji_part
                        })
            
            if not guesses:
                await thinking_msg.edit("❌ No valid Wordle guesses found in the message.")
                return
            
            # Construct the AI prompt
            prompt = f"""You are a Wordle puzzle solver. Analyze the following Wordle game state and provide your next guess.

RULES:
- Wordle is a 5-letter word guessing game
- 🟩 (green) = correct letter in correct position
- 🟨 (yellow) = correct letter but wrong position
- 🟥 (red) = letter not in the word
- You must respond with ONLY valid JSON, no other text
- Your guess must be exactly 5 letters
- Your guess must be a valid English word

PREVIOUS GUESSES:
"""
            
            for i, guess in enumerate(guesses, 1):
                prompt += f"{i}. Word: {guess['word']}\n   Result: {guess['result']}\n"
            
            prompt += """\nBased on the information above, what is your next guess?

RESPONSE FORMAT (JSON only, no markdown, no extra text):
{
  "guess": "YOURGUESSHERE",
  "reasoning": "Brief explanation of why this guess"
}

Remember:
- ONLY respond with JSON
- The guess must be EXACTLY 5 uppercase letters
- The guess must be a valid English word
- No markdown code blocks, no extra text"""
            
            # Make API request
            encoded_prompt = urllib.parse.quote(prompt)
            url = f"https://api-toxxic.zone.id/api/ai/claude?prompt={encoded_prompt}"
            
            response = requests.get(url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get("result"):
                    ai_response = data.get("data", "")
                    
                    # Try to parse JSON from response
                    try:
                        # Remove markdown code blocks if present
                        clean_response = ai_response.strip()
                        if "```json" in clean_response:
                            clean_response = clean_response.split("```json")[1].split("```")[0].strip()
                        elif "```" in clean_response:
                            clean_response = clean_response.split("```")[1].split("```")[0].strip()
                        
                        # Find JSON in response
                        json_match = re.search(r'\{[^}]+\}', clean_response)
                        if json_match:
                            clean_response = json_match.group(0)
                        
                        result = json.loads(clean_response)
                        guess = result.get("guess", "").upper()
                        reasoning = result.get("reasoning", "No reasoning provided")
                        
                        if len(guess) == 5 and guess.isalpha():
                            response_text = f"🎯 **Next Guess:** {guess}\n\n💡 **Reasoning:** {reasoning}"
                            await thinking_msg.edit(response_text)
                        else:
                            await thinking_msg.edit(f"❌ Invalid guess received: {guess}\n\nRaw response: {ai_response}")
                    except json.JSONDecodeError:
                        await thinking_msg.edit(f"❌ Failed to parse AI response as JSON.\n\nRaw response: {ai_response}")
                else:
                    await thinking_msg.edit("❌ AI did not return a valid result.")
            else:
                await thinking_msg.edit(f"❌ API request failed with status {response.status_code}")
                
        except Exception as e:
            try:
                await thinking_msg.edit(f"❌ Error: {str(e)}")
            except:
                await event.reply(f"❌ Error: {str(e)}")
    
    print(f"✅ Wordle Solver plugin loaded for user {user_id}")

async def init_plugin(client, user_id):
    await setup(client, user_id)
