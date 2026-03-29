import json
import os
from collections import deque
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", "/data"))
MAX_MESSAGES = int(os.getenv("MAX_MESSAGES_PER_CONV", "40"))


class ConversationMemory:
    """Per-channel conversation history, persisted to disk so it survives restarts."""

    def __init__(self):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._convs: dict[str, deque] = {}
        self._load_all()

    def get(self, conv_id: str) -> list[dict]:
        return list(self._convs.get(conv_id, []))

    def add(self, conv_id: str, role: str, content: str) -> None:
        if conv_id not in self._convs:
            self._convs[conv_id] = deque(maxlen=MAX_MESSAGES)
        self._convs[conv_id].append({"role": role, "content": content})
        self._persist(conv_id)

    def clear(self, conv_id: str) -> None:
        self._convs.pop(conv_id, None)
        p = self._path(conv_id)
        if p.exists():
            p.unlink()

    # ── internals ─────────────────────────────────────────────────────────────

    def _path(self, conv_id: str) -> Path:
        # Sanitise conv_id so it's safe as a filename
        safe = conv_id.replace("/", "_").replace("..", "_")
        return DATA_DIR / f"{safe}.json"

    def _load_all(self) -> None:
        for f in DATA_DIR.glob("*.json"):
            try:
                msgs = json.loads(f.read_text())
                self._convs[f.stem] = deque(msgs, maxlen=MAX_MESSAGES)
            except Exception:
                pass

    def _persist(self, conv_id: str) -> None:
        self._path(conv_id).write_text(
            json.dumps(list(self._convs[conv_id]), indent=2)
        )
