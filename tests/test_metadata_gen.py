"""
Tests for ingestion/metadata_gen.py.

Validates the Gemini call path, JSON response validation, type coercion,
and fallback behavior. All Gemini API calls are mocked — no live API keys
are required to run these tests.

Run:
    pytest tests/test_metadata_gen.py -v
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ingestion.metadata_gen import GeminiExtractionError, MetadataGenerator
from models import Chunk, ChunkMetadata


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def generator(tmp_path: Path) -> MetadataGenerator:
    """MetadataGenerator pointed at a minimal test schema."""
    schema_path = tmp_path / "schema.json"
    schema_path.write_text('{"properties": {}, "required": []}')
    return MetadataGenerator(model_name="gemini-1.5-flash", schema_path=schema_path)


def make_chunk(text: str = "Sample clinical text.", doc_id: str = "abc123") -> Chunk:
    return Chunk(
        chunk_id=f"{doc_id}_00000",
        doc_id=doc_id,
        text=text,
        page_start=1,
        page_end=1,
        chunk_index=0,
        parent_section="Introduction",
    )


# ---------------------------------------------------------------------------
# MetadataGenerator.generate
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_returns_chunk_metadata(self, generator: MetadataGenerator) -> None:
        """generate() should return a ChunkMetadata instance."""
        raise NotImplementedError

    def test_populates_doc_id_from_chunk(self, generator: MetadataGenerator) -> None:
        """Returned metadata.doc_id should match chunk.doc_id."""
        raise NotImplementedError

    def test_falls_back_when_gemini_raises(self, generator: MetadataGenerator) -> None:
        """generate() should return fallback metadata rather than propagating Gemini errors."""
        raise NotImplementedError

    def test_falls_back_on_invalid_json(self, generator: MetadataGenerator) -> None:
        """generate() should use _fallback_extraction if Gemini returns malformed JSON."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# MetadataGenerator._validate_and_coerce
# ---------------------------------------------------------------------------


class TestValidateAndCoerce:
    def test_coerces_string_year_to_int(self, generator: MetadataGenerator) -> None:
        """'2019' as a string should be coerced to int 2019 in year_published."""
        raise NotImplementedError

    def test_coerces_single_keyword_string_to_list(
        self, generator: MetadataGenerator
    ) -> None:
        """A bare string for 'keywords' should be wrapped in a list."""
        raise NotImplementedError

    def test_unknown_doc_type_is_set_to_empty(self, generator: MetadataGenerator) -> None:
        """An unrecognized doc_type value should be coerced to '' to avoid filter errors."""
        raise NotImplementedError

    def test_page_provenance_overrides_gemini_values(
        self, generator: MetadataGenerator
    ) -> None:
        """page_start, page_end, chunk_index, and doc_id should always come from the Chunk,
        not from the Gemini response."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# MetadataGenerator._fallback_extraction
# ---------------------------------------------------------------------------


class TestFallbackExtraction:
    def test_returns_metadata_with_correct_doc_id(
        self, generator: MetadataGenerator
    ) -> None:
        """Fallback metadata should have the chunk's doc_id set correctly."""
        chunk = make_chunk(doc_id="deadbeef" * 8)
        result = generator._fallback_extraction(chunk)
        assert result.doc_id == chunk.doc_id

    def test_keywords_list_is_not_none(self, generator: MetadataGenerator) -> None:
        """Fallback metadata.keywords should be a list (possibly empty), never None."""
        raise NotImplementedError

    def test_does_not_raise_on_empty_chunk_text(
        self, generator: MetadataGenerator
    ) -> None:
        """_fallback_extraction should not raise for a chunk with empty text."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# MetadataGenerator.generate_batch
# ---------------------------------------------------------------------------


class TestGenerateBatch:
    def test_returns_same_count_as_input(self, generator: MetadataGenerator) -> None:
        """generate_batch should return exactly len(chunks) metadata objects."""
        raise NotImplementedError

    def test_order_is_preserved(self, generator: MetadataGenerator) -> None:
        """Output metadata[i] should correspond to input chunks[i]."""
        raise NotImplementedError
