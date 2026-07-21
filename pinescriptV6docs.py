"""
pinescriptV6docs.py - Crawl official Pine Script v6 documentation from TradingView.

Improvements:
  - Overwrites page_name.md instead of accumulating page_name_TIMESTAMP.md files
  - SHA-256 content hashing with manifest.json (skips unchanged pages unless --force)
  - Configurable batch size (--batch-size) and rate limiting (--rate-limit)
  - Removed unused LLMExtractionStrategy
  - Uses standard logging module
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import List, Set

from bs4 import BeautifulSoup
from crawl4ai import AsyncWebCrawler, BrowserConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    BASE_URL,
    DOCS_DIR,
    MANIFEST_FILE,
    DEFAULT_BATCH_SIZE,
    DEFAULT_RATE_LIMIT_SEC,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PineScriptDocsCrawler:
    def __init__(
        self,
        batch_size: int = DEFAULT_BATCH_SIZE,
        rate_limit: float = DEFAULT_RATE_LIMIT_SEC,
        force: bool = False,
    ):
        self.base_url = BASE_URL
        self.output_dir = DOCS_DIR
        self.batch_size = batch_size
        self.rate_limit = rate_limit
        self.force = force
        self.visited_urls: Set[str] = set()
        self.manifest: dict[str, str] = self._load_manifest()

        self.structure_schema = {
            "name": "PineScript Documentation",
            "baseSelector": "main",
            "fields": [
                {"name": "title", "selector": "h1", "type": "text"},
                {"name": "content", "selector": "main > div", "type": "html"},
                {"name": "navigation", "selector": "nav", "type": "html"},
                {
                    "name": "toc",
                    "selector": "[aria-label='Table of contents']",
                    "type": "html",
                },
            ],
        }

    def _load_manifest(self) -> dict[str, str]:
        if MANIFEST_FILE.exists():
            try:
                with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning("Failed to load manifest file: %s", e)
        return {}

    def _save_manifest(self) -> None:
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
                json.dump(self.manifest, f, indent=2)
        except Exception as e:
            logger.error("Failed to save manifest file: %s", e)

    @staticmethod
    def _compute_hash(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def normalize_url(self, url: str) -> str:
        if not url:
            return ""

        url = url.split("#")[0].split("?")[0]

        if url.startswith(("http", "https")) and not url.startswith(self.base_url):
            return ""
        if url.startswith(("mailto:", "tel:", "javascript:")):
            return ""

        if not url.startswith("http"):
            if url.startswith("/"):
                url = f"https://www.tradingview.com{url}"
            else:
                url = f"{self.base_url}/{url}"

        return url

    async def get_all_doc_urls(self) -> List[str]:
        urls = set()
        logger.info("Collecting URLs from main page...")

        browser_config = BrowserConfig(
            headless=True,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )

        async with AsyncWebCrawler(config=browser_config) as crawler:
            result = await crawler.arun(url=f"{self.base_url}/welcome/")
            if result.success:
                logger.info("Successfully accessed main welcome page")
                soup = BeautifulSoup(result.html, "html.parser")

                nav_elements = soup.find_all(["nav", "div"], class_=["toc", "sidebar"])
                for nav in nav_elements:
                    for link in nav.find_all("a"):
                        href = link.get("href")
                        if href:
                            full_url = self.normalize_url(href)
                            if full_url:
                                urls.add(full_url)
            else:
                logger.error("Failed to access main page: %s", result.error_message)

        urls_list = sorted(list(urls))
        logger.info("Total URLs found: %d", len(urls_list))
        return urls_list

    async def crawl_docs(self, urls: List[str]):
        self.output_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Output directory: %s", self.output_dir)

        structure_strategy = JsonCssExtractionStrategy(
            schema=self.structure_schema, verbose=False
        )

        browser_config = BrowserConfig(
            headless=True,
            extra_args=["--disable-gpu", "--disable-dev-shm-usage", "--no-sandbox"],
        )

        success = 0
        skipped = 0
        failed = 0

        async with AsyncWebCrawler(config=browser_config) as crawler:
            total_batches = (len(urls) + self.batch_size - 1) // self.batch_size
            for i in range(0, len(urls), self.batch_size):
                batch = urls[i : i + self.batch_size]
                logger.info(
                    "Processing batch %d/%d (%d pages)",
                    i // self.batch_size + 1,
                    total_batches,
                    len(batch),
                )

                for url in batch:
                    try:
                        page_name = url.rstrip("/").split("/")[-1] or "index"

                        result = await crawler.arun(
                            url=url, extraction_strategy=structure_strategy
                        )

                        if result.success:
                            if isinstance(result.markdown, str):
                                content = result.markdown
                            else:
                                content = (
                                    result.markdown.raw_markdown
                                    if result.markdown
                                    else ""
                                )

                            content_hash = self._compute_hash(content)
                            file_path = self.output_dir / f"{page_name}.md"

                            if (
                                not self.force
                                and self.manifest.get(page_name) == content_hash
                                and file_path.exists()
                            ):
                                logger.info("  [SKIPPED - unchanged] %s", page_name)
                                skipped += 1
                                continue

                            with open(file_path, "w", encoding="utf-8") as f:
                                f.write(f"# {page_name}\n\n")
                                f.write(f"Source: {url}\n\n")
                                f.write(content)

                            self.manifest[page_name] = content_hash
                            success += 1
                            logger.info("  [SAVED] %s", page_name)
                        else:
                            logger.warning(
                                "Failed to crawl %s: %s", url, result.error_message
                            )
                            failed += 1

                    except Exception as e:
                        logger.error("Error processing %s: %s", url, e)
                        failed += 1

                self._save_manifest()
                if i + self.batch_size < len(urls):
                    await asyncio.sleep(self.rate_limit)

        logger.info(
            "Crawling completed: %d saved/updated, %d skipped, %d failed",
            success,
            skipped,
            failed,
        )

    async def run(self):
        logger.info("Starting PineScript v6 documentation crawler...")
        urls = await self.get_all_doc_urls()
        if not urls:
            logger.error("No documentation pages found!")
            return
        await self.crawl_docs(urls)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl official Pine Script v6 docs from TradingView."
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
        help=f"Number of pages to crawl per batch (default: {DEFAULT_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--rate-limit",
        type=float,
        default=DEFAULT_RATE_LIMIT_SEC,
        help=f"Delay in seconds between batches (default: {DEFAULT_RATE_LIMIT_SEC}).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-crawling all pages regardless of content hash.",
    )
    return parser.parse_args()


async def main():
    args = parse_args()
    crawler = PineScriptDocsCrawler(
        batch_size=args.batch_size, rate_limit=args.rate_limit, force=args.force
    )
    await crawler.run()


if __name__ == "__main__":
    asyncio.run(main())
