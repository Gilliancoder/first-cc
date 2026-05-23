import json
import os
from datetime import datetime, timezone
from config import CATEGORIES, DAILY_DIR
from utils import slugify


def run(articles: list[dict], target_date: str):
    """Write a daily JSON file with articles grouped by category."""
    os.makedirs(DAILY_DIR, exist_ok=True)

    # Use the categories list from config (now 4 categories with uncategorized)
    grouped: dict[str, list] = {c["id"]: [] for c in CATEGORIES}
    for article in articles:
        cat_id = article.get("category_id", "uncategorized")
        if cat_id not in grouped:
            cat_id = "uncategorized"
        grouped.setdefault(cat_id, []).append(article)

    daily_data = {
        "date": target_date,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "daily",
        "categories": [],
    }

    for category in CATEGORIES:
        cat_id = category["id"]
        cat_articles = grouped.get(cat_id, [])

        formatted_articles = []
        for a in cat_articles:
            article_id = slugify(a.get("sender", ""), a.get("title", ""))
            formatted = {
                "id": article_id,
                "sender": a.get("sender", ""),
                "title": a.get("title", ""),
                "paragraphs": a.get("paragraphs", [{"en": a.get("body", ""), "zh": ""}]),
                "sections": a.get("sections", []),
                "recap_en": a.get("recap_en", a.get("recap", "")),
                "recap_zh": a.get("recap_zh", ""),
            }
            if a.get("source"):
                formatted["source"] = a["source"]
            if a.get("images"):
                formatted["images"] = a["images"]
            formatted_articles.append(formatted)

        daily_data["categories"].append(
            {
                "category": {
                    "id": category["id"],
                    "name_en": category["name_en"],
                    "name_zh": category["name_zh"],
                },
                "articles": formatted_articles,
            }
        )

    out_path = os.path.join(DAILY_DIR, f"{target_date}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(daily_data, f, ensure_ascii=False, indent=2)

    print(f"[output_daily] Written {out_path} ({sum(len(c['articles']) for c in daily_data['categories'])} articles)")
