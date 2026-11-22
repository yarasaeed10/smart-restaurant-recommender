"""
config.py — إعدادات المشروع (المسؤولة: همس الشهري)

يقرأ الإعدادات من ملف .env محليًا، أو من Secrets في Streamlit Cloud.
لا يوجد أي مفتاح API مكتوب داخل الكود.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

# مسار جذر المشروع (المجلد الذي فيه app.py)
BASE_DIR = Path(__file__).resolve().parent.parent

# تحميل ملف .env إن وُجد (python-dotenv اختيارية حتى لا يتعطل البرنامج بدونها)
try:
    from dotenv import load_dotenv

    load_dotenv(BASE_DIR / ".env")
except ImportError:  # pragma: no cover
    pass


def _read_secret(name: str, default: str = "") -> str:
    """يقرأ القيمة من متغيرات البيئة أولًا ثم من st.secrets (Streamlit Cloud)."""
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st

        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        # لا يوجد ملف secrets أو streamlit غير مثبتة — نكمل بالقيمة الافتراضية
        pass
    return default


@dataclass(frozen=True)
class Settings:
    """كل إعدادات التطبيق في مكان واحد."""

    openai_api_key: str
    chat_model: str
    embedding_model: str
    temperature: float
    data_path: Path
    chroma_dir: Path
    db_path: Path
    top_k: int
    history_window: int

    @property
    def has_api_key(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.startswith("sk-"))


def get_settings() -> Settings:
    """ينشئ كائن الإعدادات. يُستدعى مرة واحدة عند تشغيل التطبيق."""
    return Settings(
        openai_api_key=_read_secret("OPENAI_API_KEY"),
        chat_model=_read_secret("OPENAI_MODEL", "gpt-4o-mini"),
        embedding_model=_read_secret("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        temperature=float(_read_secret("LLM_TEMPERATURE", "0.3")),
        data_path=BASE_DIR / "data" / "restaurants.csv",
        chroma_dir=BASE_DIR / "chroma_db",
        db_path=BASE_DIR / "restaurant_app.db",
        top_k=int(_read_secret("RETRIEVER_TOP_K", "6")),
        history_window=int(_read_secret("HISTORY_WINDOW", "6")),
    )
