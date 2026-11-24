"""
app.py — واجهة المستخدم بـ Streamlit (المسؤولة: رنيم حكمي)

التشغيل:  streamlit run app.py

الصفحات:
1) المحادثة: يكتب المستخدم طلبه ويستلم 1-3 مطاعم مع السبب.
2) المفضلة: المطاعم التي حفظها المستخدم (من SQLite).
3) سجل الترشيحات: كل الترشيحات السابقة في الجلسة.
4) لوحة المعلومات: إحصائيات من قاعدة البيانات.
5) عن المشروع والبيانات: شرح المعمارية + رفع ملف مطاعم والتحقق منه.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Streamlit Cloud: Chroma يحتاج sqlite3 حديث. إذا توفرت pysqlite3 نستخدمها بدلًا من القديمة.
try:  # pragma: no cover
    __import__("pysqlite3")
    import sys

    sys.modules["sqlite3"] = sys.modules.pop("pysqlite3")
except ImportError:
    pass
# ---------------------------------------------------------------------------

import dataclasses
from pathlib import Path

import pandas as pd
import streamlit as st

from src.chain import RecommendationEngine
from src.config import BASE_DIR, get_settings
from src.data_loader import PRICE_LABELS, load_restaurants
from src.database import Database
from src.errors import AppError, DatabaseUnavailableError, UnsupportedFileError
from src.ui.components import (
    chips_html,
    hero_html,
    image_to_data_uri,
    metric_html,
    preferences_to_labels,
    restaurant_card_html,
)
from src.ui.styles import GLOBAL_CSS

st.set_page_config(page_title="مُرشِد | نظام ترشيح المطاعم الذكي", page_icon="🍽️", layout="wide")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

LOGO_PATH = BASE_DIR / "assets" / "university_logo_white.svg"  # شعار شفاف بنص أبيض للشريط الداكن
if not LOGO_PATH.exists():
    LOGO_PATH = BASE_DIR / "assets" / "university_logo.png"
SUGGESTIONS = [
    "مطعم بحري عائلي في جدة",
    "فطور شعبي رخيص في الرياض",
    "عشاء عمل فاخر ستيك",
    "مكان هادئ للمذاكرة في الرياض",
]
TEAM = ["يارا المالكي", "همس الشهري", "عائشة المالكي", "رنيم حكمي", "لمى الأسمري"]


# =========================================================================== تحميل المكونات
@st.cache_resource(show_spinner="جاري تجهيز قاعدة البيانات…")
def get_db(db_path: str):
    try:
        return Database(db_path)
    except DatabaseUnavailableError:
        return None


@st.cache_resource(show_spinner="جاري تحميل المطاعم وبناء قاعدة المتجهات…")
def get_engine(data_path: str, _db):
    settings = dataclasses.replace(get_settings(), data_path=Path(data_path))
    if Path(data_path).name != "restaurants.csv":
        # ملف مرفوع: نستخدم مجلد Chroma مستقل حتى لا نخرب الأصلي
        settings = dataclasses.replace(settings, chroma_dir=BASE_DIR / "chroma_db_uploaded")
    df = load_restaurants(data_path)
    return RecommendationEngine(settings, df, _db), df


settings = get_settings()
db = get_db(str(settings.db_path))

if "data_path" not in st.session_state:
    st.session_state.data_path = str(settings.data_path)

try:
    engine, df = get_engine(st.session_state.data_path, db)
except UnsupportedFileError as exc:
    st.error(f"{exc.user_message} ({exc.detail})")
    st.stop()

# جلسة المستخدم
if "session_id" not in st.session_state:
    try:
        st.session_state.session_id = db.create_session() if db else "offline"
    except AppError:
        st.session_state.session_id = "offline"
SESSION = st.session_state.session_id
st.session_state.setdefault("messages", [])      # [{role, content, result}]
st.session_state.setdefault("pending", None)      # اقتراح ضغطه المستخدم

restaurants_by_id = {int(r["id"]): r for r in df.to_dict("records")}


# =========================================================================== الشريط الجانبي
with st.sidebar:
    if LOGO_PATH.exists():
        st.markdown(
            f'<div class="logo-box"><img src="{image_to_data_uri(LOGO_PATH)}" alt="شعار الجامعة"/></div>',
            unsafe_allow_html=True,
        )
    st.markdown(
        '<div class="side-title">نظام ترشيح المطاعم الذكي</div>'
        '<div class="side-sub">مشروع مادة أساسيات LangChain</div>',
        unsafe_allow_html=True,
    )
    page = st.radio(
        "التنقل",
        ["المحادثة", "المفضلة", "سجل الترشيحات", "لوحة المعلومات", "عن المشروع والبيانات"],
        label_visibility="collapsed",
    )
    llm_state = "متصل ✓" if engine.llm_ready else "غير متصل (بحث محلي)"
    db_state = "متصلة ✓" if db else "غير متاحة"
    st.markdown(
        f'<div class="status-box"><b>حالة النظام</b><br>'
        f"النموذج: OpenAI {llm_state}<br>"
        f"قاعدة المتجهات: {len(df)} مطعم<br>"
        f"SQLite: {db_state}</div>",
        unsafe_allow_html=True,
    )
    if st.button("محادثة جديدة"):
        st.session_state.messages = []
        if db:
            try:
                db.clear_messages(SESSION)
            except AppError:
                pass
        st.rerun()
    st.markdown(
        '<div class="team"><b>فريق العمل</b><br>' + "<br>".join(TEAM) + "</div>", unsafe_allow_html=True
    )


# =========================================================================== دوال العرض
def render_result(result: dict, msg_index: int) -> None:
    """يعرض رد المساعد: التفضيلات المفهومة، الملخص، بطاقات المطاعم، والتقييم."""
    badge = (
        '<span class="src-badge">LangChain · RAG · Chroma</span>'
        if result["source"] == "llm"
        else '<span class="src-badge local">بحث محلي احتياطي</span>'
    )
    st.markdown(badge, unsafe_allow_html=True)
    labels = preferences_to_labels(result.get("preferences", {}))
    if labels:
        st.markdown(chips_html(labels, label="فهمت طلبك:"), unsafe_allow_html=True)
    if result.get("warning"):
        st.warning(result["warning"])
    st.markdown(f"**{result['summary']}**")

    recs = result.get("recommendations", [])
    if recs:
        cols = st.columns(len(recs))
        for i, (col, rec) in enumerate(zip(cols, recs), start=1):
            with col:
                info = restaurants_by_id.get(int(rec["restaurant_id"]))
                st.markdown(restaurant_card_html(i, rec, info), unsafe_allow_html=True)
                if st.button("♡ أضف للمفضلة", key=f"fav-{msg_index}-{rec['restaurant_id']}"):
                    try:
                        db.add_favorite(SESSION, rec["restaurant_id"], rec["name"])
                        st.toast(f"تمت إضافة {rec['name']} للمفضلة")
                    except (AppError, AttributeError):
                        st.toast("تعذر الحفظ: قاعدة البيانات غير متاحة")
    if result.get("follow_up_question"):
        st.caption(f"💬 {result['follow_up_question']}")

    c1, c2, _ = st.columns([1, 1, 4])
    for col, (label, helpful) in zip([c1, c2], [("👍 مفيدة", True), ("👎 غير مفيدة", False)]):
        with col:
            if st.button(label, key=f"fb-{msg_index}-{helpful}"):
                try:
                    db.add_feedback(SESSION, result.get("question", ""), helpful)
                    st.toast("شكرًا لتقييمك!")
                except (AppError, AttributeError):
                    st.toast("تعذر حفظ التقييم")


def handle_question(question: str) -> None:
    """يرسل السؤال للـ Engine ويحفظ النتيجة في الجلسة."""
    st.session_state.messages.append({"role": "user", "content": question})
    try:
        with st.spinner("أبحث لك عن أنسب المطاعم…"):
            res = engine.recommend(question, SESSION)
        result = dataclasses.asdict(res)
        result["question"] = question
        st.session_state.messages.append({"role": "assistant", "content": res.summary, "result": result})
    except AppError as exc:  # إدخال خاطئ مثلًا
        st.session_state.messages.append({"role": "assistant", "content": exc.user_message, "error": True})


# =========================================================================== الصفحات
if page == "المحادثة":
    st.markdown(hero_html(settings.chat_model, engine.llm_ready), unsafe_allow_html=True)
    if not engine.llm_ready and engine.init_error:
        st.info(engine.init_error.user_message)

    st.markdown('<span class="chip-label">جرّب:</span>', unsafe_allow_html=True)
    s_cols = st.columns(len(SUGGESTIONS))
    for col, s in zip(s_cols, SUGGESTIONS):
        with col:
            if st.button(s, key=f"sug-{s}"):
                st.session_state.pending = s

    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"], avatar="🧑" if msg["role"] == "user" else "🍽️"):
            if msg.get("result"):
                render_result(msg["result"], idx)
            elif msg.get("error"):
                st.error(msg["content"])
            else:
                st.markdown(msg["content"])

    typed = st.chat_input("اكتب طلبك… مثال: مطعم ياباني في الرياض للمناسبات")
    question = typed or st.session_state.pending
    if question:
        st.session_state.pending = None
        handle_question(question)
        st.rerun()

elif page == "المفضلة":
    st.header("المطاعم المفضلة")
    favs = db.get_favorites(SESSION) if db else []
    if not favs:
        st.info("ما عندك مطاعم مفضلة للحين. اضغط ♡ على أي ترشيح لحفظه.")
    for f in favs:
        info = restaurants_by_id.get(int(f["restaurant_id"]), {})
        c1, c2 = st.columns([5, 1])
        with c1:
            st.markdown(
                f"**{f['restaurant_name']}** — {info.get('cuisine', '')} · {info.get('city', '')} "
                f"· {PRICE_LABELS.get(int(info.get('price_level', 2)), '')} · {info.get('rating', '')}/5"
            )
        with c2:
            if st.button("حذف", key=f"del-{f['restaurant_id']}"):
                db.remove_favorite(SESSION, f["restaurant_id"])
                st.rerun()

elif page == "سجل الترشيحات":
    st.header("سجل الترشيحات")
    hist = db.get_history(SESSION) if db else []
    if not hist:
        st.info("لا يوجد سجل بعد. ابدأ محادثة من صفحة المحادثة.")
    else:
        table = pd.DataFrame(hist).rename(columns={
            "query": "الطلب", "restaurant_name": "المطعم", "reason": "السبب",
            "match_score": "التطابق %", "source": "المصدر", "created_at": "الوقت",
        })
        st.dataframe(table, use_container_width=True, hide_index=True)

elif page == "لوحة المعلومات":
    st.header("لوحة المعلومات")
    stats = db.get_stats() if db else {}
    c1, c2, c3, c4 = st.columns(4)
    c1.markdown(metric_html(len(df), "مطعم في قاعدة البيانات"), unsafe_allow_html=True)
    c2.markdown(metric_html(stats.get("total_questions", 0), "طلب من المستخدمين"), unsafe_allow_html=True)
    c3.markdown(metric_html(stats.get("total_recommendations", 0), "ترشيح محفوظ"), unsafe_allow_html=True)
    ratio = stats.get("helpful_ratio")
    c4.markdown(metric_html(f"{ratio}%" if ratio is not None else "—", "نسبة الرضا"), unsafe_allow_html=True)
    st.subheader("المطاعم حسب المدينة")
    st.bar_chart(df["city"].value_counts())
    st.subheader("المطاعم حسب نوع المطبخ")
    st.bar_chart(df["cuisine"].value_counts())
    if stats.get("top_restaurants"):
        st.subheader("الأكثر ترشيحًا")
        st.dataframe(pd.DataFrame(stats["top_restaurants"]).rename(
            columns={"restaurant_name": "المطعم", "n": "عدد مرات الترشيح"}), hide_index=True)

else:  # عن المشروع والبيانات
    st.header("عن المشروع")
    st.markdown(
        """
**مُرشِد** نظام يرشّح المطاعم حسب طلب المستخدم المكتوب بلغته العادية.

**مسار الطلب داخل النظام (LangChain Pipeline):**
1. التحقق من المدخلات (Error Handling).
2. **Extraction Chain**: ‏`Prompt | ChatOpenAI.with_structured_output(UserPreferences)` لاستخراج المدينة والمطبخ والسعر.
3. **Retrieval**: البحث الدلالي في **Chroma** باستخدام **OpenAI Embeddings** مع فلترة بالـ metadata.
4. **Recommendation Chain**: ‏`Prompt + Memory | ChatOpenAI.with_structured_output(RecommendationResponse)`.
5. **Guardrail**: نتأكد أن كل مطعم مرشّح موجود فعلًا في نتائج البحث.
6. الحفظ في **SQLite**: الرسائل والترشيحات والمفضلة والتقييم.
"""
    )
    st.subheader("بيانات المطاعم")
    st.caption("بيانات تجريبية أعدّها الفريق لأغراض المشروع (36 مطعمًا بأسماء افتراضية).")
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.subheader("رفع ملف مطاعم جديد (CSV)")
    up = st.file_uploader("ارفع ملف CSV بنفس الأعمدة", type=None)
    if up is not None:
        try:
            if not up.name.lower().endswith(".csv"):
                raise UnsupportedFileError(up.name)
            target = BASE_DIR / "data" / "uploaded_restaurants.csv"
            target.write_bytes(up.getvalue())
            new_df = load_restaurants(target)  # يتحقق من الأعمدة
            st.success(f"الملف صالح ✓ ويحتوي على {len(new_df)} مطعم.")
            st.dataframe(new_df.head(), hide_index=True)
            if st.button("استخدام هذا الملف في الترشيح"):
                st.session_state.data_path = str(target)
                st.rerun()
        except UnsupportedFileError as exc:
            st.error(f"{exc.user_message}\n\nالتفاصيل: {exc.detail}")
    if st.session_state.data_path != str(settings.data_path):
        if st.button("الرجوع لملف المطاعم الأصلي"):
            st.session_state.data_path = str(settings.data_path)
            st.rerun()
