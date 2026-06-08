"""
Google Cloud Storage uploader for PDFs and chunk JSONL files.

Provides idempotent uploads by content-hashing the source PDF (SHA-256)
to produce a stable doc_id. The same PDF uploaded twice will produce the
same GCS paths and skip the upload if the object already exists.

GCS layout:
    gs://<bucket>/pdfs/<doc_id>.pdf
    gs://<bucket>/chunks/<doc_id>.jsonl   (one JSON object per line, one chunk per line)
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Optional

from google.cloud import storage

from models import Chunk, ChunkMetadata

logger = logging.getLogger(__name__)


class GCSUploader:
    """
    Uploads raw PDFs and serialized chunks to Google Cloud Storage.

    Usage:
        uploader = GCSUploader(bucket_name="my-rag-corpus", project_id="my-project")
        doc_id = uploader.compute_doc_id(pdf_path)
        pdf_uri = uploader.upload_pdf(pdf_path, doc_id)
        chunks_uri = uploader.upload_chunks(chunks, doc_id)
    """

    def __init__(self, bucket_name: str, project_id: str) -> None:
        """
        Args:
            bucket_name: GCS bucket name (must already exist; no auto-create).
            project_id: GCP project ID that owns the bucket.
        """
        self._bucket_name = bucket_name
        self._project_id = project_id
        self._client: Optional[storage.Client] = None

    def compute_doc_id(self, path: Path) -> str:
        """Compute the stable document ID as the SHA-256 hex digest of the PDF bytes.

        Reads the full file into memory. For very large PDFs (>500 MB) consider
        streaming the hash computation.

        Args:
            path: Path to the PDF file.

        Returns:
            64-character lowercase hex string.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        raise NotImplementedError

    def is_already_uploaded(self, doc_id: str) -> bool:
        """Return True if both the PDF and chunk JSONL objects exist in GCS.

        Used to skip re-upload without re-computing the doc_id. Checks blob
        existence via a metadata HEAD request (does not download data).

        Args:
            doc_id: SHA-256 doc ID to check.

        Returns:
            True if both gs://<bucket>/pdfs/<doc_id>.pdf and
            gs://<bucket>/chunks/<doc_id>.jsonl exist.
        """
        raise NotImplementedError

    def upload_pdf(self, local_path: Path, doc_id: str) -> str:
        """Upload the raw PDF to GCS.

        Skips the upload and returns the existing URI if is_already_uploaded(doc_id).
        Sets the GCS object's content_type to "application/pdf".

        Args:
            local_path: Local PDF path to upload.
            doc_id: The doc_id returned by compute_doc_id(local_path).

        Returns:
            GCS URI string: gs://<bucket>/pdfs/<doc_id>.pdf

        Raises:
            google.cloud.exceptions.GoogleCloudError: On upload failure.
        """
        raise NotImplementedError

    def upload_chunks(self, chunks: list[Chunk], doc_id: str) -> str:
        """Serialize chunks to JSONL and upload to GCS.

        Each line of the JSONL file is one serialized chunk. The format matches
        the Vertex AI Search unstructured document import schema.

        Args:
            chunks: List of chunks with .metadata populated.
            doc_id: Document ID (used to construct the GCS path).

        Returns:
            GCS URI string: gs://<bucket>/chunks/<doc_id>.jsonl

        Raises:
            ValueError: If any chunk is missing .metadata (not yet generated).
        """
        raise NotImplementedError

    def _serialize_chunk(self, chunk: Chunk) -> dict:
        """Serialize a Chunk to the Vertex AI Search import JSON format.

        The format must match the unstructured DataStore's registered schema.
        Key fields:
            id: chunk_id (used as the DataStore document ID)
            structData: all ChunkMetadata fields as a flat dict
            content: {"mimeType": "text/plain", "uri": ""}
            jsonData: chunk text

        Args:
            chunk: Chunk with populated metadata.

        Returns:
            Dict ready for JSON serialization to JSONL.

        Raises:
            ValueError: If chunk.metadata is None.
        """
        raise NotImplementedError

    def _gcs_pdf_path(self, doc_id: str) -> str:
        """Return the GCS object path (without gs://bucket/ prefix) for the PDF.

        Args:
            doc_id: Document SHA-256 ID.

        Returns:
            Object path string, e.g. "pdfs/abc123.pdf".
        """
        return f"pdfs/{doc_id}.pdf"

    def _gcs_chunks_path(self, doc_id: str) -> str:
        """Return the GCS object path for the chunk JSONL file.

        Args:
            doc_id: Document SHA-256 ID.

        Returns:
            Object path string, e.g. "chunks/abc123.jsonl".
        """
        return f"chunks/{doc_id}.jsonl"

    def _get_client(self) -> storage.Client:
        """Lazy-initialize and return the GCS client.

        Returns:
            Authenticated storage.Client instance.
        """
        raise NotImplementedError
