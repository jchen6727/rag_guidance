"""
One-time provisioning script for Vertex AI Search resources.

Run this ONCE before any ingestion. Creates:
  1. An unstructured DataStore (enterprise edition for semantic search)
  2. Registers the ChunkMetadata schema with filterable attributes
  3. Creates a Search Engine backed by the DataStore

CAUTION:
  - DataStore region is immutable after creation. Confirm GCP_LOCATION before running.
  - Schema changes after ingestion require a full re-import (see issues.md P3).
  - This script is IDEMPOTENT: safe to re-run; existing resources are detected
    and skipped rather than recreated.

Usage:
    python scripts/setup_vertex_search.py [--dry-run]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from google.cloud import discoveryengine_v1beta as discoveryengine
from google.api_core.exceptions import AlreadyExists

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def create_datastore(dry_run: bool = False) -> str:
    """Create the unstructured DataStore for chunk documents.

    Uses enterprise_edition=True to enable semantic (vector) search.
    FULL content level stores the chunk text for snippet extraction.

    Args:
        dry_run: If True, log what would be created without calling the API.

    Returns:
        Full DataStore resource name string.

    Raises:
        google.api_core.exceptions.GoogleAPIError: On API failure.
    """
    raise NotImplementedError


def register_schema(datastore_name: str, dry_run: bool = False) -> None:
    """Update the DataStore schema to register ChunkMetadata fields as filterable.

    Loads config/metadata_schema.json and converts each property into a
    FieldConfig with FILTERABLE and SEARCHABLE attributes.

    String enum fields (domain, doc_type) are registered with EXACT_SEARCH
    indexing mode. Integer fields (page_start, year_published) are registered
    with RANGE indexing mode.

    Must be called BEFORE the first ImportDocuments run. Calling this after
    ingestion does not retroactively index existing documents.

    Args:
        datastore_name: Full DataStore resource name from create_datastore().
        dry_run: If True, log the schema diff without updating.

    Raises:
        FileNotFoundError: If config/metadata_schema.json does not exist.
    """
    raise NotImplementedError


def create_search_engine(datastore_name: str, dry_run: bool = False) -> str:
    """Create a Search Engine backed by the DataStore.

    Configures the engine for:
      - GENERIC vertical (suitable for unstructured documents)
      - search_tier = STANDARD (upgrade to ENTERPRISE for advanced features)
      - Hybrid search (semantic + keyword) via serving config

    Args:
        datastore_name: Full DataStore resource name.
        dry_run: If True, log what would be created without calling the API.

    Returns:
        Full Search Engine resource name string.
    """
    raise NotImplementedError


def _load_metadata_schema() -> dict:
    """Load and return the parsed metadata_schema.json.

    Returns:
        Parsed schema dict.

    Raises:
        FileNotFoundError: If the schema file is missing.
    """
    raise NotImplementedError


def main() -> None:
    """Entry point: parse arguments and run provisioning in order."""
    parser = argparse.ArgumentParser(
        description="Provision Vertex AI Search resources for the RAG pipeline."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Log what would be created without making API calls.",
    )
    args = parser.parse_args()

    logger.info("Validating settings...")
    settings.validate_all()

    logger.info("Step 1/3: Creating DataStore...")
    datastore_name = create_datastore(dry_run=args.dry_run)

    logger.info("Step 2/3: Registering schema...")
    register_schema(datastore_name, dry_run=args.dry_run)

    logger.info("Step 3/3: Creating Search Engine...")
    engine_name = create_search_engine(datastore_name, dry_run=args.dry_run)

    logger.info("Done. Resources:")
    logger.info("  DataStore: %s", datastore_name)
    logger.info("  Engine:    %s", engine_name)
    if args.dry_run:
        logger.info("(dry-run: no resources were created)")


if __name__ == "__main__":
    main()
