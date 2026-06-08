"""
Vertex AI Search (Discovery Engine) query wrapper.

Wraps the SearchService with a clean interface for hybrid (semantic + keyword)
search, metadata filter expressions, and result deserialization into SearchResult
objects that carry both the chunk text and its ChunkMetadata.

Filter expressions use the AIP-160 syntax supported by Discovery Engine, e.g.:
    domain = "cardiology" AND doc_type = "clinical_guideline"

See caveats.md §1 (Search Behavior) for filter expression limitations and
the enterprise-edition requirement for semantic search.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from google.cloud import discoveryengine_v1beta as discoveryengine

from models import ChunkMetadata, SearchResult

logger = logging.getLogger(__name__)

_DEFAULT_TOP_K = 8
_MAX_TOP_K = 100


@dataclass
class SearchFilter:
    """Optional metadata filters applied to a search query.

    All non-None fields are combined with AND in the filter expression.
    Pass None for a field to omit it from the filter.
    """

    domain: Optional[str] = None
    subdomain: Optional[str] = None
    doc_type: Optional[str] = None
    year_published_min: Optional[int] = None
    year_published_max: Optional[int] = None
    custom_expression: Optional[str] = None
    """If set, overrides all other fields and is passed directly as the filter string."""


class CorpusSearcher:
    """
    Queries a Vertex AI Search engine and returns typed SearchResult objects.

    Usage:
        searcher = CorpusSearcher(
            project_id="my-project",
            location="global",
            engine_id="my-search-engine",
        )
        results = searcher.search("beta blockers in heart failure", top_k=8)
    """

    def __init__(
        self,
        project_id: str,
        location: str,
        engine_id: str,
    ) -> None:
        """
        Args:
            project_id: GCP project ID.
            location: Search engine location ("global" or "us"). Must match
                      the DataStore region — see caveats.md §1.
            engine_id: The Search Engine resource ID (not the full resource name).
        """
        self._project_id = project_id
        self._location = location
        self._engine_id = engine_id
        self._client: Optional[discoveryengine.SearchServiceClient] = None

    @property
    def _serving_config(self) -> str:
        """Return the fully-qualified serving config resource name."""
        return (
            f"projects/{self._project_id}/locations/{self._location}"
            f"/collections/default_collection/engines/{self._engine_id}"
            "/servingConfigs/default_config"
        )

    def search(
        self,
        query: str,
        top_k: int = _DEFAULT_TOP_K,
        filters: Optional[SearchFilter] = None,
        min_relevance_score: float = 0.0,
    ) -> list[SearchResult]:
        """Execute a search query and return ranked results.

        Builds the SearchRequest with the query, optional filter expression,
        and page size, then deserializes each result into a SearchResult.

        Args:
            query: Free-text search query.
            top_k: Maximum number of results to return. Capped at _MAX_TOP_K (100).
            filters: Optional metadata filters. If None, no filter is applied.
            min_relevance_score: Filter out results with score below this threshold.
                                 Set to 0.0 to return all results from the API.

        Returns:
            List of SearchResult objects in descending relevance order.
            May be shorter than top_k if fewer results meet the score threshold.

        Raises:
            google.api_core.exceptions.GoogleAPIError: On API request failure.
        """
        raise NotImplementedError

    def _build_filter_expression(self, filters: SearchFilter) -> str:
        """Construct an AIP-160 filter string from a SearchFilter.

        If filters.custom_expression is set, returns it directly.
        Otherwise combines non-None fields with AND.

        Example output: 'domain = "cardiology" AND doc_type = "clinical_guideline"'

        Args:
            filters: SearchFilter with field values to include.

        Returns:
            Filter expression string, or "" if no filters are active.
        """
        raise NotImplementedError

    def _parse_result(
        self, result: discoveryengine.SearchResponse.SearchResult
    ) -> SearchResult:
        """Deserialize a Discovery Engine SearchResult proto into a SearchResult.

        Extracts:
          - Document ID from result.document.id
          - Snippet/chunk text from result.document.derived_struct_data or
            result.document.struct_data
          - Relevance score from result.model_scores if present
          - Metadata from struct_data fields

        Args:
            result: Raw SearchResult proto from the API response.

        Returns:
            Typed SearchResult with metadata populated where available.
        """
        raise NotImplementedError

    def _parse_metadata(self, struct_data: dict) -> Optional[ChunkMetadata]:
        """Build a ChunkMetadata from the flat struct_data dict in a search result.

        Handles missing or malformed fields gracefully by using ChunkMetadata
        defaults. Does not raise on partial data.

        Args:
            struct_data: Flat dict of metadata fields from the DataStore document.

        Returns:
            ChunkMetadata instance, or None if struct_data is empty.
        """
        raise NotImplementedError

    def _get_client(self) -> discoveryengine.SearchServiceClient:
        """Lazy-initialize and return the Discovery Engine search service client.

        Returns:
            Authenticated SearchServiceClient.
        """
        raise NotImplementedError
