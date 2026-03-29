import asyncio
import os
from groq import Groq
from .persona import load_soul, load_agent

MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))


class AIClient:
    def __init__(self):
        self._client = Groq(api_key=os.environ["GROQ_API_KEY"])

    async def chat(self, messages: list[dict]) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_chat, messages)

    def _sync_chat(self, messages: list[dict]) -> str:
        # Reload SOUL.md and AGENT.md on every call — edits take effect immediately
        soul = load_soul()
        agent = load_agent()
        system = f"{soul}\n\n{agent}".strip() if agent else soul

        resp = self._client.chat.completions.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "system", "content": system}] + messages,
        )
        return resp.choices[0].message.content
