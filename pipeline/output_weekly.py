import json
import os
from datetime import date, datetime, timezone, timedelta
from config import WEEKLY_DIR, DAILY_DIR
from utils import get_week_start, get_week_end, iso_week_str


def run(target_date_str: str):
    """Aggregate daily files into a weekly JSON file."""
    os.makedirs(WEEKLY_DIR, exist_ok=True)

    target_date = date.fromisoformat(target_date_str)
    week_str = iso_week_str(target_date)
    week_start = get_week_start(target_date)
    week_end = get_week_end(target_date)

    # Collect all daily files within the week
    days = []
    current = week_start
    while current <= week_end:
        day_file = os.path.join(DAILY_DIR, f"{current.isoformat()}.json")
        if os.path.exists(day_file):
            with open(day_file, "r", encoding="utf-8") as f:
                days.append(json.load(f))
        current += timedelta(days=1)

    weekly_data = {
        "week": week_str,
        "start_date": week_start.isoformat(),
        "end_date": week_end.isoformat(),
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "weekly",
        "days": days,
    }

    out_path = os.path.join(WEEKLY_DIR, f"{week_str}.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(weekly_data, f, ensure_ascii=False, indent=2)

    total_articles = sum(
        sum(len(c["articles"]) for c in day.get("categories", []))
        for day in days
    )
    print(f"[output_weekly] Written {out_path} (week {week_str}, {len(days)} days, {total_articles} articles)")


if __name__ == "__main__":
    run("2026-05-23")
