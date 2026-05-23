#!/usr/bin/env python3
"""Daily Market Sense — Content Pipeline Orchestrator

Uses DeepSeek API for AI processing (translation + recap) and
Microsoft Graph API for Outlook email fetching.

Usage:
    python pipeline.py                          # Process today
    python pipeline.py --date 2026-05-23        # Process specific date
    python pipeline.py --skip-fetch             # Use cached raw articles
    python pipeline.py --dry-run                # Estimate token usage only
"""

import argparse
import json
import os
from datetime import date

from fetch_emails import run as run_fetch
from categorize import run as run_categorize
from translate import run as run_translate
from recap import run as run_recap
from fill_articles import run as run_fill
from screenshot import run as run_screenshot
from output_daily import run as run_output_daily
from output_index import run as run_output_index
from config import DATA_DIR, DEEPSEEK_API_KEY, MS_GRAPH_CLIENT_ID


def main():
    parser = argparse.ArgumentParser(description="Daily Market Sense Pipeline")
    parser.add_argument(
        "--date", default=str(date.today()), help="Date to process (YYYY-MM-DD)"
    )
    parser.add_argument("--mode", choices=["daily", "weekly", "full"], default="full")
    parser.add_argument("--skip-fetch", action="store_true", help="Skip email fetch")
    parser.add_argument("--include-read", action="store_true",
                        help="Include already-read emails (for re-processing)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Estimate token usage without making API calls")
    args = parser.parse_args()

    target_date = args.date

    # Step 1: Fetch emails
    if args.skip_fetch:
        cache_path = os.path.join(DATA_DIR, ".cache", f"raw_{target_date}.json")
        if os.path.exists(cache_path):
            with open(cache_path, "r", encoding="utf-8") as f:
                articles = json.load(f)
            print(f"[pipeline] Loaded {len(articles)} cached articles")
        else:
            print(f"[pipeline] No cache found at {cache_path}")
            return
    else:
        try:
            articles = run_fetch(target_date, include_read=args.include_read)
        except Exception as e:
            print(f"[pipeline] Email fetch failed: {e}")
            print("[pipeline] Make sure MS Graph API credentials are set:")
            print("  MS_GRAPH_CLIENT_ID, MS_GRAPH_CLIENT_SECRET, MS_GRAPH_TENANT_ID, MS_GRAPH_USER_ID")
            return

    if not articles:
        print(f"[pipeline] No new articles found for {target_date}.")
        return

    print(f"[pipeline] Fetched {len(articles)} articles")

    if args.dry_run:
        _estimate_tokens(articles)
        return

    # Step 2: Screenshot emails (before text processing)
    print("[pipeline] Taking email screenshots...")
    articles = run_screenshot(articles, target_date)

    # Step 3: Categorize
    print("[pipeline] Categorizing articles...")
    articles = run_categorize(articles)

    # Step 4: Translate
    print("[pipeline] Translating (DeepSeek)...")
    articles = run_translate(articles)

    # Step 5: Recaps
    print("[pipeline] Generating bilingual recaps (DeepSeek)...")
    articles = run_recap(articles)

    # Step 6: Fill empty categories
    print("[pipeline] Checking for empty categories...")
    articles = run_fill(articles, target_date)

    # Step 7: Output
    print("[pipeline] Writing output files...")
    run_output_daily(articles, target_date)
    run_output_index()

    with open(os.path.join(DATA_DIR, "daily", f"{target_date}.json"), encoding="utf-8") as f:
        daily_data = json.load(f)
    total = sum(1 for c in daily_data["categories"] for _ in c["articles"])
    print(f"[pipeline] Done! {total} articles saved for {target_date}")


def _estimate_tokens(articles: list[dict]):
    """Estimate token usage with DeepSeek pricing."""
    deepseek_input_price = 0.27   # per MTok
    deepseek_output_price = 1.10  # per MTok

    n = len(articles)
    trans_in = sum(int(len(a.get("body", "").split()) * 1.3) for a in articles)
    trans_out = int(trans_in * 0.8)
    recap_in = sum(min(int(len(a.get("body", "").split()) * 1.3), 4000) for a in articles)
    recap_out = n * 400  # EN + ZH recap output

    total_in = trans_in + recap_in
    total_out = trans_out + recap_out
    total_cost = (total_in / 1_000_000) * deepseek_input_price + (total_out / 1_000_000) * deepseek_output_price

    print(f"\n{'='*50}")
    print(f"  DeepSeek Token & Cost Estimate ({n} articles)")
    print(f"{'='*50}")
    print(f"  Translation:")
    print(f"    Input:  {trans_in:>10,} tokens")
    print(f"    Output: {trans_out:>10,} tokens")
    print(f"  Recaps (EN+ZH):")
    print(f"    Input:  {recap_in:>10,} tokens")
    print(f"    Output: {recap_out:>10,} tokens")
    print(f"  {'─'*40}")
    print(f"  Total tokens:  {total_in + total_out:>10,}")
    print(f"  Total cost:    ${total_cost:>10.4f}")
    print(f"  Per article:   ${total_cost/n:>10.4f}")
    print(f"{'='*50}\n")


if __name__ == "__main__":
    main()
