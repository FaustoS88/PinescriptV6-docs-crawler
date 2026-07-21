"""Tests for chunker.py - heading-aware document chunking."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from chunker import DocChunk, chunk_by_headings, _split_large_chunk


SAMPLE_DOC = """# Pine Script Language

## Variables

Pine Script variables are declared with type prefixes.

```pine
//@version=6
indicator("Test")
x = 10
y = close
```

## Types

Pine Script has int, float, bool, color, and string types.

# Advanced Topics

## Arrays

Arrays store collections of values.

```pine
a = array.new_float(5, 0.0)
array.push(a, close)
```

## Matrices

Matrices are two-dimensional arrays that store elements in rows and columns.
"""


class TestChunkByHeadings:
    def test_splits_at_h1_and_h2(self):
        chunks = chunk_by_headings(SAMPLE_DOC, source_url="https://example.com")
        titles = [c.title for c in chunks]
        assert "Variables" in titles
        assert "Types" in titles
        assert "Arrays" in titles
        assert "Matrices" in titles

    def test_never_splits_code_fence(self):
        chunks = chunk_by_headings(SAMPLE_DOC, source_url="https://example.com")
        for chunk in chunks:
            opens = chunk.content.count("```pine")
            closes = chunk.content.count("```") - opens
            assert opens == closes, f"Unbalanced code fence in chunk: {chunk.title}"

    def test_section_path_breadcrumbs(self):
        chunks = chunk_by_headings(SAMPLE_DOC, source_url="https://example.com")
        arrays_chunk = next(c for c in chunks if c.title == "Arrays")
        assert arrays_chunk.section_path == ["Advanced Topics", "Arrays"]

    def test_url_propagated(self):
        chunks = chunk_by_headings(SAMPLE_DOC, source_url="https://example.com/docs")
        for chunk in chunks:
            assert chunk.url == "https://example.com/docs"

    def test_code_blocks_extracted(self):
        chunks = chunk_by_headings(SAMPLE_DOC, source_url="")
        var_chunk = next(c for c in chunks if c.title == "Variables")
        assert len(var_chunk.code_blocks) == 1
        assert "array.new_float" not in var_chunk.code_blocks[0]

    def test_min_chunk_filter(self):
        tiny_doc = "# Title\n\nHi.\n"
        chunks = chunk_by_headings(tiny_doc, min_chunk_chars=50)
        assert len(chunks) == 0

    def test_empty_input(self):
        chunks = chunk_by_headings("")
        assert chunks == []


class TestSplitLargeChunk:
    def test_respects_max_chars(self):
        text = "\n\n".join([f"Paragraph {i} " + "x" * 200 for i in range(20)])
        parts = _split_large_chunk(text, max_chars=1000, overlap=100)
        for part in parts:
            assert len(part) < 1500

    def test_overlap_present(self):
        text = "\n\n".join([f"Paragraph {i} " + "x" * 200 for i in range(20)])
        parts = _split_large_chunk(text, max_chars=1000, overlap=100)
        if len(parts) > 1:
            assert parts[1][:50] != parts[0][:50]

    def test_single_small_chunk(self):
        text = "Just a small paragraph."
        parts = _split_large_chunk(text, max_chars=3000, overlap=200)
        assert len(parts) == 1
        assert parts[0] == text
