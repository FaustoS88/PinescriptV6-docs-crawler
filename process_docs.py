"""
process_docs.py - Process crawled Pine Script v6 docs into clean markdown.

Features:
  - Numeric-aware ordering of output files
  - Heading-aware chunking via chunker.py (for downstream RAG)
  - Combined JSONL output for direct ingestion into pgvector

Usage:
    python process_docs.py                # process + chunk
    python process_docs.py --no-chunk     # process only
    python process_docs.py --input ./my_docs  # custom input dir
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from config import (
    DOCS_DIR,
    PROCESSED_DIR,
    CHUNKS_DIR,
    MIN_CONTENT_LENGTH,
    COMBINED_FILENAME,
    CHUNKS_COMBINED_FILENAME,
    MAX_CHUNK_CHARS,
    CHUNK_OVERLAP_CHARS,
)
from chunker import chunk_by_headings, DocChunk

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class PineScriptDocsProcessor:
    """Process crawled Pine Script docs into clean, chunked markdown."""

    def __init__(self, input_dir: str | Path, output_dir: str | Path | None = None):
        self.input_dir = Path(input_dir)
        self.output_dir = Path(output_dir) if output_dir else self.input_dir / "processed"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def clean_navigation(self, text: str) -> str:
        """Remove navigation elements WITHOUT destroying legitimate links."""
        text = re.sub(r"Version Version.*?Auto", "", text, flags=re.DOTALL)
        text = re.sub(r"Copyright ©.*?TradingView.*?\n", "", text)
        text = re.sub(r"On this page.*?\n(?=\n)", "", text, flags=re.DOTALL)
        text = re.sub(r"^\* \[[^\]]*\]\([^)]*\)\s*$", "", text, flags=re.MULTILINE)
        return text

    def extract_code_blocks(self, text: str) -> list[str]:
        """Preserve and clean Pine Script code blocks."""
        code_blocks = re.findall(r"```(?:pine)?\n?(.*?)```", text, re.DOTALL)
        clean_blocks = []
        for block in code_blocks:
            clean_block = block.strip()
            if clean_block:
                clean_blocks.append(f"```pine\n{clean_block}\n```")
        return clean_blocks

    def extract_function_docs(self, text: str) -> list[str]:
        """Extract function documentation blocks."""
        return re.findall(r"@function.*?@returns.*?\n", text, re.DOTALL)

    def process_file(self, filename: str) -> str | None:
        """Process a single documentation file."""
        filepath = self.input_dir / filename
        if not filepath.exists():
            return None

        content = filepath.read_text(encoding="utf-8")

        if len(content) < MIN_CONTENT_LENGTH:
            logger.debug("Skipping %s: too short (%d chars)", filename, len(content))
            return None

        content = self.clean_navigation(content)

        code_blocks = self.extract_code_blocks(content)
        function_docs = self.extract_function_docs(content)

        sections = re.findall(
            r"^##\s+(?:\[([^\]]*)\][^\n]*|([^\n]+))\n(.*?)(?=^##\s|\Z)",
            content,
            re.DOTALL | re.MULTILINE,
        )

        processed: list[str] = []

        if sections:
            for bracket_title, plain_title, section_body in sections:
                title = (bracket_title or plain_title or "").strip()
                if not title:
                    continue

                keywords = [
                    "pine", "script", "function", "indicator", "strategy",
                    "value", "parameter", "variable", "type", "operator",
                    "array", "matrix", "plot", "input", "ta.", "math.",
                    "request.", "strategy.", "label.", "line.", "table.",
                ]
                if any(kw in section_body.lower() for kw in keywords):
                    clean_section = re.sub(r"\[\^[^\]]*\]", "", section_body)
                    processed.append(f"## {title}\n{clean_section.strip()}")

        if code_blocks:
            processed.append("\n## Code Examples\n")
            processed.extend(code_blocks)

        if function_docs:
            processed.append("\n## Function Documentation\n")
            processed.extend(function_docs)

        if not processed:
            logger.debug("Skipping %s: no processable content", filename)
            return None

        output_filename = f"processed_{filename}"
        output_path = self.output_dir / output_filename
        output_path.write_text("\n\n".join(processed), encoding="utf-8")
        return output_filename

    def process_all(self) -> list[str]:
        """Process all markdown files in deterministic (sorted) order."""
        processed_files: list[str] = []
        logger.info("Looking for files in: %s", self.input_dir)

        all_files = sorted(
            [
                f
                for f in os.listdir(self.input_dir)
                if f.endswith(".md")
                and f != "all_docs.md"
                and not f.startswith("processed_")
                and not f.startswith(".")
            ],
            key=self._numeric_sort_key,
        )
        logger.info("Found %d files to process", len(all_files))

        for i, filename in enumerate(all_files, 1):
            logger.info("[%d/%d] Processing: %s", i, len(all_files), filename)
            output_file = self.process_file(filename)
            if output_file:
                processed_files.append(output_file)
                logger.info("  -> %s", output_file)
            else:
                logger.info("  -> skipped (no valid content)")

        combined_path = self.output_dir / COMBINED_FILENAME
        with open(combined_path, "w", encoding="utf-8") as combined:
            for filename in processed_files:
                filepath = self.output_dir / filename
                content = filepath.read_text(encoding="utf-8")
                combined.write(f"\n\n# {filename[:-3]}\n\n")
                combined.write(content)
                combined.write("\n\n---\n\n")

        logger.info("Combined file: %s", combined_path)
        return processed_files

    @staticmethod
    def _numeric_sort_key(filename: str):
        """Sort key that handles numeric prefixes: 1_ < 2_ < 10_."""
        match = re.match(r"^(\d+)", filename)
        if match:
            return (0, int(match.group(1)), filename)
        return (1, 0, filename)


def chunk_processed_files(
    processed_dir: Path,
    chunks_dir: Path,
    max_chars: int = MAX_CHUNK_CHARS,
    overlap: int = CHUNK_OVERLAP_CHARS,
) -> int:
    """Chunk all processed files into heading-aware segments for RAG."""
    chunks_dir.mkdir(parents=True, exist_ok=True)
    total_chunks = 0
    all_chunks: list[dict] = []

    processed_files = sorted(
        [f for f in os.listdir(processed_dir) if f.startswith("processed_") and f.endswith(".md")],
        key=PineScriptDocsProcessor._numeric_sort_key,
    )

    for filename in processed_files:
        filepath = processed_dir / filename
        content = filepath.read_text(encoding="utf-8")

        url_match = re.search(r"Source:\s*(https://\S+)", content)
        source_url = url_match.group(1) if url_match else ""
        clean_content = re.sub(r"Source:\s*https://\S+\n*", "", content)

        chunks = chunk_by_headings(
            markdown=clean_content,
            source_url=source_url,
            max_chunk_chars=max_chars,
            overlap_chars=overlap,
        )

        chunk_filename = filename.replace("processed_", "chunks_").replace(".md", ".jsonl")
        chunk_path = chunks_dir / chunk_filename
        with open(chunk_path, "w", encoding="utf-8") as f:
            for chunk in chunks:
                record = {
                    "title": chunk.title,
                    "content": chunk.content,
                    "url": chunk.url,
                    "section_path": chunk.section_path,
                    "code_blocks": chunk.code_blocks,
                    "char_count": chunk.char_count,
                }
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
                all_chunks.append(record)

        total_chunks += len(chunks)
        logger.info("  %s -> %d chunks", filename, len(chunks))

    combined_path = chunks_dir / CHUNKS_COMBINED_FILENAME
    with open(combined_path, "w", encoding="utf-8") as f:
        for record in all_chunks:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    logger.info("Total chunks: %d -> %s", total_chunks, combined_path)
    return total_chunks


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Process crawled Pine Script docs into clean, chunked markdown."
    )
    parser.add_argument("--input", type=str, default=str(DOCS_DIR),
                        help=f"Input directory with crawled .md files (default: {DOCS_DIR}).")
    parser.add_argument("--output", type=str, default=None,
                        help="Output directory for processed files (default: <input>/processed).")
    parser.add_argument("--no-chunk", action="store_true",
                        help="Skip the chunking step (process only).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_dir = Path(args.input)
    output_dir = Path(args.output) if args.output else None

    processor = PineScriptDocsProcessor(input_dir, output_dir)
    processed = processor.process_all()
    logger.info("Processed %d files", len(processed))

    if not args.no_chunk:
        chunks_dir = input_dir / "chunks"
        total = chunk_processed_files(processor.output_dir, chunks_dir)
        logger.info("Chunking complete: %d chunks", total)


if __name__ == "__main__":
    main()