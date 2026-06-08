"""
Tests for ingestion/extractor.py.

Covers the PDFExtractor's text-layer detection, pdfplumber extraction path,
and Document AI fallback path. Uses sample PDFs in tests/fixtures/.

Run:
    pytest tests/test_extractor.py -v
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ingestion.extractor import PDFExtractor
from models import ExtractedDocument, Page


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def extractor() -> PDFExtractor:
    """PDFExtractor with Document AI disabled (default test configuration)."""
    return PDFExtractor(use_document_ai=False)


@pytest.fixture
def extractor_with_docai() -> PDFExtractor:
    """PDFExtractor configured to use Document AI."""
    return PDFExtractor(
        use_document_ai=True,
        document_ai_processor_id="projects/test/locations/us/processors/test-processor",
        project_id="test-project",
    )


# ---------------------------------------------------------------------------
# PDFExtractor.extract
# ---------------------------------------------------------------------------


class TestExtract:
    def test_raises_on_missing_file(self, extractor: PDFExtractor) -> None:
        """extract() should raise FileNotFoundError for a non-existent path."""
        raise NotImplementedError

    def test_returns_extracted_document(self, extractor: PDFExtractor, tmp_path: Path) -> None:
        """extract() should return an ExtractedDocument for a valid PDF."""
        raise NotImplementedError

    def test_falls_back_to_document_ai_when_no_text_layer(
        self, extractor: PDFExtractor
    ) -> None:
        """extract() should trigger Document AI when pdfplumber yields no text."""
        raise NotImplementedError

    def test_sets_correct_extraction_method(self, extractor: PDFExtractor, tmp_path: Path) -> None:
        """ExtractedDocument.extraction_method should reflect which path was used."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# PDFExtractor._has_text_layer
# ---------------------------------------------------------------------------


class TestHasTextLayer:
    def test_returns_true_for_text_heavy_doc(self, extractor: PDFExtractor) -> None:
        """_has_text_layer returns True when average chars/page exceeds threshold."""
        raise NotImplementedError

    def test_returns_false_for_empty_pages(self, extractor: PDFExtractor) -> None:
        """_has_text_layer returns False when pages have no text."""
        raise NotImplementedError

    def test_uses_min_chars_threshold(self) -> None:
        """_has_text_layer respects the min_text_chars_per_page configuration."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# PDFExtractor._parse_pdfplumber_page
# ---------------------------------------------------------------------------


class TestParsePdfplumberPage:
    def test_preserves_page_number(self, extractor: PDFExtractor) -> None:
        """Returned Page.page_num should match the input page_num argument."""
        raise NotImplementedError

    def test_detects_figures_from_image_objects(self, extractor: PDFExtractor) -> None:
        """Page.has_figures should be True when the pdfplumber page has images."""
        raise NotImplementedError

    def test_extracts_tables(self, extractor: PDFExtractor) -> None:
        """_parse_pdfplumber_page should populate Page.tables for pages with tables."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# PDFExtractor._extract_tables
# ---------------------------------------------------------------------------


class TestExtractTables:
    def test_returns_empty_list_for_no_tables(self, extractor: PDFExtractor) -> None:
        """_extract_tables should return [] when the page has no tables."""
        raise NotImplementedError

    def test_table_has_rows_key(self, extractor: PDFExtractor) -> None:
        """Each table dict should contain a 'rows' key with a list of row arrays."""
        raise NotImplementedError
