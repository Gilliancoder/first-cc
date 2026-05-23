from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL

RECAP_EN_PROMPT = """You are a professional financial analyst preparing a colleague for an interview.
Read this article and write a 2-3 sentence English recap capturing:
- The core thesis or key finding
- Important data points or arguments
- Investment or market implications (if applicable)

Write in clear, concise English suitable for verbal recall in an interview setting. Be specific — name companies, numbers, and dates where relevant.

Title: {title}
Sender: {sender}
Content:
{content}

Recap (2-3 sentences in English):"""

RECAP_ZH_PROMPT = """你是一名专业金融分析师，正在帮助同事准备面试。
阅读以下文章，写一个2-3句话的中文摘要，涵盖：
- 核心论点或关键发现
- 重要数据点或论据
- 投资或市场影响（如适用）

用清晰简洁的中文撰写，适合在面试中口头复述。要具体——在相关处提及公司名称、数字和日期。

标题：{title}
来源：{sender}
内容：
{content}

中文摘要（2-3句话）："""


def run(articles: list[dict]) -> list[dict]:
    """Generate bilingual (EN + ZH) recaps using DeepSeek."""
    if not DEEPSEEK_API_KEY:
        print("[recap] DEEPSEEK_API_KEY not set — generating placeholder recaps")
        for article in articles:
            title = article.get("title", "")
            sender = article.get("sender", "")
            article["recap_en"] = f"{sender}: {title}. [Recap requires API key.]"
            article["recap_zh"] = f"{sender}：{title}。[摘要需要API密钥。]"
        return articles

    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

    for article in articles:
        title = article.get("title", "")
        sender = article.get("sender", "")
        body = article.get("body", "")

        words = body.split()
        truncated = " ".join(words[:3000])

        # English recap
        resp_en = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            max_tokens=300,
            temperature=0.2,
            messages=[
                {"role": "user", "content": RECAP_EN_PROMPT.format(
                    title=title, sender=sender, content=truncated)},
            ],
        )
        article["recap_en"] = resp_en.choices[0].message.content.strip()

        # Chinese recap
        resp_zh = client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            max_tokens=400,
            temperature=0.2,
            messages=[
                {"role": "user", "content": RECAP_ZH_PROMPT.format(
                    title=title, sender=sender, content=truncated)},
            ],
        )
        article["recap_zh"] = resp_zh.choices[0].message.content.strip()

    return articles
