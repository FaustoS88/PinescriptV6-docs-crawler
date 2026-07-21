# Pine Script v6 Documentation Crawler & RAG Processor

An automated crawler and heading-aware chunking pipeline for the official TradingView Pine Script v6 documentation. Built with [Crawl4AI](https://github.com/unclecode/crawl4ai) and designed to feed high-quality chunks directly into RAG ingestion pipelines (e.g. pgvector, Pinecone, Qdrant).

## Features

- **Incremental Crawling**: SHA-256 content hashing via `manifest.json` — skips unchanged pages automatically on subsequent runs.
- **Clean Overwrites**: Overwrites `page_name.md` instead of accumulating timestamped files.
- **Heading-Aware Chunking**: `chunker.py` splits documents at H1/H2 boundaries into self-contained sections (`<3000` chars, `200` char overlap). Never cuts inside Pine Script code blocks.
- **Breadcrumb Context**: Each chunk includes section breadcrumbs (e.g. `["Language", "Types", "Arrays"]`) for rich context during vector retrieval.
- **JSONL Combined Output**: Exports `chunks_all_docs.jsonl` for one-pass vector DB population.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt
playwright install

# 2. Run full pipeline (crawl -> process -> chunk)
python crawl_and_process.py

# 3. Or run steps individually:
python pinescriptV6docs.py        # Crawl only
python process_docs.py            # Process & chunk only
python process_docs.py --no-chunk # Process without chunking
```

## Repository Structure

```
PinescriptV6-docs-crawler/
├── config.py              # Centralized configuration
├── pinescriptV6docs.py    # Crawls TradingView docs with incremental hashing
├── process_docs.py        # Cleans markdown & generates chunked JSONL
├── chunker.py             # Heading-aware RAG chunker module
├── crawl_and_process.py   # Convenience script running both steps
├── requirements.txt       # Dependencies
├── README.md
├── .github/workflows/
│   └── refresh-docs.yml   # Manual CI trigger for on-demand cloud refresh
└── tests/                 # Comprehensive test suite
    ├── test_process.py
    └── test_chunker.py
```

## Regenerating Docs (CI)

A GitHub Actions workflow (`.github/workflows/refresh-docs.yml`) lets you re-crawl and reprocess the docs **on demand** from the Actions tab (`workflow_dispatch`). Pine Script v6 is stable, so there is no timer by default — run it when you actually have a reason: a new language feature landed, you're cloning fresh, or you're doing a pre-release check. A commented-out quarterly cron lives in the file if you ever want a passive drift check instead. Thanks to incremental crawling, a run that finds no changes commits nothing, so triggering it "just in case" is essentially free.

## Testing

```bash
pytest tests/
```

## License

MIT
