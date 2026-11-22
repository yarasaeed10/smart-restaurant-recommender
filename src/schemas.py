"""
schemas.py — شكل المخرجات المنظمة Structured Output (المسؤولة: عائشة المالكي)

نستخدم Pydantic لتعريف الشكل الذي يجب أن يرجعه النموذج اللغوي،
بدل نص حر يصعب التعامل معه في الواجهة.
"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class UserPreferences(BaseModel):
    """تفضيلات المستخدم المستخرجة من رسالته (المرحلة الأولى في الـ Chain)."""

    city: Optional[str] = Field(None, description="المدينة المطلوبة بالعربي كما في البيانات، مثل: جدة، الرياض، مكة المكرمة")
    cuisine: Optional[str] = Field(None, description="نوع المطبخ بالعربي، مثل: سعودي، ياباني، إيطالي، مأكولات بحرية، صحي")
    max_price_level: Optional[int] = Field(None, ge=1, le=4, description="أعلى مستوى سعر مقبول: 1 اقتصادي، 2 متوسط، 3 مرتفع، 4 فاخر")
    max_budget_sar: Optional[int] = Field(None, ge=0, description="الميزانية للشخص بالريال إن ذكرها المستخدم")
    family_friendly: Optional[bool] = Field(None, description="True إذا طلب مكانًا مناسبًا للعائلة")
    vegetarian: Optional[bool] = Field(None, description="True إذا طلب خيارات نباتية")
    delivery: Optional[bool] = Field(None, description="True إذا طلب توصيل")
    outdoor_seating: Optional[bool] = Field(None, description="True إذا طلب جلسات خارجية")
    occasion: Optional[str] = Field(None, description="المناسبة إن وُجدت: عشاء عمل، عائلة، أصدقاء، فطور، مذاكرة...")
    search_query: str = Field(..., description="جملة بحث قصيرة تلخص ما يريده المستخدم لاستخدامها في البحث الدلالي")
    is_food_related: bool = Field(True, description="False إذا كان الطلب لا علاقة له بالمطاعم أو الأكل")


class RestaurantRecommendation(BaseModel):
    """مطعم واحد مرشّح مع سبب الترشيح."""

    restaurant_id: int = Field(..., description="رقم id للمطعم كما ورد في السياق")
    name: str = Field(..., description="اسم المطعم كما ورد في السياق حرفيًا")
    reason: str = Field(..., description="سبب الترشيح في جملة أو جملتين مرتبطًا بطلب المستخدم")
    suggested_dishes: List[str] = Field(default_factory=list, description="طبق أو طبقان من أشهر أطباق المطعم")
    match_score: int = Field(..., ge=0, le=100, description="مدى تطابق المطعم مع الطلب من 0 إلى 100")


class RecommendationResponse(BaseModel):
    """الرد النهائي الذي يُعرض في الواجهة."""

    summary: str = Field(..., description="رد ودي مختصر للمستخدم بالعربي (جملتان إلى ثلاث)")
    recommendations: List[RestaurantRecommendation] = Field(default_factory=list, max_length=3)
    follow_up_question: Optional[str] = Field(None, description="سؤال متابعة اختياري يساعد على تحسين الترشيح")
