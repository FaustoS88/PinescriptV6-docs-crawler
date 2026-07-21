"""
crawl_and_process.py - Convenience script to run full pipeline: crawl -> process -> chunk.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from pinescriptV6docs import PineScriptDocsCrawler
from process_docs import PineScriptDocsProcessor, chunk_processed_files
from config import DOCS_DIR

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    logger.info("=" * 60)
    logger.info("Step 1/2: Crawling Pine Script v6 documentation...")
    logger.info("=" * 60)
    crawler = PineScriptDocsCrawler()
    await crawler.run()

    logger.info("\n" + "=" * 60)
    logger.info("Step 2/2: Processing and chunking documentation...")
    logger.info("=" * 60)
    processor = PineScriptDocsProcessor(DOCS_DIR)
    processed = processor.process_all()

    chunks_dir = DOCS_DIR / "chunks"
    total_chunks = chunk_processed_files(processor.output_dir, chunks_dir)

    logger.info("\nPipeline complete!")
    logger.info("Processed %d files, generated %d chunks.", len(processed), total_chunks)
    logger.info("Processed docs: %s", processor.output_dir)
    logger.info("Chunks output: %s", chunks_dir)


if __name__ == "__main__":
    asyncio.run(main())
