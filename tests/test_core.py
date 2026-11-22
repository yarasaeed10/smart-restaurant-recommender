"""
اختبارات وحدات المشروع (المسؤولة: لمى الأسمري)
التشغيل: pytest -q
هذه الاختبارات لا تحتاج مفتاح OpenAI ولا إنترنت.
"""
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.chain import validate_user_input  # noqa: E402
from src.data_loader import load_restaurants, row_to_text, validate_dataframe  # noqa: E402
from src.database import Database  # noqa: E402
from src.errors import InvalidUserInputError, UnsupportedFileError  # noqa: E402
from src.fallback import extract_preferences_rule_based, local_search  # noqa: E402

DATA = ROOT / "data" / "restaurants.csv"


@pytest.fixture
def df():
    return load_restaurants(DATA)


@pytest.fixture
def db(tmp_path):
    return Database(tmp_path / "test.db")


# ------------------------------------------------------------------ البيانات
def test_dataset_loads_with_enough_restaurants(df):
    assert len(df) >= 30
    assert df["id"].is_unique


def test_text_contains_key_fields(df):
    text = row_to_text(df.iloc[0])
    assert "اسم المطعم" in text and "التقييم" in text and df.iloc[0]["name"] in text


def test_unsupported_extension(tmp_path):
    f = tmp_path / "data.txt"
    f.write_text("x")
    with pytest.raises(UnsupportedFileError):
        load_restaurants(f)


def test_missing_columns():
    with pytest.raises(UnsupportedFileError):
        validate_dataframe(pd.DataFrame({"name": ["a"]}))


# ------------------------------------------------------------------ المدخلات
@pytest.mark.parametrize("bad", ["", "  ", "؟؟", "؟؟؟؟؟", "!!!!!", "123456", "a" * 501])
def test_invalid_inputs_rejected(bad):
    with pytest.raises(InvalidUserInputError):
        validate_user_input(bad)


def test_valid_input_passes():
    assert validate_user_input("  مطعم في جدة ") == "مطعم في جدة"


# ------------------------------------------------------------------ البحث الاحتياطي
def test_rule_based_extraction():
    p = extract_preferences_rule_based("أبي مطعم بحري رخيص في جده للعائلة")
    assert p["city"] == "جدة"
    assert p["cuisine"] == "مأكولات بحرية"
    assert p["max_price_level"] == 1
    assert p["family_friendly"] is True


def test_local_search_respects_city(df):
    recs = local_search(df, "مطعم بحري في جدة")
    assert recs, "يجب أن يرجع نتائج"
    ids = [r["restaurant_id"] for r in recs]
    cities = df.set_index("id").loc[ids, "city"].tolist()
    assert cities[0] == "جدة"
    assert all(0 <= r["match_score"] <= 100 for r in recs)


# ------------------------------------------------------------------ قاعدة البيانات
def test_messages_and_window(db):
    sid = db.create_session()
    for i in range(10):
        db.add_message(sid, "user" if i % 2 == 0 else "assistant", f"رسالة {i}")
    last = db.get_messages(sid, limit=4)
    assert [m["content"] for m in last] == ["رسالة 6", "رسالة 7", "رسالة 8", "رسالة 9"]


def test_favorites_no_duplicates(db):
    sid = db.create_session()
    db.add_favorite(sid, 9, "لؤلؤة البحر")
    db.add_favorite(sid, 9, "لؤلؤة البحر")
    assert len(db.get_favorites(sid)) == 1
    db.remove_favorite(sid, 9)
    assert db.get_favorites(sid) == []


def test_recommendations_and_stats(db):
    sid = db.create_session()
    db.add_message(sid, "user", "مطعم بحري")
    db.save_recommendations(sid, "مطعم بحري", [
        {"restaurant_id": 9, "name": "لؤلؤة البحر", "reason": "بحري", "match_score": 90},
    ])
    db.add_feedback(sid, "مطعم بحري", True)
    stats = db.get_stats()
    assert stats["total_questions"] == 1
    assert stats["total_recommendations"] == 1
    assert stats["helpful_ratio"] == 100
    assert db.get_history(sid)[0]["restaurant_name"] == "لؤلؤة البحر"


# ------------------------------------------------------------------ المحرك بدون مفتاح (وضع الطوارئ)
def test_engine_without_api_key_uses_local_search(df, db, tmp_path):
    import dataclasses

    from src.config import get_settings
    from src.chain import RecommendationEngine

    settings = dataclasses.replace(get_settings(), openai_api_key="", db_path=tmp_path / "x.db")
    engine = RecommendationEngine(settings, df, db)
    assert not engine.llm_ready
    sid = db.create_session()
    res = engine.recommend("مطعم بحري عائلي في جدة", sid)
    assert res.source == "local"
    assert res.warning  # رسالة توضح أن المفتاح غير موجود
    assert 1 <= len(res.recommendations) <= 3
    # تم حفظ السؤال والرد والترشيحات
    assert len(db.get_messages(sid)) == 2
    assert len(db.get_history(sid)) == len(res.recommendations)


def test_local_follow_up_keeps_city(df, db, tmp_path):
    import dataclasses

    from src.config import get_settings
    from src.chain import RecommendationEngine

    settings = dataclasses.replace(get_settings(), openai_api_key="", db_path=tmp_path / "y.db")
    engine = RecommendationEngine(settings, df, db)
    sid = db.create_session()
    first = engine.recommend("مطعم بحري عائلي في جدة", sid)
    second = engine.recommend("طيب أبي أرخص", sid)
    assert second.preferences.get("city") == "جدة"
    cities = df.set_index("id").loc[[r["restaurant_id"] for r in second.recommendations], "city"]
    assert cities.iloc[0] == "جدة"
    assert first.recommendations
