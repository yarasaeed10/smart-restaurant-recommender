"""
fallback.py — البحث المحلي الاحتياطي (المسؤولة: لمى الأسمري)

يُستخدم فقط عندما:
- لا يوجد مفتاح OpenAI، أو
- تعطل الاتصال بالنموذج اللغوي، أو
- رجع النموذج ردًا غير صالح.

يعتمد على قواعد بسيطة (كلمات مفتاحية) وفلترة مباشرة على جدول المطاعم،
حتى لا يتوقف النظام أثناء العرض. هذا ليس بديلًا عن LangChain بل خطة طوارئ.
"""
from __future__ import annotations

import re
from typing import Dict, List

import pandas as pd

PRICE_WORDS = {
    1: ["رخيص", "رخيصة", "اقتصادي", "اقتصادية", "طلاب", "طالب", "ميزانية محدودة"],
    2: ["متوسط", "معقول", "مناسب السعر"],
    3: ["غالي", "مرتفع"],
    4: ["فاخر", "فخم", "راقي", "راقية", "مناسبة خاصة"],
}

CUISINE_SYNONYMS = {
    "مأكولات بحرية": ["بحري", "بحرية", "سمك", "روبيان", "سي فود"],
    "سعودي": ["سعودي", "شعبي", "كبسة", "مندي", "مظبي", "حجازي", "نجدي"],
    "ياباني": ["ياباني", "سوشي", "رامن"],
    "إيطالي": ["إيطالي", "ايطالي", "بيتزا", "باستا"],
    "صحي": ["صحي", "دايت", "سعرات", "رجيم"],
    "مقهى": ["مقهى", "كافيه", "قهوة", "كوفي", "مذاكرة"],
    "حلويات": ["حلويات", "حلا", "كنافة", "بانكيك"],
    "شامي": ["شامي", "شاورما", "سوري"],
    "لبناني": ["لبناني"],
    "هندي": ["هندي", "برياني", "كاري"],
    "ستيك": ["ستيك", "ستيك هاوس"],
    "أمريكي": ["برجر", "أمريكي", "امريكي"],
    "تركي": ["تركي", "كباب"],
    "صيني": ["صيني", "نودلز"],
    "كوري": ["كوري"],
    "تايلندي": ["تايلندي"],
    "مكسيكي": ["مكسيكي", "تاكو"],
    "يمني": ["يمني", "حنيذ"],
    "مصري": ["مصري", "كشري", "فول", "طعمية"],
    "فرنسي": ["فرنسي"],
    "إيراني": ["إيراني", "ايراني", "فارسي"],
    "أفغاني": ["أفغاني", "افغاني", "بخاري"],
}

CITY_SYNONYMS = {
    "مكة المكرمة": ["مكة", "مكه"],
    "المدينة المنورة": ["المدينة", "المدينه"],
    "الرياض": ["الرياض", "رياض"],
    "جدة": ["جدة", "جده"],
    "الدمام": ["الدمام"],
    "الخبر": ["الخبر"],
    "أبها": ["أبها", "ابها"],
    "الطائف": ["الطائف"],
    "الأحساء": ["الأحساء", "الاحساء", "الهفوف"],
}


def extract_preferences_rule_based(text: str) -> Dict:
    """استخراج بسيط للتفضيلات بالكلمات المفتاحية (بدون نموذج لغوي)."""
    prefs: Dict = {}
    for city, words in CITY_SYNONYMS.items():
        if any(w in text for w in words):
            prefs["city"] = city
            break
    for cuisine, words in CUISINE_SYNONYMS.items():
        if any(w in text for w in words):
            prefs["cuisine"] = cuisine
            break
    for level, words in PRICE_WORDS.items():
        if any(w in text for w in words):
            prefs["max_price_level"] = level
            break
    budget = re.search(r"(\d{2,4})\s*(ريال|ر\.س|SAR)", text)
    if budget:
        prefs["max_budget_sar"] = int(budget.group(1))
    if any(w in text for w in ["عائل", "عايل", "أطفال", "اطفال", "عيال"]):
        prefs["family_friendly"] = True
    if any(w in text for w in ["نباتي", "نباتية", "فيجن"]):
        prefs["vegetarian"] = True
    if any(w in text for w in ["توصيل", "ديليفري", "يوصل"]):
        prefs["delivery"] = True
    if any(w in text for w in ["خارجي", "خارجية", "برا", "إطلالة", "اطلالة"]):
        prefs["outdoor_seating"] = True
    return prefs


def _tokens(text: str) -> List[str]:
    return [t for t in re.split(r"[\s،,.؟?!]+", text) if len(t) > 2]


def local_search(df: pd.DataFrame, query: str, prefs: Dict | None = None, top_n: int = 3) -> List[Dict]:
    """يرجع أفضل المطاعم حسب نقاط بسيطة: تطابق الشروط + كلمات الطلب + التقييم."""
    prefs = prefs if prefs is not None else extract_preferences_rule_based(query)
    words = _tokens(query)
    results = []
    for _, r in df.iterrows():
        score = 0.0
        if prefs.get("city"):
            score += 40 if r["city"] == prefs["city"] else -100
        if prefs.get("cuisine"):
            score += 30 if r["cuisine"] == prefs["cuisine"] else -10
        if prefs.get("max_price_level"):
            score += 10 if r["price_level"] <= prefs["max_price_level"] else -15 * (r["price_level"] - prefs["max_price_level"])
        if prefs.get("max_budget_sar"):
            score += 10 if r["avg_price_sar"] <= prefs["max_budget_sar"] else -60
        for flag, col in [("family_friendly", "family_friendly"), ("vegetarian", "vegetarian_options"),
                          ("delivery", "delivery"), ("outdoor_seating", "outdoor_seating")]:
            if prefs.get(flag):
                score += 8 if r[col] else -15
        haystack = f"{r['name']} {r['cuisine']} {r['specialties']} {r['description']}"
        score += sum(3 for w in words if w in haystack)
        score += float(r["rating"]) * 2
        results.append((score, r))

    results.sort(key=lambda x: x[0], reverse=True)
    best = results[:top_n]
    max_score = max((s for s, _ in best), default=1) or 1
    output = []
    for s, r in best:
        output.append({
            "restaurant_id": int(r["id"]),
            "name": r["name"],
            "reason": f"{r['cuisine']} في {r['city']} - {r['district']}، تقييمه {r['rating']}، "
                      f"ومتوسط السعر {r['avg_price_sar']} ريال للشخص.",
            "suggested_dishes": [d.strip() for d in str(r["specialties"]).split("؛")][:2],
            "match_score": max(0, min(100, int(s / max_score * 85))),
        })
    return output
