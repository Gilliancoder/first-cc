import json
import os
from datetime import datetime, timezone
from config import DATA_DIR, DAILY_DIR


def run():
    """Regenerate data/index.json manifest."""
    os.makedirs(DATA_DIR, exist_ok=True)

    # Scan daily files
    daily_entries = []
    if os.path.exists(DAILY_DIR):
        for fname in sorted(os.listdir(DAILY_DIR)):
            if fname.endswith(".json"):
                date_str = fname.replace(".json", "")
                filepath = os.path.join(DAILY_DIR, fname)
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                count = sum(len(c.get("articles", [])) for c in data.get("categories", []))
                daily_entries.append(
                    {"date": date_str, "article_count": count, "available": True}
                )

    index = {
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "daily": daily_entries,
    }

    out_path = os.path.join(DATA_DIR, "index.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"[output_index] Written {out_path} ({len(daily_entries)} days)")


if __name__ == "__main__":
    run()
