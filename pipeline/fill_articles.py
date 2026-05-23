import feedparser
import re
from config import WSJ_RSS_FEEDS, CATEGORIES
from utils import slugify, split_paragraphs
from translate import run as run_translate
from recap import run as run_recap

WSJ_SENDER = "WSJ"


def run(articles: list[dict], target_date: str) -> list[dict]:
    """Fill empty categories (macroeconomics, industry-focus, special-topics) with WSJ articles.

    Uncategorized is excluded from the fill requirement — it remains empty if there are no articles.
    WSJ fill articles get the same treatment as regular newsletters (translate + bilingual recap).
    """
    # Group articles by category
    category_articles: dict[str, list] = {c["id"]: [] for c in CATEGORIES}
    for article in articles:
        cat_id = article.get("category_id", "uncategorized")
        if cat_id in category_articles:
            category_articles[cat_id].append(article)

    # The 3 main categories that must have articles
    MAIN_CATEGORIES = ["macroeconomics", "industry-focus", "special-topics"]

    new_articles = []
    for category in CATEGORIES:
        cat_id = category["id"]
        if cat_id not in MAIN_CATEGORIES:
            continue  # Skip uncategorized

        if len(category_articles.get(cat_id, [])) == 0:
            print(f"[fill] Category '{cat_id}' is empty — fetching WSJ article")
            wsj_articles = _fetch_wsj(cat_id, target_date)
            new_articles.extend(wsj_articles)

    # Process fill articles the same way as regular newsletters
    if new_articles:
        print(f"[fill] Processing {len(new_articles)} WSJ fill articles")
        new_articles = run_translate(new_articles)
        new_articles = run_recap(new_articles)

    return articles + new_articles


def _fetch_wsj(category_id: str, target_date: str) -> list[dict]:
    """Fetch 1-2 articles from WSJ RSS for the given category."""
    feed_url = WSJ_RSS_FEEDS.get(category_id)
    if not feed_url:
        print(f"  [fill] No RSS feed configured for '{category_id}'")
        return []

    try:
        feed = feedparser.parse(feed_url)
    except Exception as e:
        print(f"  [fill] Failed to parse RSS feed: {e}")
        return []

    articles = []
    for entry in feed.entries[:2]:
        title = entry.get("title", "WSJ Article").strip()

        # Get content — try multiple fields, prefer longer body
        body = ""
        for c in (entry.get("content") or []):
            v = c.get("value", "")
            if v:
                body += v + "\n"
        if not body.strip():
            body = (entry.get("summary_detail") or {}).get("value", "")
        if not body.strip():
            body = entry.get("summary", "")

        # Clean HTML from body
        body = _strip_html(body)

        if len(body) < 80:
            continue

        slug = slugify(WSJ_SENDER, title)
        articles.append({
            "sender": WSJ_SENDER,
            "title": f"{title}",
            "body": body,
            "category_id": category_id,
            "source": "WSJ",
            "received_date": target_date,
        })

    return articles[:1]


def _strip_html(text: str) -> str:
    """Remove HTML tags."""
    clean = re.sub(r"<[^>]+>", "", text)
    import html
    clean = html.unescape(clean)
    clean = re.sub(r"\n{3,}", "\n\n", clean)
    return clean.strip()
