# مُرشِد — نظام ترشيح المطاعم الذكي 🍽️

مشروع مادة **أساسيات LangChain** — جامعة الأمير مساعد بن عبدالرحمن

نظام يستقبل طلب المستخدم بلغته العادية (مثل: *"أبي مطعم بحري في جدة مناسب للعائلة وسعره متوسط"*)
ويرشّح له من 1 إلى 3 مطاعم مع سبب واضح لكل ترشيح، باستخدام **LangChain + OpenAI + Chroma + SQLite + Streamlit**.

## فريق العمل

| الاسم | الرقم الجامعي | الجزء المسؤولة عنه |
|---|---|---|
| يارا المالكي | 251000183 | البيانات، Document Loader، Embeddings، Chroma، Retriever |
| همس الشهري | 251001109 | الإعداد، ملف ‎.env‎، README، دمج الأجزاء، GitHub والنشر |
| عائشة المالكي | 251004046 | النموذج اللغوي، Prompts، Chains، Structured Output |
| رنيم حكمي | 251000215 | واجهة Streamlit وتصميم فيقما والعرض المباشر |
| لمى الأسمري | 251000016 | SQLite، Memory، معالجة الأخطاء، الاختبارات |

## مسار الطلب (Architecture)

```
المستخدم (Streamlit)
   │  رسالة نصية
   ▼
validate_user_input ──(خطأ)──► رسالة عربية واضحة
   │
   ▼
Extraction Chain:  ChatPromptTemplate + History │ ChatOpenAI.with_structured_output(UserPreferences)
   │  {city, cuisine, max_price_level, family_friendly, ...}
   ▼
Retriever:  Chroma (OpenAI Embeddings) + فلترة metadata + تخفيف تدريجي للشروط
   │  أقرب 6 مطاعم
   ▼
Recommendation Chain: ChatPromptTemplate + Context + History │ ChatOpenAI.with_structured_output(RecommendationResponse)
   │
   ▼
Guardrail: قبول المطاعم الموجودة في نتائج البحث فقط
   │
   ▼
SQLite: messages · recommendations · favorites · feedback   ──►  الواجهة (بطاقات المطاعم)

عند تعطل OpenAI أو عدم وجود المفتاح ← fallback.py (بحث محلي بالكلمات المفتاحية) حتى لا يتوقف العرض.
```

## هيكل الملفات

```
app.py                  واجهة Streamlit (5 صفحات)
src/config.py           الإعدادات وقراءة المفاتيح من .env أو Secrets
src/data_loader.py      قراءة CSV والتحقق منه وتحويله إلى Documents
src/vector_store.py     Embeddings + Chroma + Retriever مع الفلترة
src/prompts.py          تصميم الـ Prompts (استخراج + ترشيح)
src/schemas.py          نماذج Pydantic للمخرجات المنظمة
src/chain.py            RecommendationEngine: يربط كل المكونات
src/memory.py           ذاكرة المحادثة مخزنة في SQLite (BaseChatMessageHistory)
src/database.py         قاعدة بيانات SQLite (5 جداول)
src/fallback.py         البحث المحلي الاحتياطي
src/errors.py           الأخطاء المخصصة ورسائلها بالعربي
src/ui/styles.py        CSS بألوان وخطوط تصميم فيقما
src/ui/components.py    بطاقات المطاعم والهيدر والـ Chips
data/restaurants.csv    36 مطعمًا (بيانات تجريبية بأسماء افتراضية أعدها الفريق)
tests/test_core.py      19 اختبارًا (تعمل بدون مفتاح OpenAI)
static/                 خط Tajawal
assets/                 شعار الجامعة
```

## التشغيل على Google Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/yarasaeed10/smart-restaurant-recommender/blob/main/run_in_colab.ipynb)

افتحي الرابط وشغّلي الخلايا بالترتيب. الخلية الأخيرة تعطيك رابط الواجهة (trycloudflare.com).

**دفتر المشروع الكامل (مقسّم على جزئيات الفريق مع الاختبارات والديمو المتحرك):**
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/yarasaeed10/smart-restaurant-recommender/blob/main/Murshid_Restaurant_Recommender_LCH.ipynb)

## التشغيل على جهازك (VS Code)

```bash
git clone https://github.com/yarasaeed10/smart-restaurant-recommender.git
cd smart-restaurant-recommender
python -m venv .venv
# Windows:  .venv\Scripts\activate      Mac/Linux:  source .venv/bin/activate
pip install -r requirements.txt
copy .env.example .env      # على Mac/Linux:  cp .env.example .env
# افتحي .env وحطي مفتاح OpenAI الحقيقي مكان sk-...
streamlit run app.py
```

أول تشغيل يبني قاعدة المتجهات Chroma (يأخذ ثواني ويستهلك جزءًا بسيطًا من رصيد OpenAI)، والمرات التالية يعيد استخدامها.

## النشر على Streamlit Community Cloud

1. ادخلي **share.streamlit.io** بحساب GitHub.
2. **Create app** ← اختاري المستودع `yarasaeed10/smart-restaurant-recommender` والفرع `main` والملف `app.py`.
3. **Advanced settings ← Secrets** والصقي:
   ```toml
   OPENAI_API_KEY = "sk-..."
   ```
4. **Deploy**.

## الاختبارات

```bash
pytest -q
```

## الأمان

- لا يوجد أي مفتاح API داخل الكود. المفتاح يُقرأ من `.env` (محليًا) أو من Secrets (على السحابة).
- ملف `.env` موجود في `.gitignore` فلا يُرفع على GitHub.

## المكتبات الخارجية المستخدمة

LangChain (langchain-core, langchain-openai, langchain-chroma)، OpenAI API، ChromaDB، Streamlit، pandas، Pydantic، python-dotenv، pytest.
خط Tajawal مرخص برخصة SIL Open Font License (الملف `static/OFL.txt`).
