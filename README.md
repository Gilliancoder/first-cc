# Daily Market Sense

A bilingual financial newsletter reader PWA. Fetches newsletters from Outlook, uses Claude AI for Chinese translation and English recaps, categorizes articles, and displays them in daily/weekly views.

## Architecture

```
Outlook (MS Graph) → Python Pipeline → data/*.json → Next.js PWA
                         │
                    Claude API (Haiku + Sonnet)
```

- **Frontend**: Next.js (App Router) + TypeScript + Tailwind CSS → static export PWA
- **Pipeline**: Python scripts with Anthropic SDK + Microsoft Graph API
- **AI**: Claude Haiku for translation, Claude Sonnet for recap generation

## Quick Start

### Prerequisites

- Node.js 18+
- Python 3.11+
- Microsoft Graph API credentials (for Outlook integration)
- Anthropic API key (for translation and recaps)

### 1. Install Dependencies

```bash
npm install
pip install -r pipeline/requirements.txt
```

### 2. Configure Environment

Create a `.env` file or set environment variables:

```bash
ANTHROPIC_API_KEY=sk-ant-...
MS_GRAPH_CLIENT_ID=...
MS_GRAPH_CLIENT_SECRET=...
MS_GRAPH_TENANT_ID=...
MS_GRAPH_USER_ID=...
```

### 3. Run the Pipeline

```bash
# Process today's emails
python pipeline/pipeline.py

# Process a specific date
python pipeline/pipeline.py --date 2026-05-23

# Estimate token usage first
python pipeline/pipeline.py --dry-run

# Skip email fetch (use cache for testing)
python pipeline/pipeline.py --skip-fetch
```

### 4. Start the App

```bash
npm run dev
```

Open http://localhost:3000

### 5. Build for Production

```bash
npm run build
# Output: out/ directory (fully static)
```

Deploy `out/` to any static hosting (Vercel, Netlify, GitHub Pages).

## Project Structure

```
├── app/                    # Next.js pages
│   ├── daily/[date]/       # Daily reading view
│   ├── weekly/[week]/      # Weekly reading view
│   ├── article/[id]/       # Article detail (bilingual + recap)
│   ├── archive/            # Date/week browser
│   └── offline/            # Offline fallback page
├── components/             # React components
├── lib/                    # Shared logic (types, data, dates)
├── hooks/                  # Custom React hooks
├── pipeline/               # Python content pipeline
│   ├── pipeline.py         # Main orchestrator
│   ├── fetch_emails.py     # MS Graph API
│   ├── translate.py        # Haiku translation
│   ├── recap.py            # Sonnet summarization
│   ├── categorize.py       # Article classification
│   └── fill_articles.py    # WSJ fallback
├── data/                   # Generated JSON content
└── public/                 # Static assets + PWA manifest + sw.js
```

## Pipeline Scheduling

### GitHub Actions (recommended)

Set up repository secrets and use the workflow at `.github/workflows/pipeline.yml`:

```yaml
# Runs Mon-Fri at 12:00 UTC
schedule:
  - cron: '0 12 * * 1-5'
```

### Manual Cron

```bash
# Run every weekday at 7 AM
crontab -e
0 7 * * 1-5 cd /path/to/first-cc && python pipeline/pipeline.py && npm run build
```

## Key Features

- **Bilingual reading**: English paragraphs followed by Chinese translations
- **AI recaps**: 2-3 sentence summaries optimized for interview recall
- **Content categories**: Macroeconomics, Industry Focus, Special Topics
- **WSJ fallback**: Automatically fills empty categories
- **Daily + Weekly views**: Toggle between daily and weekly reading modes
- **PWA**: Installable on iOS/Android home screen, works offline
- **Dark mode**: Auto-detected from system preference
