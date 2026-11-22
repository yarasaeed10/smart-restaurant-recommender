"""
database.py — قاعدة بيانات SQLite (المسؤولة: لمى الأسمري)

تحفظ:
- sessions: جلسات المستخدمين.
- messages: سجل المحادثة (يُستخدم كـ Memory للنموذج).
- recommendations: كل مطعم تم ترشيحه وسببه.
- favorites: المطاعم المفضلة للمستخدم.
- feedback: تقييم المستخدم للترشيحات (👍 / 👎).
"""
from __future__ import annotations

import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .errors import DatabaseUnavailableError

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id          TEXT PRIMARY KEY,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recommendations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    query           TEXT NOT NULL,
    restaurant_id   INTEGER NOT NULL,
    restaurant_name TEXT NOT NULL,
    reason          TEXT,
    match_score     INTEGER,
    source          TEXT NOT NULL DEFAULT 'llm',
    created_at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS favorites (
    session_id      TEXT NOT NULL REFERENCES sessions(id),
    restaurant_id   INTEGER NOT NULL,
    restaurant_name TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    PRIMARY KEY (session_id, restaurant_id)
);
CREATE TABLE IF NOT EXISTS feedback (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES sessions(id),
    query       TEXT NOT NULL,
    is_helpful  INTEGER NOT NULL CHECK (is_helpful IN (0, 1)),
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, id);
"""


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


class Database:
    """غلاف بسيط فوق sqlite3. كل دالة تفتح اتصالًا قصيرًا وتغلقه."""

    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)
        self.init_schema()

    @contextmanager
    def _connect(self):
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
        except sqlite3.Error as exc:
            raise DatabaseUnavailableError(str(exc)) from exc
        try:
            yield conn
            conn.commit()
        except sqlite3.Error as exc:
            conn.rollback()
            raise DatabaseUnavailableError(str(exc)) from exc
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(SCHEMA)

    # ------------------------------------------------------------- الجلسات
    def create_session(self) -> str:
        session_id = uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute("INSERT INTO sessions (id, created_at) VALUES (?, ?)", (session_id, _now()))
        return session_id

    def ensure_session(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions (id, created_at) VALUES (?, ?)", (session_id, _now())
            )

    # ------------------------------------------------------------- الرسائل (Memory)
    def add_message(self, session_id: str, role: str, content: str) -> int:
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO messages (session_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (session_id, role, content, _now()),
            )
            return int(cur.lastrowid)

    def get_messages(self, session_id: str, limit: Optional[int] = None) -> List[Dict]:
        """يرجع الرسائل بالترتيب الزمني. limit يرجع آخر N رسالة فقط."""
        with self._connect() as conn:
            if limit:
                rows = conn.execute(
                    "SELECT * FROM (SELECT * FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?) "
                    "ORDER BY id ASC",
                    (session_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM messages WHERE session_id=? ORDER BY id ASC", (session_id,)
                ).fetchall()
        return [dict(r) for r in rows]

    def clear_messages(self, session_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM messages WHERE session_id=?", (session_id,))

    # ------------------------------------------------------------- الترشيحات
    def save_recommendations(self, session_id: str, query: str, items: List[Dict], source: str = "llm") -> None:
        with self._connect() as conn:
            conn.executemany(
                "INSERT INTO recommendations (session_id, query, restaurant_id, restaurant_name, reason, "
                "match_score, source, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    (session_id, query, int(i["restaurant_id"]), i["name"], i.get("reason", ""),
                     int(i.get("match_score", 0)), source, _now())
                    for i in items
                ],
            )

    def get_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT query, restaurant_name, reason, match_score, source, created_at "
                "FROM recommendations WHERE session_id=? ORDER BY id DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------- المفضلة
    def add_favorite(self, session_id: str, restaurant_id: int, name: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO favorites (session_id, restaurant_id, restaurant_name, created_at) "
                "VALUES (?, ?, ?, ?)",
                (session_id, int(restaurant_id), name, _now()),
            )

    def remove_favorite(self, session_id: str, restaurant_id: int) -> None:
        with self._connect() as conn:
            conn.execute(
                "DELETE FROM favorites WHERE session_id=? AND restaurant_id=?", (session_id, int(restaurant_id))
            )

    def get_favorites(self, session_id: str) -> List[Dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT restaurant_id, restaurant_name, created_at FROM favorites "
                "WHERE session_id=? ORDER BY created_at DESC",
                (session_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    # ------------------------------------------------------------- التقييم
    def add_feedback(self, session_id: str, query: str, is_helpful: bool) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO feedback (session_id, query, is_helpful, created_at) VALUES (?, ?, ?, ?)",
                (session_id, query, int(is_helpful), _now()),
            )

    def get_stats(self) -> Dict:
        """إحصائيات بسيطة لصفحة لوحة المعلومات."""
        with self._connect() as conn:
            total_q = conn.execute("SELECT COUNT(*) FROM messages WHERE role='user'").fetchone()[0]
            total_r = conn.execute("SELECT COUNT(*) FROM recommendations").fetchone()[0]
            helpful = conn.execute("SELECT COUNT(*) FROM feedback WHERE is_helpful=1").fetchone()[0]
            fb_total = conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0]
            top = conn.execute(
                "SELECT restaurant_name, COUNT(*) AS n FROM recommendations "
                "GROUP BY restaurant_name ORDER BY n DESC LIMIT 5"
            ).fetchall()
        return {
            "total_questions": total_q,
            "total_recommendations": total_r,
            "helpful_ratio": round(helpful / fb_total * 100) if fb_total else None,
            "top_restaurants": [dict(r) for r in top],
        }
