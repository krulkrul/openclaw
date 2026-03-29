"""
Loads SOUL.md (personality) and AGENT.md (user knowledge) from the repo root.
SOUL.md becomes the system prompt.
AGENT.md is injected as context at the start of every conversation.
Both files can be updated live — changes take effect on next message (no restart needed).
"""
import os
from pathlib import Path

# Resolve repo root relative to this file
_ROOT = Path(__file__).parent.parent


def load_soul() -> str:
    """Return SOUL.md content as the system prompt, falling back to env var."""
    path = _ROOT / "SOUL.md"
    if path.exists():
        return path.read_text().strip()
    return os.getenv(
        "SYSTEM_PROMPT",
        "You are Claw, a helpful and concise AI assistant.",
    )


def load_agent() -> str:
    """Return AGENT.md content to prepend as context."""
    path = _ROOT / "AGENT.md"
    if path.exists():
        return path.read_text().strip()
    return ""


def append_to_agent(fact: str) -> None:
    """Append a new learned fact to AGENT.md under a ## Learned section."""
    path = _ROOT / "AGENT.md"
    content = path.read_text() if path.exists() else "# Claw — Agent Knowledge\n"

    # Find or create the Learned section
    section = "## Learned"
    if section not in content:
        content = content.rstrip() + f"\n\n{section}\n"

    content = content.rstrip() + f"\n- {fact}\n"
    path.write_text(content)
