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
import os
import time
from pathlib import Path
from typing import Optional

import google.generativeai as genai

from models import Chunk, ChunkMetadata

logger = logging.getLogger(__name__)

# Default retry parameters for Gemini API calls
_MAX_RETRIES = 3
_RETRY_BASE_DELAY = 2.0  # seconds; doubled each attempt

_VALID_DOMAINS = {
    "cardiology", "oncology", "neurology", "pharmacology", "internal_medicine",
    "surgery", "pediatrics", "radiology", "pathology", "immunology", "endocrinology",
    "gastroenterology", "pulmonology", "nephrology", "hematology", "infectious_disease",
    "psychiatry", "dermatology", "orthopedics", "anatomy", "physiology", "biochemistry",
    "microbiology", "genetics", "epidemiology", "biostatistics", "other",
}

_VALID_DOC_TYPES = {
    "textbook", "clinical_guideline", "research_paper",
    "review_article", "case_report", "front_matter",
}

_VALID_EVIDENCE_LEVELS = {"A", "B", "C", "D", None}


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
        try:
            prompt = self._build_extraction_prompt(chunk, context_window)
            raw = self._call_gemini(prompt)
            return self._validate_and_coerce(raw, chunk)
        except Exception as exc:
            logger.warning(
                "Metadata generation failed for chunk %s: %s — using fallback",
                chunk.chunk_id,
                exc,
            )
            return self._fallback_extraction(chunk)

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
        results: list[ChunkMetadata] = []
        for chunk in chunks:
            metadata = self.generate(chunk, context_window)
            results.append(metadata)
            if delay_between_calls > 0:
                time.sleep(delay_between_calls)
        return results

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
        properties = self._schema.get("properties", {})
        schema_excerpt = json.dumps(properties, indent=2)

        parts = [
            "Extract structured metadata from the following clinical/scientific text.",
            "Respond ONLY with valid JSON matching this schema (no markdown, no prose):",
            "",
            schema_excerpt,
            "",
        ]

        if context_window:
            parts += ["Context (preceding text):", context_window, ""]

        parts += [
            "Chunk text to analyze:",
            chunk.text,
            "",
            "Output valid JSON only.",
        ]

        return "\n".join(parts)

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
        client = self._get_client()
        last_exc: Exception = RuntimeError("No attempts made")
        delay = _RETRY_BASE_DELAY

        for attempt in range(_MAX_RETRIES):
            try:
                response = client.generate_content(prompt)
                return json.loads(response.text)
            except json.JSONDecodeError as exc:
                raise GeminiExtractionError(
                    f"Gemini returned non-JSON response: {exc}"
                ) from exc
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Gemini call attempt %d/%d failed: %s", attempt + 1, _MAX_RETRIES, exc
                )
                if attempt < _MAX_RETRIES - 1:
                    time.sleep(delay)
                    delay *= 2

        raise GeminiExtractionError(
            f"All {_MAX_RETRIES} Gemini attempts failed: {last_exc}"
        ) from last_exc

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
        # Coerce year_published
        year = raw.get("year_published")
        if isinstance(year, str):
            try:
                raw["year_published"] = int(year)
            except (ValueError, TypeError):
                raw["year_published"] = None

        # Coerce list fields
        for list_field in ("keywords", "entities"):
            val = raw.get(list_field)
            if isinstance(val, str):
                raw[list_field] = [val]
            elif not isinstance(val, list):
                raw[list_field] = []

        # Coerce domain: unknown values default to "other"
        if raw.get("domain") not in _VALID_DOMAINS:
            raw["domain"] = "other"

        # Coerce doc_type: unknown values default to ""
        if raw.get("doc_type") not in _VALID_DOC_TYPES:
            raw["doc_type"] = ""

        # Coerce evidence_level
        if raw.get("evidence_level") not in _VALID_EVIDENCE_LEVELS:
            raw["evidence_level"] = None

        # Ensure source_file is a string
        if not isinstance(raw.get("source_file"), str):
            raw["source_file"] = ""

        # Always override provenance fields from chunk (never trust Gemini for these)
        raw["doc_id"] = chunk.doc_id
        raw["page_start"] = chunk.page_start
        raw["page_end"] = chunk.page_end
        raw["chunk_index"] = chunk.chunk_index

        return ChunkMetadata(**raw)

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
        lines = [l.strip() for l in chunk.text.splitlines() if l.strip()]
        title = lines[0][:120] if lines else ""

        words = chunk.text.split()
        seen: set[str] = set()
        keywords: list[str] = []
        for word in words:
            cleaned = word.strip(".,;:!?()")
            if cleaned and cleaned[0].isupper() and len(cleaned) > 3 and cleaned not in seen:
                seen.add(cleaned)
                keywords.append(cleaned)
                if len(keywords) >= 10:
                    break

        return ChunkMetadata(
            doc_id=chunk.doc_id,
            source_file="",
            title=title,
            page_start=chunk.page_start,
            page_end=chunk.page_end,
            chunk_index=chunk.chunk_index,
            keywords=keywords,
        )

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
        if schema_path is None:
            schema_path = Path(__file__).parent.parent / "config" / "metadata_schema.json"
        if not schema_path.exists():
            raise FileNotFoundError(f"Metadata schema not found: {schema_path}")
        with open(schema_path) as f:
            return json.load(f)

    def _get_client(self) -> genai.GenerativeModel:
        """Lazy-initialize and return the Gemini generative model client.

        Returns:
            Configured GenerativeModel instance.
        """
        if self._client is not None:
            return self._client

        api_key = self._api_key or os.environ.get("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)

        self._client = genai.GenerativeModel(
            model_name=self._model_name,
            generation_config=genai.types.GenerationConfig(
                temperature=self._temperature,
                response_mime_type="application/json",
            ),
        )
        return self._client


class GeminiExtractionError(Exception):
    """Raised when Gemini metadata extraction fails after all retries."""
