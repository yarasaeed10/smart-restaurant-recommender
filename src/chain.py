"""
chain.py — قلب النظام: سلسلة LangChain الكاملة (المسؤولة: عائشة المالكي)

مسار الطلب (Pipeline):
  رسالة المستخدم
    → (1) التحقق من المدخلات
    → (2) Extraction Chain: Prompt | LLM.with_structured_output(UserPreferences)
    → (3) Retrieval: Chroma Retriever مع فلترة metadata وتخفيف تدريجي
    → (4) Recommendation Chain: Prompt | LLM.with_structured_output(RecommendationResponse)
    → (5) Guardrail: التأكد أن كل مطعم مرشّح موجود فعلًا في نتائج البحث
    → (6) الحفظ في SQLite (الرسائل + الترشيحات)
وعند أي خطأ في OpenAI ننتقل إلى البحث المحلي (fallback.py).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .errors import (
    AppError,
    InvalidModelResponseError,
    InvalidUserInputError,
    LLMUnavailableError,
    MissingAPIKeyError,
)
from .fallback import extract_preferences_rule_based, local_search
from .schemas import RecommendationResponse, UserPreferences

logger = logging.getLogger(__name__)

MIN_LEN, MAX_LEN = 3, 500


@dataclass
class EngineResult:
    """النتيجة التي تعرضها الواجهة."""

    summary: str
    recommendations: List[Dict] = field(default_factory=list)
    follow_up_question: Optional[str] = None
    preferences: Dict = field(default_factory=dict)
    source: str = "llm"            # llm أو local
    warning: Optional[str] = None  # رسالة خطأ ودية إن وُجدت
    relax_level: int = 0           # كم مرة خففنا الفلاتر


def validate_user_input(text: str) -> str:
    """Error Handling للإدخال الخاطئ: فارغ، قصير جدًا، طويل جدًا، أو رموز فقط."""
    text = (text or "").strip()
    if len(text) < MIN_LEN:
        raise InvalidUserInputError("الطلب قصير جدًا")
    if len(text) > MAX_LEN:
        raise InvalidUserInputError("الطلب أطول من 500 حرف")
    if not re.search(r"[ء-يA-Za-z]", text):  # حروف عربية أو إنجليزية فعلية
        raise InvalidUserInputError("الطلب لا يحتوي على كلمات")
    return text


class RecommendationEngine:
    """يجمع كل مكونات LangChain في كلاس واحد تستخدمه الواجهة."""

    def __init__(self, settings, df, db):
        self.settings = settings
        self.df = df
        self.db = db
        self.store = None
        self.llm = None
        self.init_error: Optional[AppError] = None
        self._last_prefs: Dict[str, Dict] = {}  # ذاكرة بسيطة للبحث المحلي: آخر تفضيلات لكل جلسة
        self._last_top_price: Dict[str, int] = {}
        self._setup()

    # ------------------------------------------------------------------ الإعداد
    def _setup(self) -> None:
        if not self.settings.has_api_key:
            self.init_error = MissingAPIKeyError()
            return
        try:
            from langchain_openai import ChatOpenAI

            from .vector_store import build_or_load_vector_store

            self.llm = ChatOpenAI(
                model=self.settings.chat_model,
                temperature=self.settings.temperature,
                api_key=self.settings.openai_api_key,
                timeout=30,
                max_retries=2,
            )
            self.store = build_or_load_vector_store(self.df, self.settings)
        except Exception as exc:  # مفتاح خاطئ، لا يوجد إنترنت، حصة منتهية...
            logger.exception("فشل تهيئة OpenAI/Chroma")
            self.init_error = LLMUnavailableError(str(exc))
            self.llm, self.store = None, None

    @property
    def llm_ready(self) -> bool:
        return self.llm is not None and self.store is not None

    # ------------------------------------------------------------------ السلاسل
    def _extraction_chain(self):
        from .prompts import EXTRACTION_PROMPT

        return EXTRACTION_PROMPT | self.llm.with_structured_output(UserPreferences)

    def _recommendation_chain(self):
        from .prompts import RECOMMENDATION_PROMPT

        return RECOMMENDATION_PROMPT | self.llm.with_structured_output(RecommendationResponse)

    # ------------------------------------------------------------------ التشغيل
    def recommend(self, question: str, session_id: str) -> EngineResult:
        question = validate_user_input(question)  # يرمي InvalidUserInputError للواجهة

        history = self._history(session_id)
        if self.llm_ready:
            try:
                result = self._run_llm(question, history)
            except InvalidModelResponseError as exc:
                result = self._run_local(question, warning=exc.user_message, session_id=session_id)
            except Exception as exc:
                logger.exception("خطأ أثناء استدعاء النموذج")
                result = self._run_local(question, warning=LLMUnavailableError(str(exc)).user_message,
                                         session_id=session_id)
        else:
            warning = self.init_error.user_message if self.init_error else None
            result = self._run_local(question, warning=warning, session_id=session_id)

        self._save(session_id, question, result)
        return result

    def _history(self, session_id: str):
        try:
            from .memory import SQLiteChatHistory

            return SQLiteChatHistory(self.db, session_id, self.settings.history_window).messages
        except Exception:
            return []  # إذا تعطلت القاعدة نكمل بدون ذاكرة

    def _run_llm(self, question: str, history) -> EngineResult:
        from .vector_store import format_docs, retrieve_restaurants

        cities = sorted(self.df["city"].unique())
        cuisines = sorted(self.df["cuisine"].unique())

        # (2) استخراج التفضيلات
        prefs: UserPreferences = self._extraction_chain().invoke(
            {"question": question, "history": history,
             "cities": "، ".join(cities), "cuisines": "، ".join(cuisines)}
        )
        if prefs is None:
            raise InvalidModelResponseError("لم يرجع النموذج تفضيلات")

        # نتجاهل قيمًا غير موجودة في البيانات بدل أن تفشل الفلترة
        if prefs.city and prefs.city not in cities:
            prefs.city = None
        if prefs.cuisine and prefs.cuisine not in cuisines:
            prefs.cuisine = None

        if not prefs.is_food_related:
            return EngineResult(
                summary="أنا متخصص في ترشيح المطاعم فقط 😊 قل لي وش تشتهي، وفي أي مدينة، وكم ميزانيتك.",
                preferences=prefs.model_dump(exclude_none=True),
            )

        # (3) Retrieval
        docs, relax_level = retrieve_restaurants(self.store, prefs, k=self.settings.top_k)
        if not docs:
            raise InvalidModelResponseError("لا توجد نتائج من البحث")

        # (4) الترشيح
        response: RecommendationResponse = self._recommendation_chain().invoke(
            {"question": question, "history": history,
             "context": format_docs(docs),
             "preferences": prefs.model_dump_json(exclude_none=True)}
        )

        # (5) Guardrail ضد الهلوسة: نقبل فقط المطاعم الموجودة في نتائج البحث
        valid_ids = {int(d.metadata["id"]) for d in docs}
        by_id = {int(d.metadata["id"]): d.metadata for d in docs}
        recs = []
        for r in (response.recommendations if response else []):
            if r.restaurant_id in valid_ids:
                item = r.model_dump()
                item["name"] = by_id[r.restaurant_id]["name"]  # الاسم الصحيح من البيانات
                recs.append(item)
        if response is None or (response.recommendations and not recs):
            raise InvalidModelResponseError("النموذج رشّح مطاعم غير موجودة")

        warning = None
        if relax_level > 0:
            warning = "ما لقينا تطابقًا كاملًا لكل الشروط، فخففنا بعضها وعرضنا الأقرب لطلبك."
        return EngineResult(
            summary=response.summary,
            recommendations=recs,
            follow_up_question=response.follow_up_question,
            preferences=prefs.model_dump(exclude_none=True),
            source="llm",
            warning=warning,
            relax_level=relax_level,
        )

    def _run_local(self, question: str, warning: Optional[str] = None, session_id: str = "") -> EngineResult:
        new = extract_preferences_rule_based(question)
        last = self._last_prefs.get(session_id, {})
        # طلبات المتابعة: نكمل على التفضيلات السابقة ونعدّل الجديد فقط
        prefs = {**last, **new} if last and len(new) <= 1 else new
        if any(w in question for w in ["أرخص", "ارخص"]) and self._last_top_price.get(session_id):
            # «أرخص»: ميزانية أقل من سعر الترشيح الأول السابق
            prefs["max_budget_sar"] = self._last_top_price[session_id] - 1
        self._last_prefs[session_id] = prefs
        recs = local_search(self.df, question, prefs)
        if recs:
            top = self.df.loc[self.df["id"] == recs[0]["restaurant_id"], "avg_price_sar"]
            if not top.empty:
                self._last_top_price[session_id] = int(top.iloc[0])
        return EngineResult(
            summary="هذه أقرب المطاعم لطلبك من البحث المحلي:",
            recommendations=recs,
            preferences=prefs,
            source="local",
            warning=warning,
        )

    def _save(self, session_id: str, question: str, result: EngineResult) -> None:
        """يحفظ السؤال والرد والترشيحات. فشل الحفظ لا يوقف عرض النتيجة."""
        try:
            names = "، ".join(r["name"] for r in result.recommendations)
            self.db.add_message(session_id, "user", question)
            self.db.add_message(session_id, "assistant", f"{result.summary} المطاعم: {names}".strip())
            if result.recommendations:
                self.db.save_recommendations(session_id, question, result.recommendations, result.source)
        except AppError as exc:
            result.warning = (result.warning + " " if result.warning else "") + exc.user_message
