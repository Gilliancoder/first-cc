"""
PDF → section screenshot conversion using PyMuPDF.
Downloads a PDF from a URL and renders each page as a PNG image.
"""

import os
import re
import requests
import fitz  # PyMuPDF

from config import PUBLIC_DATA_DIR

# Text patterns that indicate non-content PDF pages (disclosures, author bios, etc.)
_PDF_PAGE_BLACKLIST = [
    r"\bdisclosures?\b",
    r"\bdisclaimer\b",
    r"\bimportant (legal|regulatory) (notice|information)",
    r"\bconflict of interest",
    r"\banalyst certification",
    r"\bgeneral disclosure",
    r"\babout the author\b",
    r"\bcontributors?\b",
    r"\bwritten by\b",
    r"\bcontact (us|the author)",
    r"all rights reserved",
    r"\bcopyright\b",
    r"©\s*\d{4}",
]


def download_and_render_pdf(pdf_url: str, slug: str, target_date: str) -> list[dict]:
    """Download a PDF and render each page as a screenshot. Returns section list."""
    try:
        resp = requests.get(pdf_url, timeout=30)
        if resp.status_code != 200:
            print(f"  [pdf] Failed to download {pdf_url}: {resp.status_code}")
            return []
    except Exception as e:
        print(f"  [pdf] Download error {pdf_url}: {e}")
        return []

    pdf_bytes = resp.content
    if len(pdf_bytes) < 1000:
        print(f"  [pdf] PDF too small from {pdf_url}")
        return []

    out_dir = os.path.join(PUBLIC_DATA_DIR, "screenshots", target_date, slug)
    os.makedirs(out_dir, exist_ok=True)

    sections = []
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page_num in range(min(len(doc), 20)):
            page = doc[page_num]
            text = page.get_text().strip()
            if not text:
                continue

            # Skip blacklisted pages (disclosures, author bios, etc.)
            text_lower = text.lower()
            if any(re.search(pattern, text_lower) for pattern in _PDF_PAGE_BLACKLIST):
                continue

            pix = page.get_pixmap(dpi=200)
            img_path = os.path.join(out_dir, f"pdf-page-{page_num + 1:02d}.png")
            pix.save(img_path)

            rel_path = os.path.relpath(
                img_path, os.path.join(PUBLIC_DATA_DIR, os.pardir)
            ).replace("\\", "/")

            sections.append({
                "screenshot": rel_path,
                "en": text,
            })
        doc.close()
    except Exception as e:
        print(f"  [pdf] Error rendering PDF: {e}")
        return []

    print(f"  [pdf] Rendered {len(sections)} pages from {pdf_url}")
    return sections
