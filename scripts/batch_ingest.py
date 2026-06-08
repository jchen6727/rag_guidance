"""
Batch ingestion script — process all PDFs in corpus/ in one run.

Use this to populate a fresh DataStore from an existing corpus directory,
or to re-ingest specific files after a config change.

The script:
  1. Scans corpus/ for PDF files
  2. Skips files already in the ingestion manifest (unless --force)
  3. Runs the full pipeline per file: extract → chunk → metadata → upload → index
  4. Waits for each Vertex AI Search import operation before moving to the next file
  5. Writes a summary report on completion

Usage:
    python scripts/batch_ingest.py [--dry-run] [--force] [--domain DOMAIN] [--file FILE]

Examples:
    # Ingest all new PDFs in corpus/
    python scripts/batch_ingest.py

    # Re-ingest a specific file, overwriting existing index entries
    python scripts/batch_ingest.py --file corpus/cardiology_textbook.pdf --force

    # Preview what would be ingested without running
    python scripts/batch_ingest.py --dry-run
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import settings
from ingestion.extractor import PDFExtractor
from ingestion.chunker import ContextAwareChunker
from ingestion.metadata_gen import MetadataGenerator
from ingestion.uploader import GCSUploader
from ingestion.indexer import VertexSearchIndexer

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


def ingest_file(
    pdf_path: Path,
    extractor: PDFExtractor,
    chunker: ContextAwareChunker,
    metadata_gen: MetadataGenerator,
    uploader: GCSUploader,
    indexer: VertexSearchIndexer,
    dry_run: bool = False,
) -> dict:
    """Run the full ingestion pipeline for a single PDF.

    Steps in order:
      1. Compute doc_id (content hash)
      2. Extract text and structure from the PDF
      3. Chunk the extracted document
      4. Generate metadata for each chunk via Gemini
      5. Upload PDF and chunk JSONL to GCS
      6. Import chunks into Vertex AI Search
      7. Wait for import LRO completion

    Args:
        pdf_path: Absolute path to the PDF file.
        extractor: Initialized PDFExtractor.
        chunker: Initialized ContextAwareChunker.
        metadata_gen: Initialized MetadataGenerator.
        uploader: Initialized GCSUploader.
        indexer: Initialized VertexSearchIndexer.
        dry_run: If True, run through extract/chunk/metadata but skip GCS upload
                 and Vertex AI import.

    Returns:
        Summary dict with keys: file, doc_id, n_chunks, n_metadata_failures,
        gcs_pdf_uri, gcs_chunks_uri, import_success, import_failures, elapsed_s.
    """
    raise NotImplementedError


def scan_corpus(corpus_dir: Path, manifest_path: Path, force: bool = False) -> list[Path]:
    """Return PDF paths in corpus_dir that have not yet been ingested.

    Args:
        corpus_dir: Directory to scan for PDFs.
        manifest_path: Path to the ingestion manifest JSON.
        force: If True, return all PDFs regardless of manifest state.

    Returns:
        List of PDF paths to ingest, sorted alphabetically.
    """
    raise NotImplementedError


def print_summary(results: list[dict]) -> None:
    """Print a formatted ingestion summary table to stdout.

    Args:
        results: List of result dicts from ingest_file().
    """
    raise NotImplementedError


def main() -> None:
    """Parse arguments and run batch ingestion."""
    parser = argparse.ArgumentParser(description="Batch ingest PDFs into the RAG corpus.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Extract and chunk without uploading or indexing.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingest files already in the manifest.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=None,
        help="Ingest a single specific PDF file instead of scanning corpus/.",
    )
    args = parser.parse_args()

    settings.validate_all()

    extractor = PDFExtractor(
        use_document_ai=settings.use_document_ai,
        document_ai_processor_id=settings.document_ai_processor_id or "",
        project_id=settings.gcp_project_id,
    )
    chunker = ContextAwareChunker()
    metadata_gen = MetadataGenerator(
        model_name=settings.gemini_model_metadata,
        schema_path=settings.metadata_schema_path,
    )
    uploader = GCSUploader(
        bucket_name=settings.gcs_bucket_name,
        project_id=settings.gcp_project_id,
    )
    indexer = VertexSearchIndexer(
        project_id=settings.gcp_project_id,
        location=settings.gcp_location,
        datastore_id=settings.vertex_search_datastore_id,
    )

    if args.file:
        pdf_paths = [args.file]
    else:
        pdf_paths = scan_corpus(settings.corpus_dir, settings.manifest_path, args.force)

    logger.info("Found %d PDF(s) to ingest.", len(pdf_paths))
    if args.dry_run:
        logger.info("DRY RUN: upload and index steps will be skipped.")

    results = []
    for pdf_path in pdf_paths:
        logger.info("Processing: %s", pdf_path.name)
        result = ingest_file(
            pdf_path, extractor, chunker, metadata_gen, uploader, indexer,
            dry_run=args.dry_run,
        )
        results.append(result)

    print_summary(results)


if __name__ == "__main__":
    main()
