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
    "bank of america": "BofA",
    "bofa global research": "BofA",
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
    "bofa.com", "bankofamerica.com", "barclays.com", "ubs.com",
    "db.com", "citi.com", "credit-suisse.com", "hsbc.com",
    "nomura.com", "wsj.com", "dowjones.com",
}

# Skip subjects matching these (Microsoft security alerts, ads, etc.)
SKIP_SUBJECT_PATTERNS = [
    r"检测到.*登录", r"新登录", r"sign.in", r"password",
    r"security (code|alert|notification)",
]


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
    for msg in messages:
        msg_id = msg["id"]
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

        articles.append(article)
        print(f"  [fetch] [{sender}] {subject} "
              f"({len(body_text.split())} words, {len(images)} images)")

        _mark_as_read(user_id, msg_id, headers)

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
