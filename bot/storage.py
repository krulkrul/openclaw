"""
Permanent storage: archives all messages and user notes to SQLite with FTS5 search.
Lives at DATA_DIR/memory.db — persists across restarts and container rebuilds.
"""
import os
import sqlite3
import threading
from pathlib import Path

DB_PATH = Path(os.getenv("DATA_DIR", "./data")) / "memory.db"

# Phrases that hint the user is asking about past context → trigger auto-search (EN + NL)
_RECALL_HINTS = (
    # English
    "remember", "recall", "earlier", "before", "last time", "we discussed",
    "you said", "i told you", "what did", "what was", "did we talk",
    # Dutch
    "onthoud", "herinner", "eerder", "vorige keer", "weet je nog", "hebben we",
    "je zei", "ik vertelde", "wat was", "wat hebben", "weet nog",
)


class Storage:
    """Thread-safe SQLite storage with FTS5 full-text search."""

    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._local = threading.local()
        self._setup()

    # ── Public API ────────────────────────────────────────────────────────────

    def archive(self, conv: str, role: str, body: str) -> None:
        """Permanently store a message (called for every user/assistant turn)."""
        self._db().execute(
            "INSERT INTO messages (conv, role, body) VALUES (?,?,?)", (conv, role, body)
        )
        self._db().commit()

    def save_note(self, body: str, conv: str = None) -> None:
        """Save an explicit user note."""
        self._db().execute(
            "INSERT INTO notes (conv, body) VALUES (?,?)", (conv, body)
        )
        self._db().commit()

    def search(self, query: str, limit: int = 6) -> list[dict]:
        """Full-text search across notes and archived messages."""
        db = self._db()
        results = []

        rows = db.execute(
            "SELECT ts, body FROM notes_fts JOIN notes ON notes_fts.rowid = notes.id"
            " WHERE notes_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
        results += [{"ts": r["ts"], "type": "note", "body": r["body"]} for r in rows]

        rows = db.execute(
            "SELECT ts, role, body FROM messages_fts JOIN messages ON messages_fts.rowid = messages.id"
            " WHERE messages_fts MATCH ? ORDER BY rank LIMIT ?",
            (query, limit),
        ).fetchall()
        results += [{"ts": r["ts"], "type": r["role"], "body": r["body"]} for r in rows]

        return results

    def needs_recall(self, text: str) -> bool:
        """Return True if the message seems to be asking about past context."""
        lower = text.lower()
        return any(hint in lower for hint in _RECALL_HINTS)

    def format_context(self, results: list[dict]) -> str:
        """Format search results as a context block to prepend to AI prompt."""
        if not results:
            return ""
        lines = ["[Relevant past context retrieved from memory:]"]
        for r in results:
            tag = "📝 Note" if r["type"] == "note" else f"💬 {r['type'].capitalize()}"
            lines.append(f"{tag} ({r['ts'][:16]}): {r['body'][:200]}")
        return "\n".join(lines)

    # ── Internals ─────────────────────────────────────────────────────────────

    def _db(self) -> sqlite3.Connection:
        if not hasattr(self._local, "con"):
            con = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            con.row_factory = sqlite3.Row
            self._local.con = con
        return self._local.con

    def _setup(self) -> None:
        self._db().executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                ts   TEXT    DEFAULT (datetime('now')),
                conv TEXT    NOT NULL,
                role TEXT    NOT NULL,
                body TEXT    NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts
                USING fts5(body, content='messages', content_rowid='id');
            CREATE TRIGGER IF NOT EXISTS messages_ai AFTER INSERT ON messages BEGIN
                INSERT INTO messages_fts(rowid, body) VALUES (new.id, new.body);
            END;

            CREATE TABLE IF NOT EXISTS notes (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                ts   TEXT    DEFAULT (datetime('now')),
                conv TEXT,
                body TEXT    NOT NULL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts
                USING fts5(body, content='notes', content_rowid='id');
            CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
                INSERT INTO notes_fts(rowid, body) VALUES (new.id, new.body);
            END;
        """)
        self._db().commit()
