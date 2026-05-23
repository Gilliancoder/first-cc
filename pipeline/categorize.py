from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

CATEGORY_IDS = ["macroeconomics", "industry-focus", "special-topics", "uncategorized"]

PROMPT_TEMPLATE = """Classify this financial newsletter article into exactly one category.

Categories:
- macroeconomics: broad economic trends, monetary/fiscal policy, GDP, inflation, employment, interest rates, central banks, exchange rates
- industry-focus: specific sectors, companies, equity markets, M&A, IPOs, earnings, corporate strategy, industry analysis
- special-topics: geopolitics, technology deep dives, ESG, regulatory changes, structural themes (supply chains, demographics, energy transition)
- uncategorized: ONLY if the article genuinely does NOT fit any of the above three categories

Respond with ONLY the category ID (one word).

Title: {title}
Excerpt: {excerpt}
Category:"""


def run(articles: list[dict]) -> list[dict]:
    """Classify each article using DeepSeek."""
    if not DEEPSEEK_API_KEY:
        print("[categorize] DEEPSEEK_API_KEY not set — using keyword classification")
        return _keyword_classify(articles)

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    for article in articles:
        title = article.get("title", "")
        body = article.get("body", "")
        excerpt = body[:500] if body else ""

        resp = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            max_tokens=10,
            temperature=0,
            messages=[
                {"role": "user", "content": PROMPT_TEMPLATE.format(title=title, excerpt=excerpt)},
            ],
        )

        result = resp.choices[0].message.content.strip().lower()
        if result not in CATEGORY_IDS:
            result = _keyword_classify_one(article)

        article["category_id"] = result

    return articles


def _keyword_classify_one(article: dict) -> str:
    body = article.get("body", "").lower()
    title = article.get("title", "").lower()
    text = title + " " + body

    macro_kw = ["inflation", "fed", "central bank", "gdp", "monetary", "rate hike", "employment", "fx", "exchange rate", "cpi", "interest rate"]
    industry_kw = ["merger", "acquisition", "ipo", "stock", "equity", "earnings", "sector", "revenue", "market share", "valuation"]
    special_kw = ["geopolitic", "regulation", "supply chain", "climate", "esg", "reshoring", "energy transition", "technology"]

    macro_score = sum(1 for kw in macro_kw if kw in text)
    industry_score = sum(1 for kw in industry_kw if kw in text)
    special_score = sum(1 for kw in special_kw if kw in text)

    if macro_score >= industry_score and macro_score >= special_score and macro_score > 0:
        return "macroeconomics"
    elif industry_score >= macro_score and industry_score >= special_score and industry_score > 0:
        return "industry-focus"
    elif special_score > 0:
        return "special-topics"
    return "uncategorized"


def _keyword_classify(articles: list[dict]) -> list[dict]:
    for article in articles:
        article["category_id"] = _keyword_classify_one(article)
    return articles
