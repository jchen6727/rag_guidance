"""
Ingestion package — PDF watching, extraction, chunking, metadata generation,
GCS upload, and Vertex AI Search indexing.

Typical call order for a single document:
    extractor  -> ExtractedDocument
    chunker    -> list[Chunk]
    metadata_gen (per chunk) -> ChunkMetadata attached to each Chunk
    uploader   -> GCS URIs (PDF + chunk JSONL)
    indexer    -> Vertex AI Search import operation
"""

from ingestion.watcher import CorpusWatcher
from ingestion.extractor import PDFExtractor
from ingestion.chunker import ContextAwareChunker
from ingestion.metadata_gen import MetadataGenerator
from ingestion.uploader import GCSUploader
from ingestion.indexer import VertexSearchIndexer

__all__ = [
    "CorpusWatcher",
    "PDFExtractor",
    "ContextAwareChunker",
    "MetadataGenerator",
    "GCSUploader",
    "VertexSearchIndexer",
]
