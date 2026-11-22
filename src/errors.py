"""
errors.py — الأخطاء المخصصة ورسائلها بالعربي (المسؤولة: لمى الأسمري)

كل خطأ متوقع في النظام له Class خاص ورسالة واضحة للمستخدم،
حتى لا يظهر للمستخدم Traceback إنجليزي غير مفهوم.
"""


class AppError(Exception):
    """الأب لكل أخطاء التطبيق. user_message هي الرسالة التي تظهر في الواجهة."""

    user_message = "حدث خطأ غير متوقع، حاول مرة أخرى."

    def __init__(self, detail: str = ""):
        super().__init__(detail or self.user_message)
        self.detail = detail


class MissingAPIKeyError(AppError):
    user_message = (
        "مفتاح OpenAI غير موجود. أضيفي OPENAI_API_KEY في ملف ‎.env‎ "
        "أو في Secrets على Streamlit Cloud. يعمل النظام الآن بوضع البحث المحلي."
    )


class LLMUnavailableError(AppError):
    user_message = (
        "تعذّر الاتصال بالنموذج اللغوي (OpenAI) حاليًا. "
        "عرضنا لك نتائج من البحث المحلي بدلًا من ذلك."
    )


class InvalidUserInputError(AppError):
    user_message = "الطلب غير واضح. اكتب ما تبحث عنه، مثل: مطعم بحري عائلي في جدة بسعر متوسط."


class UnsupportedFileError(AppError):
    user_message = "نوع الملف غير مدعوم. الملفات المقبولة: CSV فقط وبنفس أعمدة ملف المطاعم."


class DatabaseUnavailableError(AppError):
    user_message = "قاعدة البيانات غير متاحة حاليًا، لن يتم حفظ السجل في هذه الجلسة."


class InvalidModelResponseError(AppError):
    user_message = (
        "رد النموذج لم يكن بالشكل المتوقع، فاستخدمنا نتائج البحث مباشرة. "
        "جرّب إعادة صياغة الطلب."
    )
