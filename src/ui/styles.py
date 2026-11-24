"""
styles.py — تنسيق الواجهة CSS (المسؤولة: رنيم حكمي)

الألوان والخطوط مأخوذة من تصميم فيقما (Design Tokens):
كحلي فيروزي #0F3D4C، فيروزي #12808A، بنفسجي الشعار #5B4B9A، زعفراني #E3A33A، خلفية كريمية #F7F4EE.
الخط: Tajawal محمّل من مجلد static (يحتاج enableStaticServing في .streamlit/config.toml).
"""

COLORS = {
    "deep": "#0F3D4C",
    "teal": "#12808A",
    "teal_light": "#E3F2F1",
    "purple": "#5B4B9A",
    "saffron": "#E3A33A",
    "saffron_light": "#FCF1DE",
    "bg": "#F7F4EE",
    "ink": "#1D2A32",
    "muted": "#6B7780",
    "line": "#E8E2D6",
}

GLOBAL_CSS = f"""
<style>
@font-face {{ font-family: 'Tajawal'; src: url('app/static/Tajawal-Regular.ttf') format('truetype'); font-weight: 400; }}
@font-face {{ font-family: 'Tajawal'; src: url('app/static/Tajawal-Medium.ttf') format('truetype'); font-weight: 500; }}
@font-face {{ font-family: 'Tajawal'; src: url('app/static/Tajawal-Bold.ttf') format('truetype'); font-weight: 700; }}
@font-face {{ font-family: 'Tajawal'; src: url('app/static/Tajawal-ExtraBold.ttf') format('truetype'); font-weight: 800; }}

html, body, [class*="css"], .stApp, .stMarkdown, button, input, textarea, select {{
    font-family: 'Tajawal', sans-serif !important;
}}
.stApp {{ direction: rtl; background: {COLORS['bg']}; color: {COLORS['ink']}; }}
.stMarkdown, .stText, p, h1, h2, h3, h4, label {{ text-align: right; }}
/* إخفاء عناصر Streamlit الافتراضية غير المهمة */
#MainMenu, footer {{ visibility: hidden; }}
.block-container {{ padding-top: 1.6rem; max-width: 1180px; }}

/* ------------------------------------------------ الشريط الجانبي */
section[data-testid="stSidebar"] {{ background: {COLORS['deep']}; }}
section[data-testid="stSidebar"] * {{ color: #FFFFFFDD; }}
section[data-testid="stSidebar"] .side-title {{ font-size: 1.1rem; font-weight: 700; color: #fff; margin: .6rem 0 0; }}
section[data-testid="stSidebar"] .side-sub {{ font-size: .82rem; opacity: .65; }}
.logo-box {{ background: transparent; padding: 6px 4px 10px; text-align: center; }}
.logo-box img {{ max-width: 100%; }}
.status-box {{ background: rgba(255,255,255,.07); border-radius: 14px; padding: 12px 14px; font-size: .85rem; line-height: 1.9; }}
.status-box b {{ color: {COLORS['saffron']} !important; }}
.team {{ font-size: .82rem; line-height: 1.8; opacity: .85; }}
.team b {{ color: {COLORS['saffron']} !important; }}

/* ------------------------------------------------ الهيدر */
.hero {{
    background: linear-gradient(100deg, {COLORS['deep']} 0%, {COLORS['teal']} 50%, {COLORS['purple']} 100%);
    border-radius: 24px; padding: 26px 30px; color: #fff;
    display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-bottom: 14px;
}}
.hero h1 {{ color: #fff; font-size: 2.4rem; font-weight: 800; margin: 0; padding: 0; line-height: 1.2; }}
.hero p {{ color: #ffffffE0; margin: 4px 0 0; font-size: 1rem; font-weight: 500; }}
.pill-status {{ background: rgba(255,255,255,.16); border-radius: 999px; padding: 8px 14px; font-size: .82rem; white-space: nowrap; direction: ltr; }}
.dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-inline-start: 6px; }}

/* ------------------------------------------------ الشرائح الصغيرة Chips */
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 6px 0 10px; }}
.chip {{ background: {COLORS['teal_light']}; color: {COLORS['teal']}; border-radius: 999px; padding: 4px 12px; font-size: .82rem; font-weight: 500; }}
.chip.dish {{ background: {COLORS['saffron_light']}; color: #9A6412; }}
.chip-label {{ color: {COLORS['muted']}; font-weight: 700; font-size: .88rem; }}
.src-badge {{ background: #EEEAF7; color: {COLORS['purple']}; border-radius: 8px; padding: 3px 10px; font-size: .75rem; font-weight: 700; direction: ltr; display: inline-block; }}
.src-badge.local {{ background: {COLORS['saffron_light']}; color: #9A6412; }}

/* ------------------------------------------------ بطاقة المطعم */
.r-card {{
    background: #fff; border: 1px solid {COLORS['line']}; border-radius: 20px; padding: 18px 18px 12px;
    box-shadow: 0 8px 24px rgba(15,61,76,.08); height: 100%;
}}
.r-top {{ display: flex; justify-content: space-between; align-items: center; }}
.r-rank {{ background: {COLORS['saffron_light']}; color: #9A6412; border-radius: 999px; padding: 3px 10px; font-size: .75rem; font-weight: 700; }}
.r-match {{ color: {COLORS['teal']}; font-weight: 700; font-size: .82rem; }}
.r-name {{ font-size: 1.35rem; font-weight: 800; margin: 10px 0 4px; color: {COLORS['ink']}; }}
.r-meta {{ color: {COLORS['muted']}; font-size: .88rem; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
.r-stats {{ display: flex; gap: 18px; margin: 12px 0 8px; }}
.r-stats div {{ display: flex; flex-direction: column; }}
.r-stats b {{ font-size: 1rem; }}
.r-stats span {{ font-size: .7rem; color: {COLORS['muted']}; }}
.r-bar {{ background: #ECE7DD; border-radius: 999px; height: 6px; overflow: hidden; margin: 6px 0 10px; }}
.r-bar > div {{ height: 6px; border-radius: 999px; background: linear-gradient(90deg, {COLORS['teal']}, {COLORS['purple']}); margin-inline-start: 0; }}
.r-reason {{ color: #46535C; font-size: .9rem; line-height: 1.7; }}

/* ------------------------------------------------ عناصر Streamlit */
.stButton > button {{
    border-radius: 12px; border: 1.5px solid {COLORS['teal']}; color: {COLORS['teal']};
    background: #fff; font-weight: 700; width: 100%;
}}
.stButton > button:hover {{ background: {COLORS['teal_light']}; border-color: {COLORS['teal']}; color: {COLORS['teal']}; }}
div[data-testid="stChatInput"] textarea {{ direction: rtl; text-align: right; }}
div[data-testid="stChatMessage"] {{ background: #fff; border: 1px solid {COLORS['line']}; border-radius: 20px; padding: 14px 18px; }}
.metric-card {{ background: #fff; border: 1px solid {COLORS['line']}; border-radius: 18px; padding: 18px; text-align: center; }}
.metric-card .v {{ font-size: 2rem; font-weight: 800; color: {COLORS['teal']}; }}
.metric-card .l {{ color: {COLORS['muted']}; font-size: .9rem; }}
</style>
"""
