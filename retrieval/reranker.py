"""
Optional LLM-based re-ranker for retrieved search results.

Vertex AI Search returns results ranked by its own relevance model. This
module provides an optional second-pass re-ranking step using Gemini to
improve ordering for domain-specific or nuanced queries.

Trade-off: adds ~1–2s latency and one Gemini call per query. Enable only
when retrieval precision measurements show it's worth the cost.

Typical usage:
    reranker = LLMReranker(model_name="gemini-1.5-flash")   # flash is sufficient here
    reranked = reranker.rerank(query, results, top_n=5)
"""

from __future__ import annotations

import logging
from typing import Optional

import google.generativeai as genai

from models import SearchResult

logger = logging.getLogger(__name__)


class LLMReranker:
    """
    Re-ranks a list of SearchResults using a Gemini model.

    Presents the query and retrieved passages to Gemini and asks it to order
    them by relevance. Returns the top_n results in the new order.
    """

    def __init__(
        self,
        model_name: str = "gemini-1.5-flash",
        temperature: float = 0.0,
    ) -> None:
        """
        Args:
            model_name: Gemini model to use for re-ranking. gemini-1.5-flash is
                        recommended (lower cost; re-ranking doesn't require deep
                        reasoning, only ordering).
            temperature: Sampling temperature. 0.0 for deterministic ordering.
        """
        self._model_name = model_name
        self._temperature = temperature
        self._client: Optional[genai.GenerativeModel] = None

    def rerank(
        self,
        query: str,
        results: list[SearchResult],
        top_n: int = 5,
    ) -> list[SearchResult]:
        """Re-rank retrieved results by relevance to the query using Gemini.

        If the Gemini call fails (network error, quota, parse error), falls back
        to returning the original results in their original order.

        Args:
            query: The original user query.
            results: Results from CorpusSearcher.search(), in original rank order.
            top_n: Number of results to return after re-ranking. Must be <= len(results).

        Returns:
            Up to top_n SearchResults in new relevance order. Falls back to
            original order if re-ranking fails.
        """
        raise NotImplementedError

    def _build_rerank_prompt(self, query: str, results: list[SearchResult]) -> str:
        """Build the prompt asking Gemini to rank the passages.

        Presents each passage as a numbered entry. Instructs the model to return
        only a JSON array of 1-based indices in descending relevance order.

        Example output instruction: "Return only: [3, 1, 5, 2, 4]"

        Args:
            query: User query.
            results: Candidate passages to rank.

        Returns:
            Full prompt string.
        """
        raise NotImplementedError

    def _parse_ranking(
        self, response_text: str, results: list[SearchResult]
    ) -> list[SearchResult]:
        """Parse Gemini's ranking response and reorder results accordingly.

        Expects a JSON array of 1-based result indices. Falls back to original
        order if the response cannot be parsed or contains out-of-range indices.

        Args:
            response_text: Raw text response from Gemini.
            results: The original results list (indexed 1-based in the prompt).

        Returns:
            Re-ordered list of SearchResults. May be shorter than the original
            if Gemini returns fewer indices than requested.
        """
        raise NotImplementedError

    def _get_client(self) -> genai.GenerativeModel:
        """Lazy-initialize and return the Gemini model client.

        Returns:
            Configured GenerativeModel instance.
        """
        raise NotImplementedError
