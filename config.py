"""Centralized configuration for Pine Script v6 docs crawler and processor."""

from __future__ import annotations

import os
from pathlib import Path

# Base URLs
BASE_URL = os.getenv("PINESCRIPT_BASE_URL", "https://www.tradingview.com/pine-script-docs")

# Directories
BASE_DIR = Path(__file__).parent.resolve()
DOCS_DIR = BASE_DIR / "pinescript_docs"
PROCESSED_DIR = DOCS_DIR / "processed"
CHUNKS_DIR = DOCS_DIR / "chunks"
MANIFEST_FILE = DOCS_DIR / "manifest.json"

# Crawling settings
DEFAULT_BATCH_SIZE = int(os.getenv("PINESCRIPT_BATCH_SIZE", "3"))
DEFAULT_RATE_LIMIT_SEC = float(os.getenv("PINESCRIPT_RATE_LIMIT", "2.0"))

# Processing & Chunking settings
MIN_CONTENT_LENGTH = int(os.getenv("PINESCRIPT_MIN_CONTENT_LEN", "100"))
MAX_CHUNK_CHARS = int(os.getenv("PINESCRIPT_MAX_CHUNK_CHARS", "3000"))
CHUNK_OVERLAP_CHARS = int(os.getenv("PINESCRIPT_CHUNK_OVERLAP", "200"))

# File naming
COMBINED_FILENAME = "processed_all_docs.md"
CHUNKS_COMBINED_FILENAME = "chunks_all_docs.jsonl"
