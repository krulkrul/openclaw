import asyncio
import os
import anthropic

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-5")
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))
SYSTEM_PROMPT = os.getenv(
    "SYSTEM_PROMPT",
    "You are Claw, a helpful and concise AI assistant. Keep replies short unless asked to elaborate.",
)


class ClaudeClient:
    def __init__(self):
        self._client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    async def chat(self, messages: list[dict]) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._sync_chat, messages)

    def _sync_chat(self, messages: list[dict]) -> str:
        resp = self._client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        return resp.content[0].text
