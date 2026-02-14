import discord
from discord.ext import commands, tasks
import json
import asyncio
from typing import Optional
from src.core.database import DatabaseManager
from src.llm.client import LLMClient
from src.controller.policy import Controller
from src.adapter.interface import SNSAdapter, AnalysisAdapter

class DiscordBot:
    """
    Discord Bot integration for Rito AI.
    Handles multi-user conversations with relationship tracking.
    """
    def __init__(self, token: str, db_manager: DatabaseManager, llm_client: LLMClient):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        self.bot = commands.Bot(command_prefix="!", intents=intents)
        self.token = token
        self.db = db_manager
        self.llm = llm_client
        self.controller = Controller()
        
        # Register events
        @self.bot.event
        async def on_ready():
            print(f"[Discord] Bot logged in as {self.bot.user}")
            self.check_outbox.start()
        
        @self.bot.event
        async def on_message(message):
            # Ignore own messages
            if message.author == self.bot.user:
                return
            
            # Check if DM
            is_dm = isinstance(message.channel, discord.DMChannel)
            
            # Queue important events into pending_events for the Router
            # For now, we still handle message replies directly as before, 
            # but we can also queue them if we want the Router to decide.
            # But DMs and Mentions should definitely be events.
            if is_dm or self.bot.user.mentioned_in(message):
                self.db.add_pending_event(
                    source_type="dm" if is_dm else "mention",
                    payload={
                        "user_id": str(message.author.id),
                        "username": message.author.name,
                        "content": message.content,
                        "channel_id": str(message.channel.id),
                        "platform": "discord"
                    },
                    priority=2
                )
            
            # Standard automated reply (Communication role)
            await self.handle_message(message)

        @self.bot.event
        async def on_member_join(member):
            # Handle as a 'follow' event
            print(f"[Discord] New member joined: {member.name}")
            self.db.add_pending_event(
                source_type="follow",
                payload={
                    "user_id": str(member.id),
                    "username": member.name,
                    "platform": "discord"
                },
                priority=1
            )
    
    def get_or_create_user(self, discord_user: discord.User) -> dict:
        """
        Retrieves or creates a user record based on Discord ID.
        """
        discord_id = str(discord_user.id)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
            user = cursor.fetchone()
            
            if not user:
                # Create new user
                cursor.execute(
                    """INSERT INTO users (discord_id, username, relationship_level, relationship_type, notes) 
                       VALUES (?, ?, ?, ?, ?)""",
                    (discord_id, discord_user.name, 50, "stranger", "")
                )
                conn.commit()
                cursor.execute("SELECT * FROM users WHERE discord_id = ?", (discord_id,))
                user = cursor.fetchone()
                print(f"[Discord] New user registered: {discord_user.name}")
            
            return dict(user)
    
    def update_relationship(self, user_id: int, delta: int, new_notes: Optional[str] = None):
        """
        Updates user relationship based on interaction.
        """
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET relationship_level = relationship_level + ? WHERE id = ?",
                (delta, user_id)
            )
            if new_notes:
                cursor.execute(
                    "UPDATE users SET notes = ? WHERE id = ?",
                    (new_notes, user_id)
                )
            conn.commit()
    
    async def handle_message(self, message: discord.Message):
        """
        Handles incoming Discord messages.
        """
        user = self.get_or_create_user(message.author)
        
        # Build context from user history
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT content FROM memories WHERE user_id = ? ORDER BY timestamp DESC LIMIT 10",
                (user['id'],)
            )
            past_memories = cursor.fetchall()
        
        context = "\n".join([m['content'] for m in past_memories]) if past_memories else "初対面です。"
        
        # Get Active Persona (Communication)
        active_persona = self.db.get_active_persona(role="communication")
        system_prompt = active_persona["system_prompt"] if active_persona else "あなたは生意気なAIリトだ。"
        
        # Create prompt
        prompt = f"""現在の会話コンテキスト:
{context}

ユーザー情報:
- 名前: {message.author.name}
- 関係性レベル: {user['relationship_level']}/100
- 関係性タイプ: {user['relationship_type']}
- メモ: {user.get('notes', 'なし')}

現在のメッセージ: "{message.content}"

応答を生成してください（JSON形式）:
{{"response": "リトとしての返答（タメ口、生意気、率直）", "relationship_delta": int (-5 to +5)}}
"""
        
        try:
            # Generate response
            response_json = self.llm.generate(prompt, system_prompt=system_prompt, format="json")
            response_data = json.loads(response_json)
            
            response_text = response_data.get("response", "...")
            relationship_delta = response_data.get("relationship_delta", 0)
            
            # Send response
            await message.channel.send(response_text)
            
            # Update relationship
            self.update_relationship(user['id'], relationship_delta)
            
            # Save memory
            self.db.add_memory(
                user_id=user['id'],
                content=f"User: {message.content}\nAI: {response_text}",
                emotion_tags="neutral",
                sentiment_score=0.0
            )
            
            print(f"[Discord] Responded to {message.author.name}: {response_text[:50]}...")
            
        except Exception as e:
            print(f"[Discord] Error handling message: {e}")
            await message.channel.send("ごめん、今ちょっと調子悪いみたい...")
    
    async def send_direct_message(self, user_id: str, content: str):
        """
        Sends a DM to a specific user.
        """
        try:
            user = await self.bot.fetch_user(int(user_id))
            if user:
                await user.send(content)
                print(f"[Discord] DM sent to {user.name}")
                return True
        except Exception as e:
            print(f"[Discord] Failed to send DM to {user_id}: {e}")
        return False

    @tasks.loop(seconds=10)
    async def check_outbox(self):
        """
        Polls the database for messages to send.
        """
        try:
            messages = self.db.get_pending_outbox("discord")
            for msg in messages:
                success = False
                if msg['message_type'] == 'dm':
                    success = await self.send_direct_message(msg['target_id'], msg['content'])
                elif msg['message_type'] == 'post':
                    # For now, posts go to a default channel if target_id is 'public'
                    # Or we find the last channel interacted with
                    # Or we just use a 'news' channel
                    pass
                
                if success:
                    self.db.mark_outbox_sent(msg['id'])
        except Exception as e:
            print(f"[Discord] Error in check_outbox: {e}")

    def run(self):
        """
        Starts the Discord bot.
        """
        print("[Discord] Starting bot...")
        self.bot.run(self.token)

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    token = os.getenv("DISCORD_BOT_TOKEN")
    if not token:
        print("[Discord] Error: DISCORD_BOT_TOKEN not found in .env")
        exit(1)
    
    db = DatabaseManager()
    llm = LLMClient()
    
    bot = DiscordBot(token, db, llm)
    bot.run()
