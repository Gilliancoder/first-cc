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
from pdf_screenshot import download_and_render_pdf

SCREENSHOT_WIDTH = 640

# Text patterns that indicate email chrome (headers, footers, system prompts)
SECTION_BLACKLIST = [
    r"difficult to read",
    r"view (it )?in (a |your )?(web )?browser",
    r"unsubscribe",
    r"click here to (unsubscribe|opt out|manage)",
    r"(email|subscription) preferences",
    r"privacy (notice|policy|statement)",
    r"cookie (policy|notice|settings)",
    r"all rights reserved",
    r"please do not reply",
    r"this (email|message) (was|is) (sent|approved|subject)",
    r"forward(ed)? this email",
    r"\bPID:\s*\d+",
    r"sponsored by",
    r"manage (your )?(cookies|re-targeting)",
    r"customer service at",
    r"to stop receiving",
    r"registered office:",
    r"©\s*\d{4}",
    # Methodology / disclosures / legal sections
    r"\bmethodology\b",
    r"\bdisclosures?\b",
    r"\bdisclaimer\b",
    r"important (legal|regulatory) (notice|information)",
    r"conflict of interest",
    r"analyst certification",
    r"general disclosure",
    # Author bio / column intro
    r"\babout the author\b",
    r"\bwritten by\b",
    r"\bcontributor\b",
    r"\bmeet the (author|team|analyst)",
    r"\bget in touch\b",
    r"\bcontact (us|the author)",
    r"\bfollow (us|me|the author) on",
    # Ads / promotions
    r"\bsummer reading\b",
    r"\bbook list\b",
    r"\bpodcast\b",
    r"\bwatch (the |our )?video\b",
]


def _is_blacklisted_text(text: str) -> bool:
    """Return True if text matches email chrome patterns, not content."""
    text_lower = text.lower()
    for pattern in SECTION_BLACKLIST:
        if re.search(pattern, text_lower):
            return True
    return False


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
                pdf_links = article.get("pdf_links", [])
                if pdf_links:
                    slug = slugify(article.get("sender", ""), article.get("title", ""))
                    out_dir = _screenshot_dir(article, target_date)
                    os.makedirs(out_dir, exist_ok=True)

                    all_sections = []
                    for pdf_url in pdf_links[:3]:
                        sections = download_and_render_pdf(pdf_url, slug, target_date)
                        all_sections.extend(sections)
                    if all_sections:
                        article["sections"] = all_sections
                        article["body"] = "\n\n".join(
                            s["en"] for s in all_sections if s["en"].strip()
                        )
                    return article

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

    # Mark individual content elements for per-paragraph screenshotting
    element_count = await page.evaluate("""() => {
        // Find individual block-level content elements (paragraphs, list items, cells)
        const candidates = document.querySelectorAll(
            'p, li, h4, h5, h6, ' +
            'div[class*="paragraph"], div[class*="text-block"], div[class*="body-text"], ' +
            'td[class*="text"], td[class*="body"], td[class*="content"], ' +
            'div[class*="article"], div[class*="content"], div[class*="section"]'
        );

        // If very few candidates, fall back to larger containers
        let elements;
        if (candidates.length >= 3) {
            elements = Array.from(candidates);
        } else {
            const tables = document.querySelectorAll('table > tbody > tr > td > table');
            if (tables.length >= 2) {
                elements = Array.from(tables).filter(t => {
                    return (t.innerText || '').trim().length > 30;
                });
            } else {
                elements = Array.from(document.body.children).filter(el => {
                    return (el.innerText || '').trim().length > 25;
                });
            }
        }

        // Filter and deduplicate
        const seen = new Set();
        const unique = [];
        for (const el of elements) {
            // Skip heading elements (title is in article title already)
            const tagName = el.tagName.toLowerCase();
            if (['h1','h2','h3'].includes(tagName)) continue;

            // Skip elements with header/footer/watermark/avatar class names
            const className = (el.className || '').toString().toLowerCase();
            if (/\\b(title|header|banner|watermark|footer|disclaimer|legal|logo|branding|masthead|avatar|portrait|headshot|profile-pic|author-photo|methodology|disclosures)\\b/.test(className)) continue;

            // Skip elements that are children of <thead>
            if (el.closest('thead')) continue;

            // Skip elements with role="banner" or role="contentinfo" (footer)
            const role = (el.getAttribute('role') || '').toLowerCase();
            if (role === 'banner' || role === 'contentinfo') continue;

            // Skip elements with large font (likely titles/headers)
            try {
                const computed = window.getComputedStyle(el);
                const fontSize = parseFloat(computed.fontSize);
                if (fontSize > 22) continue;
            } catch(e) {}

            const text = (el.innerText || '').trim().substring(0, 200);
            if (text.length < 15) continue;
            if (seen.has(text)) continue;
            seen.add(text);
            el.setAttribute('data-section-idx', unique.length);
            unique.push(el);
        }

        return unique.length;
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
            if len(text) < 15:
                continue
            if _is_blacklisted_text(text):
                continue

            # Skip chart-only sections: mostly images with minimal text
            img_count = await el_handle.evaluate(
                "el => el.querySelectorAll('img').length"
            )
            if img_count >= 1 and len(text) < 50:
                continue  # Chart/logo already in prior section screenshot

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

    # WSJ emails: drop last 2 sections (usually author bio + column intro)
    sender = article.get("sender", "")
    if sender == "WSJ" and len(result) >= 4:
        result = result[:-2]

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
