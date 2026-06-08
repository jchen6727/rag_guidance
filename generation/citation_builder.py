"""
Citation building and formatting.

Maps Attribution objects (from ResponseGenerator) to numbered Citation objects
using the SearchResult metadata for page numbers and source details.

See caveats.md §2 and issues.md P2 for known limitations:
  - Grounding attributions are approximate; page-level precision is not guaranteed.
  - Hallucinated content receives no attribution and will appear without a citation.
  - Un-cited spans should be visually flagged in the UI, not silently passed through.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

from models import Attribution, Citation, SearchResult

logger = logging.getLogger(__name__)


class CitationBuilder:
    """
    Converts Attribution objects into formatted Citation references.

    Usage:
        builder = CitationBuilder()
        citations = builder.build(attributions, results)
        annotated_text = builder.format_inline(response_text, citations)
        reference_list = builder.format_reference_list(citations)
    """

    def build(
        self,
        attributions: list[Attribution],
        results: list[SearchResult],
    ) -> list[Citation]:
        """Build a deduplicated, numbered list of Citations from attributions.

        Each unique source_chunk_id in attributions becomes one Citation.
        Citation numbers are assigned in order of first appearance in attributions.

        Args:
            attributions: Grounding attributions from ResponseGenerator.
            results: The SearchResults used to look up page metadata by chunk ID.

        Returns:
            List of Citation objects with numbers starting at 1.
            Returns an empty list if attributions is empty (no grounding metadata).
        """
        raise NotImplementedError

    def format_inline(
        self, response_text: str, citations: list[Citation]
    ) -> str:
        """Insert inline [n] citation markers into the response text.

        Uses the Attribution.segment_text to locate where each attribution
        appears in response_text and inserts "[n]" immediately after the
        corresponding span.

        Falls back to appending "[n]" at the end of the response for
        attributions whose segment_text cannot be located (fuzzy match failure).

        Args:
            response_text: The raw generated response from Gemini.
            citations: Ordered citations from build().

        Returns:
            Response text with inline [n] markers inserted.
        """
        raise NotImplementedError

    def format_reference_list(self, citations: list[Citation]) -> str:
        """Format citations as a numbered reference list for appending to the response.

        Output format per citation:
            [n] <title>. <chapter>. <source_file>, pp. <page_start>–<page_end>.

        Args:
            citations: Ordered list of Citation objects.

        Returns:
            Multi-line string starting with "---\\nReferences:\\n".
            Returns empty string if citations is empty.
        """
        raise NotImplementedError

    def _lookup_chunk(
        self, chunk_id: str, results: list[SearchResult]
    ) -> Optional[SearchResult]:
        """Find the SearchResult with the given chunk_id.

        Args:
            chunk_id: The chunk ID to look up.
            results: List of SearchResult objects to search.

        Returns:
            Matching SearchResult, or None if not found.
        """
        raise NotImplementedError

    def _make_citation(
        self,
        number: int,
        chunk_id: str,
        result: Optional[SearchResult],
    ) -> Citation:
        """Build a Citation from a SearchResult's metadata.

        Falls back to placeholder values ("Unknown", page 0) if the result
        or its metadata is None, so the citation list is always complete.

        Args:
            number: 1-based citation number.
            chunk_id: Source chunk ID.
            result: SearchResult containing page and title metadata. May be None.

        Returns:
            Populated Citation dataclass.
        """
        raise NotImplementedError
