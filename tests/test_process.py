"""Tests for process_docs.py - the processing pipeline."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from process_docs import PineScriptDocsProcessor


@pytest.fixture
def tmp_docs(tmp_path):
    """Create a temporary docs directory with sample files."""
    docs_dir = tmp_path / "pinescript_docs"
    docs_dir.mkdir()

    (docs_dir / "arrays.md").write_text(
        "# Arrays and matrices\n\n"
        "Source: https://www.tradingview.com/pine-script-docs/en/v6/language/Arrays.html\n\n"
        "## Creating arrays\n\n"
        "Pine Script arrays are created with `array.new_float()`.\n\n"
        "```pine\n"
        "//@version=6\n"
        "indicator(\"Array Example\")\n"
        "a = array.new_float(5, 0.0)\n"
        "```\n\n"
        "## Array functions\n\n"
        "The `array.push()` function appends a value.\n",
        encoding="utf-8",
    )

    (docs_dir / "operators.md").write_text(
        "# Operators\n\n"
        "Source: https://www.tradingview.com/pine-script-docs/en/v6/language/Operators.html\n\n"
        "## Arithmetic operators\n\n"
        "Pine Script supports +, -, *, /, % operators.\n\n"
        "## Comparison operators\n\n"
        "Use ==, !=, >, <, >=, <= for comparisons.\n",
        encoding="utf-8",
    )

    (docs_dir / "welcome.md").write_text(
        "# Welcome\n\n"
        "* [Home](/pine-script-docs/)\n"
        "* [Language](/pine-script-docs/en/v6/language/)\n\n"
        "## Getting started\n\n"
        "Pine Script is a domain-specific language for TradingView.\n"
        "See the [documentation](https://www.tradingview.com/pine-script-docs/) for details.\n",
        encoding="utf-8",
    )

    (docs_dir / "empty.md").write_text("# Empty\n\nNothing here.\n", encoding="utf-8")

    return docs_dir


class TestCleanNavigation:
    def test_strips_nav_links(self, tmp_docs):
        proc = PineScriptDocsProcessor(tmp_docs)
        text = "* [Home](/pine-script-docs/)\n* [Language](/en/v6/)\n\nReal content here."
        cleaned = proc.clean_navigation(text)
        assert "[Home]" not in cleaned
        assert "[Language]" not in cleaned
        assert "Real content here." in cleaned

    def test_preserves_inline_links(self, tmp_docs):
        proc = PineScriptDocsProcessor(tmp_docs)
        text = "See the [docs](https://www.tradingview.com/pine-script-docs/) for details."
        cleaned = proc.clean_navigation(text)
        assert "https://www.tradingview.com/pine-script-docs/" in cleaned


class TestProcessFile:
    def test_processes_standard_headings(self, tmp_docs):
        proc = PineScriptDocsProcessor(tmp_docs)
        result = proc.process_file("arrays.md")
        assert result is not None
        output = (proc.output_dir / result).read_text()
        assert "Creating arrays" in output
        assert "array.new_float" in output

    def test_processes_page_without_user_manual(self, tmp_docs):
        proc = PineScriptDocsProcessor(tmp_docs)
        result = proc.process_file("operators.md")
        assert result is not None
        output = (proc.output_dir / result).read_text()
        assert "Arithmetic operators" in output

    def test_skips_too_short(self, tmp_docs):
        proc = PineScriptDocsProcessor(tmp_docs)
        result = proc.process_file("empty.md")
        assert result is None

    def test_preserves_code_blocks(self, tmp_docs):
        proc = PineScriptDocsProcessor(tmp_docs)
        result = proc.process_file("arrays.md")
        output = (proc.output_dir / result).read_text()
        assert "```pine" in output
        assert "array.new_float(5, 0.0)" in output


class TestProcessAll:
    def test_deterministic_order(self, tmp_docs):
        proc = PineScriptDocsProcessor(tmp_docs)
        processed = proc.process_all()
        assert len(processed) >= 2

    def test_combined_file_created(self, tmp_docs):
        proc = PineScriptDocsProcessor(tmp_docs)
        proc.process_all()
        combined = proc.output_dir / "processed_all_docs.md"
        assert combined.exists()
        content = combined.read_text()
        assert len(content) > 100


class TestNumericSort:
    def test_numeric_ordering(self):
        key = PineScriptDocsProcessor._numeric_sort_key
        files = ["10_operators.md", "2_types.md", "1_intro.md", "welcome.md"]
        sorted_files = sorted(files, key=key)
        assert sorted_files == ["1_intro.md", "2_types.md", "10_operators.md", "welcome.md"]
