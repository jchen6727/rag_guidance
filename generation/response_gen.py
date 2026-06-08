"""
Gemini-based response generation with grounding attribution.

Takes the assembled prompt from PromptBuilder and retrieved SearchResults,
calls Gemini, then extracts grounding attributions from the response metadata
to feed into CitationBuilder.

Grounding note (see caveats.md §2): Vertex AI grounding attributions are
approximate — they map to retrieved segments, not to individual sentences.
Page-level citations require custom reconstruction in citation_builder.py.
"""

from __future__ import annotations

import logging
from typing import Optional

import google.generativeai as genai

from models import Attribution, GeneratedResponse, SearchResult

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """
    Generates grounded responses from an assembled prompt using Gemini.

    Usage:
        generator = ResponseGenerator(model_name="gemini-1.5-pro")
        response = generator.generate(prompt, results, query=query, domain=domain)
    """

    def __init__(
        self,
        model_name: str = "gemini-1.5-pro",
        temperature: float = 0.2,
        max_output_tokens: int = 2048,
    ) -> None:
        """
        Args:
            model_name: Gemini model to use. gemini-1.5-pro is recommended for
                        clinical/scientific responses requiring nuanced reasoning.
            temperature: Sampling temperature. 0.0 = fully deterministic;
                         0.2 provides slight variation while remaining factual.
            max_output_tokens: Token ceiling for the generated response.
        """
        self._model_name = model_name
        self._temperature = temperature
        self._max_output_tokens = max_output_tokens
        self._client: Optional[genai.GenerativeModel] = None

    def generate(
        self,
        prompt: str,
        results: list[SearchResult],
        query: str = "",
        domain: str = "",
    ) -> GeneratedResponse:
        """Generate a grounded response and attach citations.

        Calls Gemini with the assembled prompt, extracts grounding attributions,
        then delegates citation building to CitationBuilder.

        Args:
            prompt: Full prompt string from PromptBuilder.build().
            results: The same SearchResults passed to PromptBuilder. Used by
                     CitationBuilder to look up page metadata for attributions.
            query: Original user query (stored on GeneratedResponse for logging).
            domain: Domain string (stored on GeneratedResponse for logging).

        Returns:
            GeneratedResponse with .text, .citations, and .attributions populated.
            If the Gemini call fails, raises; callers should handle GeminiError.
        """
        raise NotImplementedError

    def _call_gemini(
        self, prompt: str
    ) -> tuple[str, list]:
        """Send the prompt to Gemini and return (response_text, grounding_chunks).

        Configures generation_config with temperature and max_output_tokens.
        Extracts grounding_chunks from response.candidates[0].grounding_metadata
        if available.

        Args:
            prompt: Full assembled prompt string.

        Returns:
            Tuple of (generated_text, grounding_chunks_list).
            grounding_chunks_list is empty if no grounding metadata is returned.

        Raises:
            google.generativeai.types.BlockedPromptException: If content is blocked.
            RuntimeError: On unexpected API response structure.
        """
        raise NotImplementedError

    def _extract_grounding_attributions(
        self,
        response_text: str,
        grounding_chunks: list,
        results: list[SearchResult],
    ) -> list[Attribution]:
        """Map Gemini grounding chunks back to source SearchResult chunk IDs.

        Grounding chunks contain web_search or retrieval source references.
        For Vertex AI Search grounding, each chunk maps to a retrieved document.
        The mapping is approximate — see caveats.md §2.

        Args:
            response_text: The generated response text.
            grounding_chunks: Raw grounding_chunks list from the Gemini response.
            results: The original SearchResults (used to resolve chunk IDs by
                     matching snippet text to result text).

        Returns:
            List of Attribution objects. May be empty if grounding metadata is
            unavailable (e.g., when using non-grounded generation).
        """
        raise NotImplementedError

    def _get_client(self) -> genai.GenerativeModel:
        """Lazy-initialize and return the Gemini generative model client.

        Returns:
            Configured GenerativeModel instance.
        """
        raise NotImplementedError
