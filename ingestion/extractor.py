"""
PDF text and structure extraction.

Primary path: pdfplumber (layout-aware, handles multi-column and tables).
Fallback path: Google Document AI (OCR for scanned PDFs with no text layer).

The public interface is PDFExtractor.extract(path) which returns an
ExtractedDocument regardless of which path was used.

See caveats.md §3 for known limitations of PDF extraction.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from models import ExtractedDocument, Page

logger = logging.getLogger(__name__)


class PDFExtractor:
    """
    Extracts text and structure from a PDF file.

    Automatically falls back to Document AI OCR when pdfplumber yields
    fewer than `min_text_chars_per_page` characters on average (indicating
    a scanned PDF without a text layer).
    """

    def __init__(
        self,
        use_document_ai: bool = False,
        document_ai_processor_id: str = "",
        project_id: str = "",
        location: str = "us",
        min_text_chars_per_page: int = 100,
    ) -> None:
        """
        Args:
            use_document_ai: If True, always use Document AI instead of pdfplumber.
                             If False, Document AI is used only as a fallback when
                             text-layer detection fails.
            document_ai_processor_id: Full resource name of the Document AI processor,
                                       e.g. projects/{id}/locations/{loc}/processors/{id}.
            project_id: GCP project ID (required if Document AI is enabled).
            location: GCP region for Document AI (typically "us" or "eu").
            min_text_chars_per_page: Average characters per page below which the PDF
                                     is classified as scanned and falls back to OCR.
        """
        self._use_document_ai = use_document_ai
        self._processor_id = document_ai_processor_id
        self._project_id = project_id
        self._location = location
        self._min_chars = min_text_chars_per_page

    def extract(self, path: Path) -> ExtractedDocument:
        """Extract text and structure from a PDF, choosing the appropriate method.

        If use_document_ai is False, attempts pdfplumber first. If the result
        fails the text-layer quality check, re-extracts with Document AI.

        Args:
            path: Absolute path to the PDF file. Must exist and be readable.

        Returns:
            ExtractedDocument with all pages populated.

        Raises:
            FileNotFoundError: If path does not exist.
            ExtractionError: If both pdfplumber and Document AI fail.
        """
        raise NotImplementedError

    def _has_text_layer(self, doc: ExtractedDocument) -> bool:
        """Heuristic check: return True if the document has a usable text layer.

        Computes the average characters per page across all extracted pages.
        Falls back to Document AI if below self._min_chars.

        Args:
            doc: Partially extracted document from pdfplumber.

        Returns:
            True if the document has sufficient text for indexing.
        """
        raise NotImplementedError

    def _extract_with_pdfplumber(self, path: Path) -> ExtractedDocument:
        """Extract text and tables using pdfplumber.

        Preserves page boundaries and attempts to extract table cell content
        as structured rows. Multi-column layouts may produce interleaved text —
        see caveats.md §3.

        Args:
            path: Path to the PDF.

        Returns:
            ExtractedDocument with extraction_method = "pdfplumber".
        """
        raise NotImplementedError

    def _extract_with_document_ai(self, path: Path) -> ExtractedDocument:
        """Extract text using Google Document AI OCR.

        Reads the PDF bytes, submits to the configured processor, and parses
        the response into Page objects. Significantly slower and more expensive
        than pdfplumber (~$1.50/1000 pages) — gate this behind _has_text_layer.

        Args:
            path: Path to the PDF.

        Returns:
            ExtractedDocument with extraction_method = "document_ai".

        Raises:
            ValueError: If document_ai_processor_id is not configured.
        """
        raise NotImplementedError

    def _parse_pdfplumber_page(self, page: object, page_num: int) -> Page:
        """Convert a pdfplumber Page object into the internal Page model.

        Extracts plain text via page.extract_text() and tables via
        page.extract_tables(). Detects figure presence by checking for
        image objects on the page.

        Args:
            page: A pdfplumber page object.
            page_num: 1-indexed page number.

        Returns:
            Populated Page dataclass.
        """
        raise NotImplementedError

    def _extract_tables(self, page: object) -> list[dict]:
        """Extract tables from a pdfplumber page as a list of row arrays.

        Each returned dict has:
            {"rows": [["cell00", "cell01"], ["cell10", "cell11"]], "bbox": tuple}

        Merged cells are represented as None in the row array. Complex table
        structures (spanning headers, nested tables) are not reliably supported.

        Args:
            page: A pdfplumber page object.

        Returns:
            List of table dicts, possibly empty.
        """
        raise NotImplementedError
