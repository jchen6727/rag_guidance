"""
AI-guided metadata generation using Google Gemini.

Sends each chunk (plus a configurable surrounding context window) to Gemini
with a structured extraction prompt. The response is validated against the
ChunkMetadata Pydantic schema. On parse failure, falls back to rule-based
heuristics so that ingestion never hard-fails due to a bad Gemini response.

See caveats.md §2 (Gemini output reliability) and issues.md P3 (schema drift).

Rate limiting: standard Gemini 1.5 Pro quotas are ~360 RPM. For large batches
use exponential backoff or switch to Vertex AI Batch Prediction.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

import google.generativeai as genai

from models import Chunk, ChunkMetadata

logger = logging.getLogger(__name__)

# Default retry parameters for Gemini API calls
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0  # seconds; doubled each attempt


class MetadataGenerator:
    """
    Calls Gemini to extract structured metadata from document chunks.

    Usage:
        gen = MetadataGenerator(model_name="gemini-1.5-pro")
        metadata = gen.generate(chunk, context_window=preceding_text)
        chunk.metadata = metadata
    """

    def __init__(
        self,
        model_name: str = "gemini-1.5-pro",
        schema_path: Optional[Path] = None,
        temperature: float = 0.0,
        api_key: Optional[str] = None,
    ) -> None:
        """
        Args:
            model_name: Gemini model identifier. gemini-1.5-pro is recommended
                        for long-context metadata extraction; gemini-1.5-flash
                        is acceptable for short chunks if cost is a concern.
            schema_path: Path to config/metadata_schema.json. Loaded at init;
                         defaults to the project-local path if None.
            temperature: Gemini sampling temperature. 0.0 for deterministic output.
            api_key: Gemini API key. Falls back to GEMINI_API_KEY env var if None.
        """
        self._model_name = model_name
        self._temperature = temperature
        self._schema = self._load_schema(schema_path)
        self._client: Optional[genai.GenerativeModel] = None
        self._api_key = api_key

    def generate(self, chunk: Chunk, context_window: str = "") -> ChunkMetadata:
        """Generate metadata for a single chunk.

        Builds the extraction prompt, calls Gemini with retry/backoff, validates
        the response, and returns a ChunkMetadata. Falls back to rule-based
        extraction if Gemini fails after all retries.

        Args:
            chunk: The chunk to generate metadata for.
            context_window: Optional preceding text (e.g., previous chunk or section
                            header) to give Gemini additional context.

        Returns:
            Validated ChunkMetadata. Fields that cannot be inferred are set to
            their default values (empty string / None / empty list).
        """
        raise NotImplementedError

    def generate_batch(
        self,
        chunks: list[Chunk],
        context_window: str = "",
        delay_between_calls: float = 0.1,
    ) -> list[ChunkMetadata]:
        """Generate metadata for a list of chunks sequentially with rate-limiting.

        For large batches (>1000 chunks), consider switching to Vertex AI Batch
        Prediction to avoid hitting online quota limits.

        Args:
            chunks: Chunks to process, in order.
            context_window: Shared context text passed to every generate() call.
            delay_between_calls: Seconds to sleep between calls for rate limiting.

        Returns:
            List of ChunkMetadata in the same order as the input chunks.
        """
        raise NotImplementedError

    def _build_extraction_prompt(self, chunk: Chunk, context_window: str) -> str:
        """Build the Gemini extraction prompt for a chunk.

        The prompt includes:
          - The JSON schema of required output fields (from self._schema)
          - The context window (if provided)
          - The chunk text
          - Explicit instruction to output valid JSON only

        Args:
            chunk: Chunk to extract metadata for.
            context_window: Preceding text for additional context.

        Returns:
            Full prompt string ready to send to Gemini.
        """
        raise NotImplementedError

    def _call_gemini(self, prompt: str) -> dict:
        """Send prompt to Gemini and return the parsed JSON response.

        Uses response_mime_type="application/json" to request structured output.
        Retries on transient errors with exponential backoff.

        Args:
            prompt: The full extraction prompt.

        Returns:
            Parsed dict from the model's JSON response.

        Raises:
            GeminiExtractionError: If all retries are exhausted or the response
                                   cannot be parsed as JSON.
        """
        raise NotImplementedError

    def _validate_and_coerce(self, raw: dict, chunk: Chunk) -> ChunkMetadata:
        """Validate the Gemini response dict against ChunkMetadata and coerce types.

        Common coercions:
          - String "2019" -> int 2019 for year_published
          - Single string -> list[str] for keywords and entities
          - Unknown doc_type values -> "" to avoid filter expression errors

        Args:
            raw: Raw dict parsed from Gemini's JSON response.
            chunk: Source chunk (used to fill doc_id, chunk_index, page_start, etc.).

        Returns:
            Valid ChunkMetadata instance.

        Raises:
            ValidationError: If the response is structurally invalid after coercion.
                             Callers should catch this and call _fallback_extraction.
        """
        raise NotImplementedError

    def _fallback_extraction(self, chunk: Chunk) -> ChunkMetadata:
        """Produce minimal metadata via rule-based heuristics when Gemini fails.

        Extracts:
          - doc_id, source_file, page_start, page_end, chunk_index from chunk fields
          - title from the first non-empty line of chunk text
          - keywords from high-frequency capitalized terms (TF-IDF not available here)
          - All other fields set to defaults

        Args:
            chunk: The chunk for which Gemini extraction failed.

        Returns:
            ChunkMetadata with best-effort populated fields.
        """
        raise NotImplementedError

    def _load_schema(self, schema_path: Optional[Path]) -> dict:
        """Load and return the metadata JSON schema.

        Args:
            schema_path: Explicit path. If None, resolves to
                         <project_root>/config/metadata_schema.json.

        Returns:
            Parsed schema dict.

        Raises:
            FileNotFoundError: If the schema file does not exist.
        """
        raise NotImplementedError

    def _get_client(self) -> genai.GenerativeModel:
        """Lazy-initialize and return the Gemini generative model client.

        Returns:
            Configured GenerativeModel instance.
        """
        raise NotImplementedError


class GeminiExtractionError(Exception):
    """Raised when Gemini metadata extraction fails after all retries."""
