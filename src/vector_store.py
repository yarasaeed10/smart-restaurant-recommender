"""
vector_store.py — Embeddings + Chroma + Retriever (المسؤولة: يارا المالكي)

- Embeddings: نحول وصف كل مطعم إلى متجه رقمي باستخدام OpenAI Embeddings.
- Vector Store: نخزن المتجهات في Chroma (قاعدة متجهات محلية تحفظ على القرص).
- Retriever: نبحث عن أقرب المطاعم دلاليًا لطلب المستخدم مع فلترة بالـ metadata.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from typing import List, Optional

from .data_loader import dataframe_to_documents
from .schemas import UserPreferences

COLLECTION_NAME = "restaurants"


def _data_fingerprint(data_path: Path, embedding_model: str) -> str:
    """بصمة للملف والنموذج: إذا تغيّر ملف البيانات نعيد بناء قاعدة المتجهات."""
    digest = hashlib.md5(data_path.read_bytes()).hexdigest()
    return f"{digest}-{embedding_model}"


def build_or_load_vector_store(df, settings):
    """يبني قاعدة Chroma أول مرة، ويعيد استخدامها في المرات التالية."""
    from langchain_chroma import Chroma
    from langchain_openai import OpenAIEmbeddings

    embeddings = OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.openai_api_key)
    persist_dir: Path = settings.chroma_dir
    marker = persist_dir / "fingerprint.txt"
    fingerprint = _data_fingerprint(settings.data_path, settings.embedding_model)

    if marker.exists() and marker.read_text(encoding="utf-8") == fingerprint:
        return Chroma(
            collection_name=COLLECTION_NAME,
            embedding_function=embeddings,
            persist_directory=str(persist_dir),
        )

    # البيانات تغيرت أو أول تشغيل: نحذف القديم ونبني من جديد
    if persist_dir.exists():
        shutil.rmtree(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    documents = dataframe_to_documents(df)
    store = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(persist_dir),
        ids=[str(d.metadata["id"]) for d in documents],
    )
    marker.write_text(fingerprint, encoding="utf-8")
    return store


def preferences_to_filter(prefs: UserPreferences, level: int = 0) -> Optional[dict]:
    """
    يحوّل التفضيلات إلى فلتر Chroma.
    level يحدد درجة التخفيف عند قلة النتائج:
      0 = كل الشروط، 1 = المدينة + المطبخ + السعر، 2 = المدينة فقط، 3 = بدون فلتر.
    """
    conditions: List[dict] = []
    if prefs.city and level <= 2:
        conditions.append({"city": {"$eq": prefs.city}})
    if level <= 1:
        if prefs.cuisine:
            conditions.append({"cuisine": {"$eq": prefs.cuisine}})
        if prefs.max_price_level:
            conditions.append({"price_level": {"$lte": prefs.max_price_level}})
    if level == 0:
        if prefs.max_budget_sar:
            conditions.append({"avg_price_sar": {"$lte": prefs.max_budget_sar}})
        for field in ("family_friendly", "delivery", "outdoor_seating"):
            if getattr(prefs, field):
                conditions.append({field: {"$eq": True}})
        if prefs.vegetarian:
            conditions.append({"vegetarian_options": {"$eq": True}})

    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


def retrieve_restaurants(store, prefs: UserPreferences, k: int = 6, min_results: int = 2):
    """
    Retrieval مع تخفيف تدريجي للفلاتر:
    نبدأ بكل الشروط، وإذا كانت النتائج أقل من min_results نخفف الشروط خطوة خطوة.
    يرجع (المستندات, مستوى التخفيف المستخدم).
    """
    docs = []
    for level in range(4):
        search_kwargs = {"k": k}
        flt = preferences_to_filter(prefs, level)
        if flt:
            search_kwargs["filter"] = flt
        retriever = store.as_retriever(search_type="similarity", search_kwargs=search_kwargs)
        docs = retriever.invoke(prefs.search_query)
        if len(docs) >= min_results:
            return docs, level
    return docs, 3


def format_docs(docs) -> str:
    """يجهز المطاعم المسترجعة كنص للـ Prompt، مع رقم id لكل مطعم."""
    blocks = []
    for d in docs:
        blocks.append(f"[restaurant_id={d.metadata['id']}]\n{d.page_content}")
    return "\n\n---\n\n".join(blocks) if blocks else "لا توجد نتائج."
