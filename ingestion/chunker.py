"""
Context-aware chunking of extracted PDF documents.

Two-pass strategy (see structure.md §3 and issues.md P1):
  1. Structural pass  — split on detected section headers and page group boundaries.
  2. Semantic pass    — sub-split sections that exceed the token budget using
                        sentence-embedding cosine similarity (split where similarity drops).

Each Chunk carries `parent_section`, `page_start`, and `page_end` provenance fields
so citations can be resolved to source pages.

Configuration is loaded from config/chunk_config.yaml via ChunkerConfig.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from models import Chunk, ExtractedDocument, Page

logger = logging.getLogger(__name__)


@dataclass
class ChunkerConfig:
    """Chunking parameters loaded from config/chunk_config.yaml."""

    max_tokens: int = 512
    """Hard token ceiling for a single chunk. Chunks never exceed this."""

    min_tokens: int = 64
    """Minimum chunk size; smaller fragments are merged with their neighbor."""

    overlap_tokens: int = 64
    """Token overlap between consecutive chunks to preserve context across boundaries."""

    semantic_similarity_threshold: float = 0.75
    """Cosine similarity below which a sentence boundary becomes a chunk boundary.
    Lower values = more splits. Tune per-domain — see issues.md P1."""

    embedding_model: str = "all-MiniLM-L6-v2"
    """sentence-transformers model for semantic boundary detection."""

    header_patterns: list[str] = field(default_factory=lambda: [
        r"^(Chapter|Section|CHAPTER|SECTION)\s+\d+",
        r"^\d+\.\d*\s+[A-Z]",   # "3.1 Introduction" style
        r"^[A-Z][A-Z\s]{4,}$",  # ALL CAPS headers
    ])
    """Regex patterns used to detect section headers in page text."""

    skip_doc_types: list[str] = field(default_factory=lambda: [
        "front_matter",
        "index",
        "bibliography",
    ])
    """Chunk metadata doc_types to exclude from the final output."""


class ContextAwareChunker:
    """
    Converts an ExtractedDocument into a list of semantically coherent Chunks.

    Usage:
        config = ChunkerConfig()
        chunker = ContextAwareChunker(config)
        chunks = chunker.chunk(extracted_doc)
    """

    def __init__(self, config: Optional[ChunkerConfig] = None) -> None:
        """
        Args:
            config: Chunking parameters. Defaults to ChunkerConfig() if None.
        """
        self._config = config or ChunkerConfig()
        self._embedding_model = None  # Lazy-loaded on first use

    def chunk(self, doc: ExtractedDocument) -> list[Chunk]:
        """Convert an ExtractedDocument into a list of Chunks.

        Runs the structural pass followed by the semantic pass on each section.
        Chunks are assigned sequential `chunk_index` values across the document.

        Args:
            doc: Fully extracted document from PDFExtractor.

        Returns:
            Ordered list of Chunks. Empty if the document has no extractable text.
        """
        raise NotImplementedError

    def _structural_split(
        self, doc: ExtractedDocument
    ) -> list[tuple[str, list[Page]]]:
        """Group pages into sections based on detected headers.

        Scans each page for lines matching ChunkerConfig.header_patterns.
        When a new header is found, the current section is closed and a new one
        begins. Pages with no detectable header belong to the most recent section.

        Args:
            doc: Extracted document.

        Returns:
            List of (section_name, pages) tuples in document order.
            `section_name` is the header text or "preamble" for pre-header pages.
        """
        raise NotImplementedError

    def _semantic_split(
        self,
        section_name: str,
        pages: list[Page],
        doc_id: str,
        start_chunk_idx: int,
    ) -> list[Chunk]:
        """Split a section's text into token-bounded, semantically coherent chunks.

        Steps:
          1. Concatenate page text; track page-number offsets per sentence.
          2. Embed all sentences using the configured sentence-transformers model.
          3. Find boundaries where cosine similarity between adjacent sentences
             drops below semantic_similarity_threshold.
          4. Merge spans into chunks respecting max_tokens and min_tokens.
          5. Add overlap tokens from the previous chunk's tail.

        Args:
            section_name: The section header text (used as parent_section).
            pages: Pages in this section.
            doc_id: Parent document ID.
            start_chunk_idx: The chunk_index to assign to the first chunk of this section.

        Returns:
            List of Chunks for this section.
        """
        raise NotImplementedError

    def _detect_section_headers(self, text: str) -> list[str]:
        """Return all lines in text that match any configured header pattern.

        Args:
            text: Raw page text.

        Returns:
            List of matched header strings, in order of appearance.
        """
        raise NotImplementedError

    def _embed_sentences(self, sentences: list[str]) -> "np.ndarray":
        """Compute sentence embeddings using the configured model.

        Lazy-loads the sentence-transformers model on first call.

        Args:
            sentences: List of sentence strings.

        Returns:
            2D numpy array of shape (len(sentences), embedding_dim).
        """
        raise NotImplementedError

    def _find_semantic_boundaries(
        self, embeddings: "np.ndarray"
    ) -> list[int]:
        """Return sentence indices where a chunk boundary should be placed.

        A boundary is placed at index i when the cosine similarity between
        embeddings[i-1] and embeddings[i] drops below
        ChunkerConfig.semantic_similarity_threshold.

        Args:
            embeddings: (N, D) embedding array from _embed_sentences.

        Returns:
            Sorted list of sentence indices that start new chunks.
            Index 0 is always included.
        """
        raise NotImplementedError

    def _token_count(self, text: str) -> int:
        """Approximate token count using whitespace splitting (fast, not exact).

        For a precise count, swap this for a tiktoken or sentencepiece tokenizer
        matching the target model's vocabulary.

        Args:
            text: Input text string.

        Returns:
            Approximate token count.
        """
        raise NotImplementedError

    def _make_chunk_id(self, doc_id: str, chunk_index: int) -> str:
        """Build the canonical chunk ID string.

        Format: "{doc_id}_{chunk_index:05d}"

        Args:
            doc_id: Parent document SHA-256 ID.
            chunk_index: Zero-based sequential chunk index.

        Returns:
            Unique chunk identifier string.
        """
        raise NotImplementedError

    def _load_embedding_model(self) -> None:
        """Lazy-initialize the sentence-transformers model.

        Called on first use of _embed_sentences to avoid loading the model
        during import (slow) or when Document AI OCR falls back (unnecessary).
        """
        raise NotImplementedError
