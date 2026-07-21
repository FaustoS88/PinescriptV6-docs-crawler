"""
chunker.py - Heading-aware document chunking for downstream RAG.

Splits markdown documents at H1/H2 boundaries so each chunk is a
self-contained section. Never splits inside pine code fences.
Carries section_path breadcrumbs for hierarchical context.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class DocChunk:
    """A single chunk of documentation."""

    title: str
    content: str
    url: str
    section_path: list[str] = field(default_factory=list)
    code_blocks: list[str] = field(default_factory=list)
    char_count: int = 0

    def __post_init__(self):
        self.char_count = len(self.content)


def chunk_by_headings(
    markdown: str,
    source_url: str = "",
    max_chunk_chars: int = 3000,
    overlap_chars: int = 200,
    min_chunk_chars: int = 50,
) -> list[DocChunk]:
    """Split a markdown document into chunks at H1/H2 boundaries."""
    lines = markdown.split("\n")
    chunks: list[DocChunk] = []
    current_lines: list[str] = []
    current_h1 = ""
    current_h2 = ""
    in_code_fence = False

    def flush() -> None:
        nonlocal current_lines
        if not current_lines:
            return
        text = "\n".join(current_lines).strip()
        if len(text) < min_chunk_chars:
            current_lines = []
            return

        section_path = [p for p in [current_h1, current_h2] if p]
        code_blocks = re.findall(r"```(?:pine)?\n(.*?)```", text, re.DOTALL)

        if len(text) > max_chunk_chars:
            sub_chunks = _split_large_chunk(text, max_chunk_chars, overlap_chars)
            for i, sub in enumerate(sub_chunks):
                chunks.append(
                    DocChunk(
                        title=f"{current_h2 or current_h1 or 'Untitled'} (part {i + 1})",
                        content=sub,
                        url=source_url,
                        section_path=section_path,
                        code_blocks=code_blocks if i == 0 else [],
                    )
                )
        else:
            chunks.append(
                DocChunk(
                    title=current_h2 or current_h1 or "Untitled",
                    content=text,
                    url=source_url,
                    section_path=section_path,
                    code_blocks=code_blocks,
                )
            )
        current_lines = []

    for line in lines:
        # Track code fences - never split inside them
        if line.strip().startswith("```"):
            in_code_fence = not in_code_fence
            current_lines.append(line)
            continue

        if in_code_fence:
            current_lines.append(line)
            continue

        h1_match = re.match(r"^# (.+)", line)
        h2_match = re.match(r"^## (.+)", line)

        if h1_match:
            flush()
            current_h1 = h1_match.group(1).strip()
            current_h2 = ""
            current_lines.append(line)
        elif h2_match:
            flush()
            current_h2 = h2_match.group(1).strip()
            current_lines.append(line)
        else:
            current_lines.append(line)

    flush()  # last chunk
    return chunks


def _split_large_chunk(text: str, max_chars: int, overlap: int) -> list[str]:
    """Split an oversized chunk at paragraph boundaries with overlap."""
    paragraphs = text.split("\n\n")
    result: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 2 > max_chars and current:
            result.append(current.strip())
            current = current[-overlap:] + "\n\n" + para
        else:
            current = current + "\n\n" + para if current else para

    if current.strip():
        result.append(current.strip())
    return result
