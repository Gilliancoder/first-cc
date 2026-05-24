import json
import os
import re
import sys
import base64
import requests
from datetime import date, datetime, timedelta, timezone

# Force UTF-8 output on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from auth_helper import (
    get_access_token,
    get_user_id,
    GRAPH_BASE_URL,
)
from config import DATA_DIR, PUBLIC_DATA_DIR

# --- Newsletter sender recognition ---
# Only process emails matching these sender names or domains.
NEWSLETTER_SENDERS = {
    "goldman sachs": "GS",
    "morgan stanley": "MS",
    "j.p. morgan": "JPM",
    "jpmorgan": "JPM",
    "barclays": "Barclays",
    "ubs": "UBS",
    "deutsche bank": "DB",
    "citigroup": "Citi",
    "citi": "Citi",
    "credit suisse": "CS",
    "hsbc": "HSBC",
    "nomura": "Nomura",
    "wsj": "WSJ",
    "wall street journal": "WSJ",
    "dow jones": "WSJ",
    "spencer": "SPEN",
    "mckinsey": "McKinsey",
    "blackrock": "BlackRock",
    "fidelity": "Fidelity",
    "vanguard": "Vanguard",
}

NEWSLETTER_DOMAINS = {
    "gs.com", "morganstanley.com", "jpmorgan.com", "jpmchase.com",
    "barclays.com", "ubs.com",
    "db.com", "citi.com", "credit-suisse.com", "hsbc.com",
    "nomura.com", "wsj.com", "dowjones.com",
}

# Skip subjects matching these (Microsoft security alerts, ads, etc.)
SKIP_SUBJECT_PATTERNS = [
    r"检测到.*登录", r"新登录", r"sign.in", r"password",
    r"security (code|alert|notification)",
]


def _detect_pdf_links(raw_html: str) -> list[str]:
    """Find PDF file URLs in HTML content."""
    pdf_urls = []

    # Pattern 1: href ending in .pdf
    href_matches = re.findall(r'href=["\']([^"\']+\.pdf)["\']', raw_html, re.IGNORECASE)
    pdf_urls.extend(href_matches)

    # Pattern 2: anchor text containing PDF indicators
    anchor_matches = re.findall(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        raw_html, re.IGNORECASE | re.DOTALL,
    )
    for href, anchor_text in anchor_matches:
        anchor_lower = re.sub(r"<[^>]+>", "", anchor_text).strip().lower()
        if any(kw in anchor_lower for kw in ["pdf", "download report", "full report", "download pdf"]):
            if href not in pdf_urls:
                pdf_urls.append(href)

    return pdf_urls


# Patterns to skip when following links from multi-topic emails
SKIP_LINK_PATTERNS = [
    r"youtube\.com", r"vimeo\.com", r"dailymotion\.com",
    r"/video", r"/videos", r"/blog", r"/podcast",
    r"/subscribe", r"/unsubscribe", r"/privacy", r"/terms",
    r"mailto:", r"javascript:",
]


def _extract_all_anchors(html: str) -> list[tuple[str, str]]:
    """Extract all (href, anchor_text) pairs from HTML."""
    return re.findall(
        r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
        html, re.IGNORECASE | re.DOTALL,
    )


def _clean_anchor_text(anchor_html: str) -> str:
    """Strip HTML tags from anchor text, normalize whitespace."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", anchor_html)).strip()


def _is_noise_link(href: str, anchor_text: str) -> bool:
    """Check if a link is noise (unsubscribe, video, blog, etc.)."""
    if not href or href.startswith("javascript:") or href.startswith("#"):
        return True
    full_url = href.lower()
    if any(re.search(p, full_url) for p in SKIP_LINK_PATTERNS):
        return True
    anchor_lower = anchor_text.lower()
    if any(kw in anchor_lower for kw in ["unsubscribe", "manage preferences",
                                           "privacy", "terms", "summer reading",
                                           "book list", "podcast"]):
        return True
    return False


def _is_garbled_text(text: str) -> bool:
    """Detect binary/garbled content in extracted text."""
    if not text:
        return True
    # More than 30% non-printable/symbol characters = garbled
    non_printable = sum(1 for c in text if c.isprintable() is False and c not in '\n\r\t')
    if len(text) > 0 and non_printable / max(len(text), 1) > 0.3:
        return True
    # Common mojibake patterns
    if re.search(r"[€‚ƒ„…†‡ˆ‰Š‹ŒŽ]", text):
        return True
    return False


def _extract_title_from_html(html: str) -> str:
    """Extract best available title from HTML page."""
    # Try <title> first
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if title_match:
        title = re.sub(r"\s+", " ", title_match.group(1).strip()).strip()
        if title and title.lower() != "untitled":
            return title[:200]
    # Try <h1>
    h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    if h1_match:
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h1_match.group(1))).strip()
        if title:
            return title[:200]
    # Try <h2>
    h2_match = re.search(r"<h2[^>]*>(.*?)</h2>", html, re.IGNORECASE | re.DOTALL)
    if h2_match:
        title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h2_match.group(1))).strip()
        if title:
            return title[:200]
    return ""


def _find_preceding_heading(html: str, href: str) -> str:
    """Try to find a heading element before a link to use as article title."""
    # Look for h1-h6 or strong text within 500 chars before the link
    idx = html.find(href)
    if idx < 0:
        return ""
    before = html[max(0, idx - 1000):idx]
    # Try h4-h6 first (common section headers in emails)
    for tag in ['h4', 'h5', 'h6', 'h3', 'h2', 'strong', 'b']:
        matches = list(re.finditer(rf"<{tag}[^>]*>(.*?)</{tag}>", before, re.IGNORECASE | re.DOTALL))
        if matches:
            text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", matches[-1].group(1))).strip()
            if text and len(text) > 3:
                return text[:150]
    return ""


def _sender_link_strategy(sender: str, html: str) -> list[dict]:
    """Return list of {'url': ..., 'title': ...} dicts per sender's link pattern."""
    anchors = _extract_all_anchors(html)
    results = []

    if sender == "Barclays":
        # Click each "more" link
        for href, anchor_html in anchors:
            anchor_text = _clean_anchor_text(anchor_html)
            if _is_noise_link(href, anchor_text):
                continue
            if re.search(r"\bmore\b", anchor_text, re.IGNORECASE) and len(anchor_text) < 80:
                heading = _find_preceding_heading(html, href)
                results.append({"url": href, "title": heading or anchor_text[:100]})

    elif sender == "MS":
        # Each "Read More" link
        for href, anchor_html in anchors:
            anchor_text = _clean_anchor_text(anchor_html)
            if _is_noise_link(href, anchor_text):
                continue
            if re.search(r"read\s+more", anchor_text, re.IGNORECASE):
                heading = _find_preceding_heading(html, href)
                results.append({"url": href, "title": heading or anchor_text[:100]})

    elif sender == "DB":
        # Links starting with "Read" in anchor text
        for href, anchor_html in anchors:
            anchor_text = _clean_anchor_text(anchor_html)
            if _is_noise_link(href, anchor_text):
                continue
            if re.match(r"^read\b", anchor_text, re.IGNORECASE):
                heading = _find_preceding_heading(html, href)
                results.append({"url": href, "title": heading or anchor_text[:100]})

    elif sender == "GS":
        # "read the full article" links → separate article
        for href, anchor_html in anchors:
            anchor_text = _clean_anchor_text(anchor_html)
            if _is_noise_link(href, anchor_text):
                continue
            if re.search(r"read\s+the\s+full\s+article", anchor_text, re.IGNORECASE):
                heading = _find_preceding_heading(html, href)
                results.append({"url": href, "title": heading or anchor_text[:100]})

    elif sender == "JPM":
        # Detail page links, skip summer reading/ads
        for href, anchor_html in anchors:
            anchor_text = _clean_anchor_text(anchor_html)
            if _is_noise_link(href, anchor_text):
                continue
            anchor_lower = anchor_text.lower()
            if any(kw in anchor_lower for kw in ["summer reading", "book list", "subscribe", "advertisement"]):
                continue
            if re.search(r"read\s+(more|full|the|article|report)|learn\s+more|view\s+(full|more)",
                         anchor_text, re.IGNORECASE):
                heading = _find_preceding_heading(html, href)
                results.append({"url": href, "title": heading or anchor_text[:100]})

    # Deduplicate by URL before returning
    seen = set()
    unique = []
    for r in results:
        if r["url"] not in seen:
            seen.add(r["url"])
            unique.append(r)
    return unique


def _follow_link_to_article(link_url: str, base_sender: str, base_date: str,
                            fallback_title: str = "") -> dict | None:
    """Fetch a linked article page and extract its content."""
    try:
        resp = requests.get(link_url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        if resp.status_code != 200:
            return None

        # Check content-type — skip PDFs (handled by PDF pipeline)
        content_type = resp.headers.get("content-type", "").lower()
        if "application/pdf" in content_type:
            return None

        html = resp.text

        # Extract best title
        title = _extract_title_from_html(html)
        if not title:
            title = fallback_title or "Untitled"
        if title.lower() == "untitled":
            return None  # Skip articles we can't identify

        # Remove scripts, styles, nav, footer, header
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<nav[^>]*>.*?</nav>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<footer[^>]*>.*?</footer>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<header[^>]*>.*?</header>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Get body text
        body_match = re.search(r"<body[^>]*>(.*?)</body>", html, re.DOTALL | re.IGNORECASE)
        body_html = body_match.group(1) if body_match else html

        body_text = _html_to_text(body_html, {})
        body_text = _strip_boilerplate(body_text)

        if _is_garbled_text(body_text) or len(body_text) < 200:
            return None

        return {
            "sender": base_sender,
            "title": title[:200],
            "body": body_text,
            "raw_html": body_html,
            "received_date": base_date,
        }
    except Exception as e:
        print(f"  [fetch] Failed to follow link {link_url}: {e}")
        return None


def _is_newsletter(sender_name: str, sender_email: str, subject: str) -> bool:
    for pattern in SKIP_SUBJECT_PATTERNS:
        if re.search(pattern, subject, re.IGNORECASE):
            return False
    name_lower = sender_name.lower().strip()
    for key in NEWSLETTER_SENDERS:
        if key in name_lower:
            return True
    email_match = re.search(r"@([\w.]+)", sender_email)
    if email_match:
        domain = email_match.group(1).lower()
        for d in NEWSLETTER_DOMAINS:
            if d in domain:
                return True
    return False


# --- Main entry point ---

def run(target_date: str, include_read: bool = False) -> list[dict]:
    token = get_access_token()
    user_id = get_user_id()
    headers = {"Authorization": f"Bearer {token}"}

    days_back = 7 if include_read else 2
    lookback = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    url = f"{GRAPH_BASE_URL}/users/{user_id}/mailFolders/inbox/messages"
    filter_parts = [f"receivedDateTime ge {lookback}"]
    if not include_read:
        filter_parts.append("isRead eq false")
    params = {
        "$filter": " and ".join(filter_parts),
        "$select": "id,subject,from,receivedDateTime,hasAttachments",
        "$top": 50,
    }
    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        print(f"[fetch] Graph API error: {resp.status_code} {resp.text}")
        return []

    messages = resp.json().get("value", [])
    label = "messages" if include_read else "unread message(s)"
    print(f"[fetch] Found {len(messages)} {label}")

    articles = []
    seen_msg_ids = set()  # Prevent duplicate emails
    for msg in messages:
        msg_id = msg["id"]
        if msg_id in seen_msg_ids:
            continue
        seen_msg_ids.add(msg_id)
        raw_subject = msg.get("subject", "")
        subject = _clean_subject(raw_subject)

        sender_info = msg.get("from", {}).get("emailAddress", {})
        sender_email = sender_info.get("address", "")
        sender_name = sender_info.get("name", sender_email)

        if not _is_newsletter(sender_name, sender_email, raw_subject):
            print(f"  [fetch] Skip non-newsletter: '{subject}' from {sender_name}")
            _mark_as_read(user_id, msg_id, headers)
            continue

        sender = _extract_sender_abbr(sender_name, sender_email)
        received_date = msg.get("receivedDateTime", "")[:10] or target_date

        body_text, images, raw_html = _get_full_message(user_id, msg_id, token, target_date)
        body_text = body_text.strip()

        if len(body_text) < 200:
            print(f"  [fetch] Skip '{subject}' — too short ({len(body_text)} chars)")
            _mark_as_read(user_id, msg_id, headers)
            continue

        article = {
            "sender": sender,
            "title": subject,
            "body": body_text,
            "received_date": received_date,
        }
        if images:
            article["images"] = images
        if raw_html:
            article["raw_html"] = raw_html

        # Check for PDF links in the email
        if raw_html:
            pdf_links = _detect_pdf_links(raw_html)
            if pdf_links:
                article["pdf_links"] = pdf_links

        articles.append(article)
        print(f"  [fetch] [{sender}] {subject} "
              f"({len(body_text.split())} words, {len(images)} images)")

        _mark_as_read(user_id, msg_id, headers)

    # Sender-aware link expansion: each sender has different link patterns
    expanded = []
    seen_urls = set()  # Track all expanded URLs to prevent duplicates
    for article in articles:
        raw_html = article.get("raw_html", "")
        sender = article.get("sender", "")
        if raw_html and sender:
            links = _sender_link_strategy(sender, raw_html)
            pdf_links = article.get("pdf_links", [])
            # Merge PDF links, skipping already-seen URLs
            for pl in pdf_links:
                if pl not in [l["url"] for l in links] and pl not in seen_urls:
                    links.append({"url": pl, "title": ""})
            # Filter out already-seen URLs
            new_links = [l for l in links if l["url"] not in seen_urls]
            if new_links:
                print(f"  [fetch] [{sender}] Expanding {len(new_links)} link(s) "
                      f"from '{article['title']}'")
                for link_info in new_links[:10]:
                    seen_urls.add(link_info["url"])
                    sub = _follow_link_to_article(
                        link_info["url"], sender, article["received_date"],
                        fallback_title=link_info.get("title", ""),
                    )
                    if sub:
                        # Skip if we already have an article with the same sender+title
                        dup_key = (sub["sender"], sub["title"])
                        existing_keys = {(a["sender"], a["title"]) for a in expanded}
                        existing_keys.update((a["sender"], a["title"]) for a in articles)
                        if dup_key not in existing_keys:
                            expanded.append(sub)
    articles = expanded

    _cache_raw_articles(articles, target_date)
    return articles


# --- Message body extraction ---

def _get_full_message(
    user_id: str, msg_id: str, token: str, target_date: str
) -> tuple[str, list[str], str]:
    """Returns (body_text, images, raw_html). raw_html is the original HTML body."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"{GRAPH_BASE_URL}/users/{user_id}/messages/{msg_id}"
    resp = requests.get(url, headers=headers, params={"$expand": "attachments"})
    if resp.status_code != 200:
        return "", [], ""

    msg = resp.json()
    images = []
    cid_map = {}

    # Collect inline image attachments → CID map
    for att in msg.get("attachments", []):
        name = att.get("name", "")
        content_id = att.get("contentId", "")
        if att.get("@odata.type") == "#microsoft.graph.fileAttachment":
            b64 = att.get("contentBytes", "")
            if b64 and _is_image_filename(name):
                try:
                    img_bytes = base64.b64decode(b64)
                    img_path = _save_inline_image(img_bytes, name, target_date)
                    if img_path:
                        images.append(img_path)
                        if content_id:
                            cid_map[content_id] = img_path
                except Exception:
                    pass

    body = msg.get("body", {})
    raw_html = body.get("content", "")

    if body.get("contentType") == "html":
        body_text = _html_to_text(raw_html, cid_map)
    else:
        body_text = raw_html

    body_text = _strip_boilerplate(body_text)
    return body_text, images, raw_html


# --- HTML → clean paragraph text ---

def _html_to_text(html: str, cid_map: dict) -> str:
    # Remove invisible / zero-width characters
    text = re.sub(r"[​‌‍‎‏­   ]", "", html)

    # Remove style/script blocks entirely
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)

    # Normalize consecutive <br> to paragraph breaks
    text = re.sub(r"(?:<br\s*/?>\s*){2,}", "\n\n", text, flags=re.IGNORECASE)
    # Single <br> → newline
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    # Opening tags
    text = re.sub(r"<(?:p|div|h\d|header|li)[^>]*>", "\n", text, flags=re.IGNORECASE)
    # Closing block tags → double newline (paragraph break)
    text = re.sub(r"</(?:p|div|h\d|header)[^>]*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<(?:hr\s*/?>)", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</?(?:tr|table|tbody|thead|tfoot)[^>]*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li[^>]*>", "\n", text, flags=re.IGNORECASE)

    # Replace <img> with [IMG:…] markers
    def _img_repl(m):
        src = m.group(1) or ""
        alt = m.group(2) or ""
        cid_m = re.search(r"cid:([^\"]+)", src)
        if cid_m and cid_m.group(1) in cid_map:
            return f"\n[IMG:{cid_map[cid_m.group(1)]}]\n"
        if alt.strip():
            return f"\n[IMG: {alt.strip()}]\n"
        return ""

    text = re.sub(
        r"<img[^>]+src=\"([^\"]+)\"[^>]*(?:alt=\"([^\"]*)\")?[^>]*/?>",
        _img_repl, text, flags=re.IGNORECASE,
    )

    # Strip remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    import html as html_mod
    text = html_mod.unescape(text)

    # Whitespace normalization
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n[ \t]+\n", "\n\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^\n+", "", text)

    return text.strip()


# --- Boilerplate removal ---

def _strip_boilerplate(text: str) -> str:
    """Strip email footers, legal disclaimers, UI prompts, etc."""
    patterns = [
        r"Want to sign up and stay\s+connected\?\s*Click\s*here\.?",
        r"Not yet a subscriber\?\s*Sign Up\b[^.]*\.?",
        r"Sign Up Here\s*›?\s*",
        r"Share this email with a friend\.?\s*",
        r"Forwarded this email by a friend\?\s*",
        r"Forward\s*›\s*",
        r"Access WSJ\.com[^.]*\.?\s*",
        r"Click here to [Uu]nsubscribe[^.]*\.?\s*",
        r"Unsubscribe\b",
        r"Is this email difficult to read\?\s*",
        r"View (it )?in (a |your )?(web )?browser[^.]*\s*›?\s*",
        r"©\s*\d{4}\s+[^.]*All rights reserved\.?",
        r"Copyright[—\s]?\d{4}\s+[^.]*(All Rights Reserved|Dow Jones)[^.]*\.?",
        r"This email was (written|sent) by:[^.]*\.?\s*",
        r"Please do not reply to this email[^.]*\.?\s*",
        r"This message is subject to important terms and conditions[^.]*\.?\s*",
        r"Visit our [^.]* for a compilation of prior publications\.?\s*",
        r"for internal or external use\.?\s*",
        r"For further assistance,?\s*please contact[^.]*\.?\s*",
        r"You are currently subscribed as[^.]*\.?\s*",
        r"Dow Jones & Company, Inc\. [^.]*\.?",
        r"Barclays Bank PLC UK[^.]*\.?",
        r"Registered office:[^.]*\.?\s*",
        r"\bPID:\s*\d+\b",
        r"\[?PID:?\s*\d+\]?",
        r"CONTENT FROM:\s*[^\n]*\n?",
        r"Sponsored by\s*[^\n]*\n?",
        r"Play Podcast\s*",
        r"Manage Cookies\s*\|\s*Manage Re-targeting Consent\s*",
        r"(Privacy notice|Cookie Policy|Disclosures)\s*\|\s*[^\n]*\n?",
        r"please contact Customer Service at[^.]*\.?\s*",
        r"for more information about our privacy[^.]*\.?\s*",
        r"To stop receiving[^.]*\.?\s*",
        r"To the extent this newsletter includes[^.]*\.?\s*",
        # WSJ-specific email footer/boilerplate
        r"Markets P\.M\. catches you up[^.]*\.?\s*",
        r"About Us\s*",
        r"Subscribe\s*",
        r"\S+\s*\|\s*\S+.*?\|\s*.*?(Contact Us|All Rights Reserved).*",
        r"S\. Route 1 North Monmouth Junction[^.]*\.?\s*",
        r"\S+com\. com or 1-800-JOURNAL[^.]*\.?\s*",
        r"Markets at a Glance\s*",
        r"Read More\s*",
        r"\.\s*›\s*",
    ]

    for pat in patterns:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)

    # Remove empty / whitespace-only lines
    lines = [l.rstrip() for l in text.split("\n")]
    lines = [l for l in lines if l.strip()]
    text = "\n".join(lines)

    return text.strip()


# --- Helpers ---

def _is_image_filename(name: str) -> bool:
    return bool(re.search(r"\.(png|jpe?g|gif|webp|svg|bmp|tiff?)$", name, re.IGNORECASE))


def _save_inline_image(img_bytes: bytes, filename: str, target_date: str) -> str | None:
    try:
        images_dir = os.path.join(PUBLIC_DATA_DIR, "images", target_date)
        os.makedirs(images_dir, exist_ok=True)
        safe_name = re.sub(r"[^\w\-.]", "_", filename)[:60]
        img_path = os.path.join(images_dir, safe_name)
        if os.path.exists(img_path):
            base, ext = os.path.splitext(safe_name)
            img_path = os.path.join(images_dir, f"{base}_{hash(img_bytes) & 0xffff}{ext}")
        with open(img_path, "wb") as f:
            f.write(img_bytes)
        return f"data/images/{target_date}/{os.path.basename(img_path)}"
    except Exception as e:
        print(f"  [fetch] Failed to save inline image: {e}")
        return None


def _mark_as_read(user_id: str, msg_id: str, headers: dict):
    url = f"{GRAPH_BASE_URL}/users/{user_id}/messages/{msg_id}"
    requests.patch(url, headers=headers, json={"isRead": True})


def _clean_subject(subject: str) -> str:
    subject = re.sub(r"^(RE|FW|Fwd|Re):\s*", "", subject, flags=re.IGNORECASE)
    subject = re.sub(r"\s*\[.*?\]\s*$", "", subject).strip()
    return subject


def _extract_sender_abbr(name: str, email: str = "") -> str:
    name_lower = name.lower().strip()
    for key, abbr in NEWSLETTER_SENDERS.items():
        if key in name_lower:
            return abbr
    target = email or name
    email_match = re.search(r"@([\w.]+)", target)
    if email_match:
        domain = email_match.group(1).lower()
        for d in NEWSLETTER_DOMAINS:
            if d in domain:
                return name[:4].upper()
    clean = re.sub(r"[<>\"]", "", name).strip()
    return clean[:4].upper()


def _cache_raw_articles(articles: list[dict], target_date: str):
    cache_dir = os.path.join(DATA_DIR, ".cache")
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, f"raw_{target_date}.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(articles, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    arts = run(str(date.today()))
    print(f"\nFetched {len(arts)} articles")
    for a in arts:
        print(f"  [{a['sender']}] {a['title']}")
