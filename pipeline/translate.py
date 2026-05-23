import asyncio
from openai import AsyncOpenAI
from utils import split_paragraphs
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

TRANSLATE_PROMPT = """Translate the following financial English paragraph to Simplified Chinese.
Maintain financial terminology accuracy. Use natural Chinese financial writing style.
CRITICAL: Preserve all line breaks exactly as they appear in the source text.
Each visual line in the English text corresponds to a separate line in the screenshot —
keep the same number of lines and the same paragraph structure in the Chinese output.
Do not merge lines together. Match the formatting of the original.
Do not add commentary or interpretation. Output only the Chinese translation.

English: {paragraph}
Chinese:"""


def run(articles: list[dict]) -> list[dict]:
    """Translate each paragraph of each article from English to Chinese using DeepSeek."""
    if not DEEPSEEK_API_KEY:
        print("[translate] DEEPSEEK_API_KEY not set — skipping translation")
        for article in articles:
            body = article.get("body", "")
            article["paragraphs"] = [{"en": body, "zh": "[Translation requires API key]"}]
        return articles

    return asyncio.run(_translate_async(articles))


async def _translate_async(articles: list[dict]) -> list[dict]:
    client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)
    semaphore = asyncio.Semaphore(10)

    async def translate_paragraph(para: str) -> str:
        async with semaphore:
            resp = await client.chat.completions.create(
                model=DEEPSEEK_MODEL,
                max_tokens=1500,
                temperature=0.1,
                messages=[
                    {"role": "user", "content": TRANSLATE_PROMPT.format(paragraph=para)},
                ],
            )
            return resp.choices[0].message.content.strip()

    for article in articles:
        # If article has screenshot sections, translate per-section
        sections = article.get("sections", [])
        if sections:
            en_texts = [s["en"] for s in sections if s["en"].strip()]
            if en_texts:
                zh_results = await asyncio.gather(
                    *[translate_paragraph(t) for t in en_texts]
                )
                for i, s in enumerate(sections):
                    if i < len(zh_results):
                        s["zh"] = zh_results[i]
            # Also set legacy paragraphs for backward compatibility
            article["paragraphs"] = [
                {"en": s["en"], "zh": s.get("zh", "")} for s in sections
            ]
            continue

        # Legacy: split body into paragraphs and translate
        body = article.get("body", "")
        en_paras = split_paragraphs(body)
        if not en_paras:
            article["paragraphs"] = [{"en": body, "zh": ""}]
            continue

        tasks = [translate_paragraph(p) for p in en_paras]
        zh_paras = await asyncio.gather(*tasks)

        article["paragraphs"] = [
            {"en": en, "zh": zh} for en, zh in zip(en_paras, zh_paras)
        ]

    return articles
