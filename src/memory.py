"""
memory.py — ذاكرة المحادثة Conversation Memory (المسؤولة: لمى الأسمري)

نربط LangChain بقاعدة SQLite عن طريق كلاس يرث من BaseChatMessageHistory.
بهذا الشكل سجل المحادثة محفوظ في قاعدة البيانات، ونمرر آخر N رسالة للنموذج
عن طريق MessagesPlaceholder("history") في الـ Prompt.
"""
from __future__ import annotations

from typing import List, Sequence

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from .database import Database


class SQLiteChatHistory(BaseChatMessageHistory):
    """سجل محادثة LangChain مخزّن في جدول messages."""

    def __init__(self, db: Database, session_id: str, window: int = 6):
        self.db = db
        self.session_id = session_id
        self.window = window  # عدد الرسائل التي تُمرر للنموذج (نافذة الذاكرة)

    @property
    def messages(self) -> List[BaseMessage]:  # type: ignore[override]
        rows = self.db.get_messages(self.session_id, limit=self.window)
        result: List[BaseMessage] = []
        for r in rows:
            if r["role"] == "user":
                result.append(HumanMessage(content=r["content"]))
            else:
                result.append(AIMessage(content=r["content"]))
        return result

    def add_messages(self, messages: Sequence[BaseMessage]) -> None:
        for m in messages:
            role = "user" if isinstance(m, HumanMessage) else "assistant"
            self.db.add_message(self.session_id, role, str(m.content))

    def clear(self) -> None:
        self.db.clear_messages(self.session_id)
