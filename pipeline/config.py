import os
from dotenv import load_dotenv

load_dotenv()

# Categories (order matters for display)
CATEGORIES = [
    {"id": "macroeconomics", "name_en": "Macroeconomics", "name_zh": "宏观经济"},
    {"id": "industry-focus", "name_en": "Industry Focus", "name_zh": "行业聚焦"},
    {"id": "special-topics", "name_en": "Special Topics", "name_zh": "专题研究"},
    {"id": "uncategorized", "name_en": "Other Articles", "name_zh": "其他文章"},
]

# ── AI API (DeepSeek) ──
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"  # DeepSeek-V3

# ── Microsoft Graph API (Outlook) ──
MS_GRAPH_CLIENT_ID = os.environ.get("MS_GRAPH_CLIENT_ID", "")
MS_GRAPH_TENANT_ID = os.environ.get("MS_GRAPH_TENANT_ID", "consumers")
MS_GRAPH_USER_ID = os.environ.get("MS_GRAPH_USER_ID", "gilshaw79@outlook.com")

# Output paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
PUBLIC_DIR = os.path.join(BASE_DIR, "public")
PUBLIC_DATA_DIR = os.path.join(PUBLIC_DIR, "data")
DAILY_DIR = os.path.join(DATA_DIR, "daily")
WEEKLY_DIR = os.path.join(DATA_DIR, "weekly")

# WSJ RSS feeds for fill articles
WSJ_RSS_FEEDS = {
    "macroeconomics": "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml",
    "industry-focus": "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
    "special-topics": "https://feeds.a.dj.com/rss/RSSWSJD.xml",
}
