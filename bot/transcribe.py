import asyncio
import os
import discord
from groq import Groq

WHISPER_MODEL = os.getenv("WHISPER_MODEL", "whisper-large-v3-turbo")

_client = Groq(api_key=os.environ["GROQ_API_KEY"])


async def transcribe_audio(attachment: discord.Attachment) -> str:
    """Download a Discord audio attachment and transcribe it via Groq Whisper."""
    audio_bytes = await attachment.read()
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_transcribe, audio_bytes, attachment.filename)


def _sync_transcribe(audio_bytes: bytes, filename: str) -> str:
    result = _client.audio.transcriptions.create(
        file=(filename, audio_bytes),
        model=WHISPER_MODEL,
    )
    return result.text
