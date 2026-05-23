"""
Email HTML → section screenshots using Playwright.

For each email, renders the HTML body in a headless browser, detects
visual content sections, screenshots each section, and extracts the
text for bilingual translation.
"""

import asyncio
import base64
import json
import os
import re
from playwright.async_api import async_playwright

from config import PUBLIC_DATA_DIR
from utils import slugify

SCREENSHOT_WIDTH = 640


def run(articles: list[dict], target_date: str) -> list[dict]:
    """Take section screenshots for each article that has raw_html."""
    if not any(a.get("raw_html") for a in articles):
        print("[screenshot] No raw HTML in articles — skipping")
        return articles
    return asyncio.run(_screenshot_async(articles, target_date))


async def _screenshot_async(articles: list[dict], target_date: str) -> list[dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        semaphore = asyncio.Semaphore(3)

        async def process_one(article: dict) -> dict:
            async with semaphore:
                raw_html = article.get("raw_html", "")
                if not raw_html:
                    return article

                out_dir = _screenshot_dir(article, target_date)
                os.makedirs(out_dir, exist_ok=True)

                sections = await _capture_sections(
                    browser, raw_html, out_dir, article
                )
                if sections:
                    article["sections"] = sections
                    # Build flat body text from sections for downstream translation
                    article["body"] = "\n\n".join(
                        s["en"] for s in sections if s["en"].strip()
                    )
                return article

        tasks = [process_one(a) for a in articles]
        results = await asyncio.gather(*tasks)
        await browser.close()
        return list(results)


async def _capture_sections(
    browser, raw_html: str, out_dir: str, article: dict
) -> list[dict]:
    """Render email, detect sections via headings/breaks, screenshot each."""
    page = await browser.new_page(
        viewport={"width": SCREENSHOT_WIDTH, "height": 600}
    )

    full_html = _build_render_html(raw_html, article)

    try:
        await page.set_content(full_html, wait_until="networkidle", timeout=15000)
    except Exception:
        await page.set_content(full_html, wait_until="load", timeout=10000)

    # Mark all block-level elements with an index for later screenshotting
    element_count = await page.evaluate("""() => {
        // Find content-bearing block elements, skipping tiny/nested ones
        const candidates = document.querySelectorAll(
            'table > tbody > tr > td > table, ' +
            'div[class*="article"], div[class*="content"], div[class*="section"], ' +
            'div[class*="text"], div[class*="body"], ' +
            'td[class*="text"], td[class*="body"], td[class*="content"]'
        );

        // If no good candidates, use top-level tables or body children
        let elements;
        if (candidates.length >= 2) {
            elements = Array.from(candidates);
        } else {
            const tables = document.querySelectorAll('table');
            if (tables.length >= 2) {
                elements = Array.from(tables).filter(t => {
                    const text = (t.innerText || '').trim();
                    return text.length > 50;
                });
            } else {
                elements = Array.from(document.body.children).filter(el => {
                    const text = (el.innerText || '').trim();
                    return text.length > 40;
                });
            }
        }

        // Deduplicate by text content
        const seen = new Set();
        const unique = [];
        for (const el of elements) {
            const text = (el.innerText || '').trim().substring(0, 200);
            if (text.length < 30) continue;
            if (seen.has(text)) continue;
            seen.add(text);
            el.setAttribute('data-section-idx', unique.length);
            unique.push(el);
        }

        // Limit to prevent too many screenshots
        return Math.min(unique.length, 12);
    }""")

    result = []
    for i in range(element_count):
        try:
            # Get the element by its data attribute
            el_handle = await page.query_selector(f"[data-section-idx='{i}']")
            if not el_handle:
                continue

            # Get text content
            text = await el_handle.inner_text()
            text = text.strip()
            if len(text) < 30:
                continue

            # Screenshot just this element
            screenshot_path = os.path.join(out_dir, f"section-{i + 1:02d}.png")
            await el_handle.screenshot(path=screenshot_path)

            rel_path = os.path.relpath(
                screenshot_path,
                os.path.join(PUBLIC_DATA_DIR, os.pardir),
            ).replace("\\", "/")

            result.append({
                "screenshot": rel_path,
                "en": text,
            })
        except Exception as e:
            print(f"  [screenshot] Section {i} failed: {e}")

    await page.close()

    # Fallback: full-page screenshot if no sections found
    if not result:
        fallback_path = os.path.join(out_dir, "full.png")
        page2 = await browser.new_page(
            viewport={"width": SCREENSHOT_WIDTH, "height": 600}
        )
        try:
            await page2.set_content(full_html, wait_until="load", timeout=10000)
        except Exception:
            await page2.close()
            return []
        await page2.screenshot(path=fallback_path, full_page=True)
        await page2.close()
        rel_path = os.path.relpath(
            fallback_path,
            os.path.join(PUBLIC_DATA_DIR, os.pardir),
        ).replace("\\", "/")
        result.append({
            "screenshot": rel_path,
            "en": article.get("body", ""),
        })

    return result


def _screenshot_dir(article: dict, target_date: str) -> str:
    """Get the screenshot output directory for an article."""
    slug = slugify(article.get("sender", ""), article.get("title", ""))
    return os.path.join(PUBLIC_DATA_DIR, "screenshots", target_date, slug)


def _build_render_html(raw_html: str, article: dict) -> str:
    """Build a self-contained HTML document from raw email body."""
    # Replace cid: image references with local paths
    images = article.get("images", [])
    html = raw_html

    # Try to fix cid: references with local image paths
    for img_path in images:
        basename = os.path.basename(img_path)
        # cid references are hard to match perfectly; try common patterns
        html = re.sub(
            r'cid:([^"\']*' + re.escape(basename) + r'[^"\']*)',
            "/" + img_path,
            html,
            flags=re.IGNORECASE,
        )

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={SCREENSHOT_WIDTH}">
<style>
  body {{
    margin: 0;
    padding: 16px;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    font-size: 15px;
    line-height: 1.6;
    color: #1a1a1a;
    background: #ffffff;
    max-width: {SCREENSHOT_WIDTH}px;
    word-wrap: break-word;
  }}
  img {{ max-width: 100%; height: auto; }}
  a {{ color: #2563eb; }}
  table {{ max-width: 100%; }}
</style>
</head>
<body>{html}</body>
</html>"""


if __name__ == "__main__":
    # Test: render cached articles
    import sys

    cache_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data", ".cache", "raw_test.json",
    )
    if os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            test_articles = json.load(f)
        print(f"Testing with {len(test_articles)} articles...")
        results = run(test_articles, "2026-05-23")
        for a in results:
            sections = a.get("sections", [])
            print(f"  [{a.get('sender', '')}] {len(sections)} sections")
            for s in sections:
                print(f"    {s['screenshot']}: {len(s['en'])} chars")
    else:
        print(f"No test cache at {cache_path}")
