"""
Vertex AI Search (Discovery Engine) DataStore indexer.

Imports chunk JSONL from GCS into the configured DataStore via the
ImportDocuments API. Import operations are asynchronous LROs (long-running
operations) — use wait_for_import() to poll until completion.

Important notes:
  - Schema must be registered (scripts/setup_vertex_search.py) BEFORE importing.
  - ImportDocuments is not atomic: partial success is possible. Always check
    ImportResult.failure_count after waiting.
  - Re-importing the same doc_id will create duplicate entries. Use
    delete_document() before re-importing updated documents.

See caveats.md §1 for full Vertex AI Search limitations.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from google.cloud import discoveryengine_v1beta as discoveryengine

from models import ImportResult

logger = logging.getLogger(__name__)

_POLL_INTERVAL_SECONDS = 15
_DEFAULT_TIMEOUT_SECONDS = 600


class VertexSearchIndexer:
    """
    Manages document import and deletion in a Vertex AI Search DataStore.

    Usage:
        indexer = VertexSearchIndexer(
            project_id="my-project",
            location="global",
            datastore_id="my-rag-datastore",
        )
        op_name = indexer.import_chunks("gs://bucket/chunks/abc123.jsonl", "abc123")
        result = indexer.wait_for_import(op_name)
    """

    def __init__(
        self,
        project_id: str,
        location: str,
        datastore_id: str,
    ) -> None:
        """
        Args:
            project_id: GCP project ID.
            location: DataStore location. Use "global" or "us" — must match
                      the region chosen at DataStore creation (immutable).
            datastore_id: The DataStore resource ID (not the full resource name).
        """
        self._project_id = project_id
        self._location = location
        self._datastore_id = datastore_id
        self._client: Optional[discoveryengine.DocumentServiceClient] = None

    @property
    def _datastore_name(self) -> str:
        """Return the fully-qualified DataStore resource name."""
        return (
            f"projects/{self._project_id}/locations/{self._location}"
            f"/collections/default_collection/dataStores/{self._datastore_id}"
        )

    def import_chunks(self, gcs_jsonl_uri: str, doc_id: str) -> str:
        """Submit a GCS-sourced import request and return the LRO operation name.

        Constructs a GcsSource pointing to the JSONL file and calls
        ImportDocuments with FULL reconciliation mode (safer for re-imports
        than INCREMENTAL — avoids partial state on retry).

        Args:
            gcs_jsonl_uri: Full gs:// URI to the chunk JSONL file,
                           e.g. "gs://bucket/chunks/abc123.jsonl".
            doc_id: The document ID (used for logging and error tracking only;
                    the DataStore document IDs come from the JSONL content).

        Returns:
            LRO operation name string (used with wait_for_import).

        Raises:
            google.api_core.exceptions.GoogleAPIError: On request failure.
        """
        raise NotImplementedError

    def wait_for_import(
        self,
        operation_name: str,
        poll_interval: int = _POLL_INTERVAL_SECONDS,
        timeout: int = _DEFAULT_TIMEOUT_SECONDS,
    ) -> ImportResult:
        """Poll an import LRO until completion or timeout.

        Logs progress at each poll interval. Returns an ImportResult with
        success/failure counts from the operation metadata.

        Args:
            operation_name: LRO name returned by import_chunks().
            poll_interval: Seconds between status checks.
            timeout: Maximum seconds to wait before raising TimeoutError.

        Returns:
            ImportResult with completed=True and populated counts.

        Raises:
            TimeoutError: If the operation does not complete within `timeout`.
            ImportError: If the operation completes with a terminal error status.
        """
        raise NotImplementedError

    def delete_document(self, chunk_id: str) -> None:
        """Delete a single document (chunk) from the DataStore by its ID.

        Use this before re-importing updated chunks to avoid duplicates.
        For bulk re-ingestion, use scripts/purge_datastore.py instead.

        Args:
            chunk_id: The DataStore document ID (same as Chunk.chunk_id).

        Raises:
            google.api_core.exceptions.NotFound: If the document does not exist.
        """
        raise NotImplementedError

    def list_documents(self, page_size: int = 100) -> list[str]:
        """List all document IDs currently in the DataStore.

        Handles pagination automatically. Useful for auditing or deduplication checks.

        Args:
            page_size: Number of documents per API page (max 1000).

        Returns:
            List of document ID strings.
        """
        raise NotImplementedError

    def _get_client(self) -> discoveryengine.DocumentServiceClient:
        """Lazy-initialize and return the Discovery Engine document service client.

        Returns:
            Authenticated DocumentServiceClient.
        """
        raise NotImplementedError

    def _parse_import_result(self, operation_metadata: dict) -> ImportResult:
        """Extract success/failure counts from a completed import operation's metadata.

        Args:
            operation_metadata: The metadata dict from the completed LRO.

        Returns:
            ImportResult with counts populated from metadata fields.
        """
        raise NotImplementedError
