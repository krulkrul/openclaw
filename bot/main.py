import asyncio
import os
import discord
from discord.ext import commands

from .ai_client import AIClient, MODEL
from .memory import ConversationMemory
from .transcribe import transcribe_audio

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
GUILD_ID = os.getenv("DISCORD_GUILD_ID")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
ai = AIClient()
memory = ConversationMemory()


# ── Events ────────────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"✅ OpenClaw online as {bot.user}  |  model: {MODEL}")
    guild = discord.Object(id=int(GUILD_ID)) if GUILD_ID else None
    try:
        if guild:
            bot.tree.copy_global_to(guild=guild)
            synced = await bot.tree.sync(guild=guild)
        else:
            synced = await bot.tree.sync()
        print(f"   Synced {len(synced)} slash command(s)")
    except Exception as e:
        print(f"   Slash command sync failed: {e}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    is_dm = isinstance(message.channel, discord.DMChannel)
    conv_id = f"dm_{message.author.id}" if is_dm else str(message.channel.id)

    # ── Audio message (Discord voice note) ────────────────────────────────────
    audio = next(
        (a for a in message.attachments if a.content_type and a.content_type.startswith("audio/")),
        None,
    )
    if audio:
        print(f"   AUDIO from {message.author} | {audio.filename} ({audio.size} bytes)")
        async with message.channel.typing():
            try:
                content = await transcribe_audio(audio)
                print(f"   Transcribed: {content[:80]!r}")
                await message.channel.send(f"🎙️ *{content}*")
            except Exception as e:
                await message.channel.send(f"⚠️ Could not transcribe audio: {e}")
                return
    else:
        # ── Text message ───────────────────────────────────────────────────────
        content = message.content.replace(f"<@{bot.user.id}>", "").strip()
        print(f"   MSG from {message.author} | {content[:60]!r}")
        if not content:
            return

    # ── Send to AI ─────────────────────────────────────────────────────────────
    async with message.channel.typing():
        memory.add(conv_id, "user", content)
        try:
            response = await ai.chat(memory.get(conv_id))
            memory.add(conv_id, "assistant", response)
        except Exception as e:
            response = f"⚠️ Error: {e}"

    for chunk in _split(response):
        await message.channel.send(chunk)


# ── Slash commands ─────────────────────────────────────────────────────────────

@bot.tree.command(name="clear", description="Clear conversation history for this channel")
async def clear_cmd(interaction: discord.Interaction):
    conv_id = str(interaction.channel_id)
    memory.clear(conv_id)
    await interaction.response.send_message("🧹 Conversation history cleared.", ephemeral=True)


@bot.tree.command(name="status", description="Show OpenClaw status")
async def status_cmd(interaction: discord.Interaction):
    conv_id = str(interaction.channel_id)
    await interaction.response.send_message(
        f"✅ **OpenClaw** is running\n"
        f"Model: `{MODEL}`\n"
        f"History: `{len(memory.get(conv_id))}` messages in this channel",
        ephemeral=True,
    )


# ── Helpers ───────────────────────────────────────────────────────────────────

def _split(text: str, limit: int = 1990) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:limit])
        text = text[limit:]
    return chunks


def run():
    bot.run(DISCORD_TOKEN)
