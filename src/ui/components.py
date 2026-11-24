"""
components.py — مكونات الواجهة القابلة لإعادة الاستخدام (المسؤولة: رنيم حكمي)

كل دالة ترجع HTML لعنصر واحد من تصميم فيقما:
Hero (الهيدر)، Chips (التفضيلات والأطباق)، RestaurantCard (بطاقة المطعم).
نستخدم html.escape لحماية الواجهة من أي نص غريب قادم من النموذج أو من البيانات.
"""
from __future__ import annotations

import base64
from html import escape
from pathlib import Path
from typing import Dict, Iterable, Optional

from ..data_loader import PRICE_LABELS

PREF_LABELS = {
    "family_friendly": "مناسب للعائلة",
    "vegetarian": "خيارات نباتية",
    "delivery": "توصيل",
    "outdoor_seating": "جلسات خارجية",
}


def image_to_data_uri(path: Path) -> str:
    """يحوّل صورة الشعار إلى data URI لعرضها داخل HTML."""
    data = base64.b64encode(Path(path).read_bytes()).decode()
    mime = "image/svg+xml" if str(path).endswith(".svg") else "image/png"
    return f"data:{mime};base64,{data}"


def hero_html(model_name: str, llm_ready: bool) -> str:
    status = f"متصل · OpenAI {escape(model_name)}" if llm_ready else "وضع البحث المحلي (بدون OpenAI)"
    color = "#7CF0B4" if llm_ready else "#F5C26B"
    return f"""
    <div class="hero">
      <div>
        <h1>مُرشِد</h1>
        <p>نظام ترشيح المطاعم الذكي — قل لي وش تشتهي، وفي أي مدينة، وكم ميزانيتك</p>
      </div>
      <div class="pill-status">{status}<span class="dot" style="background:{color}"></span></div>
    </div>"""


def chips_html(items: Iterable[str], label: Optional[str] = None, kind: str = "") -> str:
    chips = "".join(f'<span class="chip {kind}">{escape(str(i))}</span>' for i in items if i)
    lab = f'<span class="chip-label">{escape(label)}</span>' if label else ""
    return f'<div class="chips">{lab}{chips}</div>' if chips else ""


def preferences_to_labels(prefs: Dict) -> list:
    """يحوّل التفضيلات المستخرجة إلى كلمات قصيرة تُعرض للمستخدم (فهمت طلبك: ...)."""
    labels = []
    if prefs.get("city"):
        labels.append(prefs["city"])
    if prefs.get("cuisine"):
        labels.append(prefs["cuisine"])
    if prefs.get("max_price_level"):
        labels.append(f"سعر {PRICE_LABELS.get(int(prefs['max_price_level']), '')}")
    if prefs.get("max_budget_sar"):
        labels.append(f"حتى {prefs['max_budget_sar']} ريال")
    for key, lab in PREF_LABELS.items():
        if prefs.get(key):
            labels.append(lab)
    if prefs.get("occasion"):
        labels.append(prefs["occasion"])
    return labels


def restaurant_card_html(rank: int, rec: Dict, info: Optional[Dict]) -> str:
    """بطاقة مطعم واحدة. rec من النموذج، info من بيانات المطعم الأصلية."""
    info = info or {}
    score = int(rec.get("match_score", 0))
    price_level = int(info.get("price_level", 2))
    dishes = rec.get("suggested_dishes") or str(info.get("specialties", "")).split("؛")[:2]
    return f"""
    <div class="r-card">
      <div class="r-top">
        <span class="r-rank">الترشيح {rank}</span>
        <span class="r-match">تطابق {score}%</span>
      </div>
      <div class="r-name">{escape(rec.get('name', ''))}</div>
      <div class="r-meta">
        <span class="chip">{escape(str(info.get('cuisine', '')))}</span>
        <span>{escape(str(info.get('city', '')))} · {escape(str(info.get('district', '')))}</span>
      </div>
      <div class="r-stats">
        <div><b>{info.get('rating', '-')} / 5</b><span>التقييم</span></div>
        <div><b>{PRICE_LABELS.get(price_level, '-')}</b><span>مستوى السعر</span></div>
        <div><b>{info.get('avg_price_sar', '-')} ريال</b><span>للشخص</span></div>
      </div>
      <div class="r-bar"><div style="width:{max(4, min(score, 100))}%"></div></div>
      <div class="r-reason">{escape(rec.get('reason', ''))}</div>
      {chips_html([d.strip() for d in dishes], kind='dish')}
      <div class="r-meta" style="font-size:.78rem">أوقات العمل: {escape(str(info.get('opening_hours', '')))}</div>
    </div>"""


def metric_html(value, label: str) -> str:
    return f'<div class="metric-card"><div class="v">{escape(str(value))}</div><div class="l">{escape(label)}</div></div>'
