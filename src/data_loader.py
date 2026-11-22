"""
data_loader.py — تحميل بيانات المطاعم وتحويلها إلى Documents (المسؤولة: يارا المالكي)

الخطوات:
1) قراءة ملف CSV والتحقق من الأعمدة والقيم.
2) تحويل كل مطعم إلى Document في LangChain:
   - page_content: نص وصفي يُحوَّل لاحقًا إلى Embedding.
   - metadata: الحقول المنظمة (المدينة، السعر، التقييم...) لاستخدامها في الفلترة.
"""
from __future__ import annotations

from pathlib import Path
from typing import List

import pandas as pd

from .errors import UnsupportedFileError

REQUIRED_COLUMNS = [
    "id", "name", "cuisine", "city", "district", "price_level", "avg_price_sar",
    "rating", "vegetarian_options", "family_friendly", "delivery", "outdoor_seating",
    "opening_hours", "specialties", "description",
]

PRICE_LABELS = {1: "اقتصادي", 2: "متوسط", 3: "مرتفع", 4: "فاخر"}


def load_restaurants(path: Path | str) -> pd.DataFrame:
    """يقرأ ملف المطاعم ويتحقق منه. يرمي UnsupportedFileError إذا كان الملف غير صالح."""
    path = Path(path)
    if path.suffix.lower() != ".csv":
        raise UnsupportedFileError(f"امتداد غير مدعوم: {path.suffix}")
    if not path.exists():
        raise UnsupportedFileError(f"الملف غير موجود: {path}")

    try:
        df = pd.read_csv(path, encoding="utf-8")
    except Exception as exc:  # ملف تالف أو ترميز خاطئ
        raise UnsupportedFileError(f"تعذر قراءة الملف: {exc}") from exc

    return validate_dataframe(df)


def validate_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """يتأكد من وجود الأعمدة المطلوبة وينظف القيم."""
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise UnsupportedFileError(f"أعمدة ناقصة: {', '.join(missing)}")

    df = df.copy()
    df = df.dropna(subset=["name", "city", "cuisine"])
    df["price_level"] = pd.to_numeric(df["price_level"], errors="coerce").fillna(2).astype(int).clip(1, 4)
    df["avg_price_sar"] = pd.to_numeric(df["avg_price_sar"], errors="coerce").fillna(0).astype(int)
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0).clip(0, 5)
    for col in ["vegetarian_options", "family_friendly", "delivery", "outdoor_seating"]:
        df[col] = df[col].astype(str).str.strip().isin(["نعم", "yes", "Yes", "1", "True", "true"])
    for col in ["name", "cuisine", "city", "district", "specialties", "description", "opening_hours"]:
        df[col] = df[col].fillna("").astype(str).str.strip()

    if df.empty:
        raise UnsupportedFileError("الملف لا يحتوي على أي مطعم صالح.")
    return df.reset_index(drop=True)


def _yes_no(value: bool) -> str:
    return "نعم" if value else "لا"


def row_to_text(row: pd.Series) -> str:
    """يبني النص الوصفي للمطعم — هذا النص هو ما يُحوَّل إلى Embedding."""
    return (
        f"اسم المطعم: {row['name']}\n"
        f"نوع المطبخ: {row['cuisine']}\n"
        f"الموقع: {row['city']} - حي {row['district']}\n"
        f"مستوى السعر: {PRICE_LABELS.get(int(row['price_level']), 'متوسط')} "
        f"(متوسط {row['avg_price_sar']} ريال للشخص)\n"
        f"التقييم: {row['rating']} من 5\n"
        f"خيارات نباتية: {_yes_no(row['vegetarian_options'])} | "
        f"مناسب للعائلات: {_yes_no(row['family_friendly'])} | "
        f"توصيل: {_yes_no(row['delivery'])} | جلسات خارجية: {_yes_no(row['outdoor_seating'])}\n"
        f"أوقات العمل: {row['opening_hours']}\n"
        f"أشهر الأطباق: {row['specialties'].replace('؛', '،')}\n"
        f"الوصف: {row['description']}"
    )


def row_to_metadata(row: pd.Series) -> dict:
    """البيانات المنظمة المرفقة مع كل Document (تُستخدم للفلترة في Chroma)."""
    return {
        "id": int(row["id"]),
        "name": row["name"],
        "cuisine": row["cuisine"],
        "city": row["city"],
        "district": row["district"],
        "price_level": int(row["price_level"]),
        "avg_price_sar": int(row["avg_price_sar"]),
        "rating": float(row["rating"]),
        "vegetarian_options": bool(row["vegetarian_options"]),
        "family_friendly": bool(row["family_friendly"]),
        "delivery": bool(row["delivery"]),
        "outdoor_seating": bool(row["outdoor_seating"]),
        "opening_hours": row["opening_hours"],
        "specialties": row["specialties"],
    }


def dataframe_to_documents(df: pd.DataFrame) -> List["Document"]:
    """Document Loader: يحوّل جدول المطاعم إلى قائمة Documents في LangChain."""
    from langchain_core.documents import Document  # استيراد متأخر لتسهيل الاختبارات

    return [
        Document(page_content=row_to_text(row), metadata=row_to_metadata(row))
        for _, row in df.iterrows()
    ]
