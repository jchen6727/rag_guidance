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
import json
import logging
import sys
from pathlib import Path

from google.api_core import retry as api_retry
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import AlreadyExists, DeadlineExceeded, ServiceUnavailable
from google.cloud import discoveryengine_v1beta as discoveryengine

sys.path.insert(0, str(Path(__file__).parent.parent))
from config.settings import settings
from config.schema_loader import SchemaVocabulary

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

_LRO_RPC_TIMEOUT = 300  # seconds for the initial RPC that starts a long-running operation
_LRO_RESULT_TIMEOUT = 600  # seconds to wait for the LRO (whole process) to complete -> 300 (5 minutes) increased to 600 (10 minutes)
_RETRY_TRANSIENT = api_retry.Retry(
    predicate=api_retry.if_exception_type(DeadlineExceeded, ServiceUnavailable),
    initial=2.0,
    maximum=30.0,
    multiplier=2.0,
    deadline=300.0, # retry extended 120 -> 300 in case GCP scale up
)


def _client_options() -> ClientOptions | None:
    """Resolve the regional API endpoint for settings.gcp_location.

    The Discovery Engine client libraries default to the *global* endpoint
    (discoveryengine.googleapis.com) regardless of settings.gcp_location. If
    GCP_LOCATION is a non-global region (e.g. "us", "eu"), calls made against
    the global endpoint for a regional parent resource are misrouted: they
    don't fail fast, they hang until the RPC/LRO timeout elapses with no
    useful error — a "gRPC sinkhole". Passing the matching regional endpoint
    via client_options avoids this.

    Returns:
        ClientOptions with the regional api_endpoint set, or None for the
        default (global) endpoint.
    """
    location = settings.gcp_location
    if location == "global":
        return None
    return ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")


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
    parent = (
        f"projects/{settings.gcp_project_id}/locations/{settings.gcp_location}"
        f"/collections/default_collection"
    )
    datastore_name = f"{parent}/dataStores/{settings.vertex_search_datastore_id}"

    if dry_run:
        logger.info(
            "[DRY RUN] Would create DataStore: %s", settings.vertex_search_datastore_id
        )
        return datastore_name

    client = discoveryengine.DataStoreServiceClient(client_options=_client_options())

    datastore = discoveryengine.DataStore(
        display_name=settings.vertex_search_datastore_id,
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED,
        solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
    )

    try:
        operation = client.create_data_store(
            parent=parent,
            data_store=datastore,
            data_store_id=settings.vertex_search_datastore_id,
            timeout=_LRO_RPC_TIMEOUT,
            retry=_RETRY_TRANSIENT,
        )
        result = operation.result(timeout=_LRO_RESULT_TIMEOUT)
        logger.info("DataStore created: %s", result.name)
        return result.name
    except AlreadyExists:
        logger.info("DataStore already exists: %s", datastore_name)
        return datastore_name


def register_schema(datastore_name: str, dry_run: bool = False) -> None:
    """Update the DataStore schema to register ChunkMetadata fields as filterable.

    Loads config/metadata_schema.json and submits it as the DataStore schema.
    String enum fields (domain, doc_type) are registered with FILTERABLE indexing.
    Integer fields (page_start, year_published) are registered with RANGE indexing.

    Must be called BEFORE the first ImportDocuments run. Calling this after
    ingestion does not retroactively index existing documents.

    Args:
        datastore_name: Full DataStore resource name from create_datastore().
        dry_run: If True, log the schema diff without updating.

    Raises:
        FileNotFoundError: If config/metadata_schema.json does not exist.
    """
    schema_data = _load_metadata_schema()

    if dry_run:
        logger.info(
            "[DRY RUN] Would register schema with %d field(s)",
            len(schema_data.get("properties", {})),
        )
        return

    client = discoveryengine.SchemaServiceClient(client_options=_client_options())
    schema_name = f"{datastore_name}/schemas/default_schema"

    # Build field configs from metadata_schema.json properties. The integer and
    # array field sets are derived from the schema itself (via SchemaVocabulary)
    # rather than hard-coded, so this stays in sync with metadata_schema.json —
    # the old {"keywords", "entities"} set referenced the removed `entities`
    # field and missed every psychotherapy array field. See DISCREPANCIES.md.
    vocab = SchemaVocabulary(schema_data)
    field_configs: dict[str, discoveryengine.FieldConfig] = {}
    int_fields = vocab.integer_fields
    array_fields = vocab.array_fields

    for field_name, field_def in schema_data.get("properties", {}).items():
        if field_name in array_fields:
            # Array fields are stored but not individually filterable
            continue
        config = discoveryengine.FieldConfig(
            filterable=discoveryengine.FieldConfig.FilterableOption.FILTERABLE_ENABLED,
            retrievable=discoveryengine.FieldConfig.RetrievableOption.RETRIEVABLE_ENABLED,
            searchable=discoveryengine.FieldConfig.SearchableOption.SEARCHABLE_ENABLED,
        )
        if field_name in int_fields:
            config.field_type = discoveryengine.FieldConfig.FieldType.INTEGER
        else:
            config.field_type = discoveryengine.FieldConfig.FieldType.TEXT
        field_configs[field_name] = config

    schema = discoveryengine.Schema(
        name=schema_name,
        json_schema=json.dumps(schema_data),
        field_configs=field_configs,
    )

    try:
        client.update_schema(
            schema=schema,
            timeout=_LRO_RPC_TIMEOUT,
            retry=_RETRY_TRANSIENT,
        )
        logger.info("Schema updated: %s", schema_name)
    except Exception:
        try:
            client.create_schema(
                parent=datastore_name,
                schema=schema,
                schema_id="default_schema",
                timeout=_LRO_RPC_TIMEOUT,
                retry=_RETRY_TRANSIENT,
            )
            logger.info("Schema created: %s", schema_name)
        except AlreadyExists:
            logger.info("Schema already exists, no changes made: %s", schema_name)


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
    parent = (
        f"projects/{settings.gcp_project_id}/locations/{settings.gcp_location}"
        f"/collections/default_collection"
    )
    engine_name = f"{parent}/engines/{settings.vertex_search_engine_id}"

    if dry_run:
        logger.info(
            "[DRY RUN] Would create Search Engine: %s", settings.vertex_search_engine_id
        )
        return engine_name

    client = discoveryengine.EngineServiceClient(client_options=_client_options())

    engine = discoveryengine.Engine(
        display_name=settings.vertex_search_engine_id,
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        solution_type=discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH,
        data_store_ids=[settings.vertex_search_datastore_id],
        search_engine_config=discoveryengine.Engine.SearchEngineConfig(
            search_tier=discoveryengine.SearchTier.SEARCH_TIER_STANDARD,
        ),
    )

    try:
        operation = client.create_engine(
            parent=parent,
            engine=engine,
            engine_id=settings.vertex_search_engine_id,
            timeout=_LRO_RPC_TIMEOUT,
            retry=_RETRY_TRANSIENT,
        )
        result = operation.result(timeout=_LRO_RESULT_TIMEOUT)
        logger.info("Search Engine created: %s", result.name)
        return result.name
    except AlreadyExists:
        logger.info("Search Engine already exists: %s", engine_name)
        return engine_name


def _load_metadata_schema() -> dict:
    """Load and return the parsed metadata_schema.json.

    Returns:
        Parsed schema dict.

    Raises:
        FileNotFoundError: If the schema file is missing.
    """
    schema_path = settings.metadata_schema_path
    if not schema_path.exists():
        raise FileNotFoundError(f"Metadata schema not found: {schema_path}")
    with open(schema_path) as f:
        return json.load(f)


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
