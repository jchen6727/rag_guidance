# Changelog

---

## 2026-07-09 (f)

### Changed

- **Switched the Discovery Engine client from `discoveryengine_v1beta` to `discoveryengine_v1`** in all four files that import it: `scripts/setup_vertex_search.py`, `ingestion/indexer.py`, `retrieval/searcher.py`, and `scripts/verify_context.py` (the last also carried a `# why v1beta?` comment, now resolved). Also updated the stale `discoveryengine_v1beta` reference in `ingestion/README.md`.

  **Reason for the switch.** No feature in this project requires the beta surface. Every Discovery Engine symbol the code touches — `DataStore`, `Schema`, `Engine`, `IndustryVertical`, `SolutionType`, `SearchTier`, `ImportDocumentsRequest`, `GcsSource`, `ImportDocumentsMetadata`, `ListDocumentsRequest`, `DocumentServiceClient`, `DataStoreServiceClient`, `SchemaServiceClient`, `EngineServiceClient`, `SearchServiceClient`, `SearchResponse` — exists identically in `discoveryengine_v1` (verified against the installed 0.20.0). The provisioning + ingestion path (DataStore/Schema/Engine creation, `ImportDocuments`, `ListDocuments`) and the search path (`SearchServiceClient.search`) are all GA operations. No `.md` documented any rationale for choosing v1beta; it appears to have been copied from a tutorial rather than chosen for a beta-only capability. Standardizing on the GA (`v1`) surface removes reliance on a preview API whose shape can change without notice.

  **IMPORTANT — this switch does NOT fix the reported `FieldConfig` error.** The premise that `discoveryengine.FieldConfig` is a v1-vs-v1beta difference is incorrect. `FieldConfig` does **not** exist in *either* `discoveryengine_v1` or `discoveryengine_v1beta` (0.20.0), and the `Schema` message in both versions carries only three fields — `name`, `struct_schema`, `json_schema` — with **no** `field_configs` field. The `register_schema()` block in `scripts/setup_vertex_search.py` that builds `discoveryengine.FieldConfig(...)` and passes `Schema(field_configs=...)` was written against a client API that never shipped; it raises `AttributeError` under both v1 and v1beta and would not be fixed by any version pin. Field-level indexing in Discovery Engine is expressed as annotations **inside** the `json_schema` document (per-property `retrievable` / `indexable` / `searchable` / `dynamicFacetable` booleans), not via a separate `FieldConfig` object. This is left **unresolved by this change** (see "Possible issues" below and DISCREPANCIES.md) because the task scoped the `FieldConfig` fix to the "v1beta is required" branch, which does not apply.

### Possible issues arising from the switch

- **`setup_vertex_search.py` still fails at the `FieldConfig` line.** As above, the dead `FieldConfig`/`field_configs` code is unchanged and still raises `AttributeError` when `register_schema()` runs (non-dry-run). The correct fix — emit the indexing annotations into the `json_schema` string and drop `FieldConfig` entirely — is a separate follow-up. Until then `create_datastore` and `create_search_engine` work, but schema registration does not.
- **Future query-path features may need beta.** The query path (`retrieval/searcher.py`, `generation/`) is still stubbed. Some Discovery Engine capabilities that were preview-only at various points (e.g. certain `SearchRequest.ContentSearchSpec` summary/extractive options, the conversational `answer`/grounded-generation methods, chunk-mode search) are richer or only present under `v1beta`. If the implemented query path needs one of those, that specific client (only) may need to re-import `discoveryengine_v1beta`; the ingestion/provisioning clients should stay on `v1`. Generation is expected to call Gemini directly (`google.generativeai`), not the Discovery Engine `answer` API, so this is unlikely to bite.
- **No wire/behavior change** for the operations actually used: DataStore/Schema/Engine resources, `ImportDocuments` semantics, filter (AIP-160) syntax, and regional endpoint hosts are identical across v1 and v1beta. Enum values and resource-name formats are unchanged, so no re-provisioning is required.

---

## 2026-07-09 (e)

### Fixed

- **`scripts/setup_vertex_search.py`** — `DataStoreServiceClient()`, `SchemaServiceClient()`, and `EngineServiceClient()` were constructed with no `client_options`, so they always talked to the global Discovery Engine endpoint (`discoveryengine.googleapis.com`) regardless of `settings.gcp_location`. When `GCP_LOCATION` is a non-global region (e.g. `us`, `eu`), requests for that regional parent resource are misrouted and don't fail fast — they hang until the RPC/LRO timeout (up to 600s) with no useful error (a "gRPC sinkhole"). Added `_client_options()`, which resolves `{location}-discoveryengine.googleapis.com` for non-global locations (`None`/default for `global`), and passed it to all three service clients.
- **`scripts/preflight_check.sh`** — added a new §5 check that resolves the same endpoint `setup_vertex_search.py` will use for `GCP_LOCATION` and verifies (a) the location is a recognized Discovery Engine location (`global`, `us`, `eu`) and (b) the resulting endpoint hostname is resolvable, so an invalid/unreachable `GCP_LOCATION` is caught in seconds instead of surfacing as a multi-minute hang inside `setup_vertex_search.py`. Old §5 (IAM permissions) renumbered to §6.

### TODO — other possible gRPC sinkholes found by static check of `scripts/*.py`

Same failure shape as above (a Discovery Engine gRPC client constructed/used without a location-matched endpoint, or with an invalid default location), not yet fixed:

- `ingestion/indexer.py:241` — `self._client = discoveryengine.DocumentServiceClient()` is constructed with no `client_options`, so it always targets the global endpoint even though `VertexSearchIndexer.__init__` accepts and stores a `location` (`self._location`, set at `ingestion/indexer.py:73`). Reached from two call sites in `scripts/`:
  - `scripts/batch_ingest.py:280` — `VertexSearchIndexer(..., location=settings.gcp_location, ...)`
  - `scripts/purge_datastore.py:175` — `VertexSearchIndexer(..., location=settings.gcp_location, ...)`
  Needs the same `_client_options()`-style fix as `setup_vertex_search.py`, applied inside `ingestion/indexer.py:_get_client()`.
- `scripts/verify_context.py:21` — `verify_discovery_engine_api(project_id: str, location: str = "us-central1")` defaults `location` to `"us-central1"`, which is not a valid Discovery Engine location (only `global`, `us`, `eu` are supported). The function's own `client_options` logic (`verify_context.py:25-29`) is otherwise correct, but with the bad default it builds a nonexistent endpoint (`us-central1-discoveryengine.googleapis.com`) and the `list_data_stores` call at `verify_context.py:37` will sinkhole. The unguarded module-level call at `verify_context.py:68` (`verify_discovery_engine_api(project_id="jchen-6727")`) exercises this default and executes on import.

---

## 2026-07-09 (d)

### Fixed

- **`scripts/preflight_check.sh`** — the IAM permissions check (§5) called `gcloud projects test-iam-permissions`, which does not exist as a gcloud command; the script always fell through to its `2>/dev/null` failure path and silently reported every required permission as missing. Replaced with a direct `curl` POST to the Cloud Resource Manager `testIamPermissions` REST API (`cloudresourcemanager.googleapis.com/v1/projects/{id}:testIamPermissions`), authenticated with the same ADC access token the Python code uses, with the response parsed via `python3 -c` (repo already requires Python). The check now distinguishes network/curl failure, non-200 HTTP responses, and unparseable JSON from an actual missing-permission result, each with its own `fail`/`fix` message instead of collapsing into one generic failure.
- **`scripts/preflight_check.sh`** — audited every `2>/dev/null` in the script for silent failure. §4 (`gcloud services list`) previously suppressed all stderr and treated a failed/permission-denied call identically to "no APIs enabled," so every required API was misreported as not enabled instead of surfacing the real cause. §1 (`gcloud auth list`), §2 (`gcloud config get-value project`), and §3 (`gcloud billing projects describe`) had the same issue — errors indistinguishable from the "true" negative case (no active account / no matching project / billing disabled). All four now capture stderr, check the command's exit code explicitly, and report a distinct `fail` message with the raw gcloud error when the command itself failed, only falling back to the original negative-result message when the command succeeded but returned the "false" case.

---

## 2026-07-09 (c)

### Added

- **`scripts/preflight_check.sh`** — new gcloud-based preflight check for `scripts/setup_vertex_search.py`. Verifies (in order) that the gcloud CLI is installed and authenticated, Application Default Credentials are set up, `GCP_PROJECT_ID` exists and matches the active gcloud config project, billing is enabled, the required APIs (`discoveryengine.googleapis.com`, `storage.googleapis.com`, `aiplatform.googleapis.com`) are enabled, and the active identity holds the IAM permissions `setup_vertex_search.py` needs (checked via `gcloud projects test-iam-permissions`, so it correctly accounts for permissions granted through group membership, not just direct role bindings). On any failure it prints the exact `gcloud` command to fix that specific issue and keeps checking the rest, so a single run surfaces every outstanding problem instead of stopping at the first one. Complements the existing Python-based `scripts/verify_context.py` (API reachability check via the Discovery Engine client) rather than replacing it — this script checks project/billing/IAM state ahead of time using the `gcloud` CLI directly, which doesn't require the API client libraries or credentials to already be fully working.

### Documentation updates

- **`ingestion/INGESTION_TUTORIAL.md`** — inserted a new "Step 2 — Preflight check" between environment configuration and resource provisioning, instructing readers to run `scripts/preflight_check.sh` before `setup_vertex_search.py`. All subsequent steps ("Provision GCP resources" through "Ingest a single PDF") renumbered up by one (old Step 2–6 → Step 3–7).

---

## 2026-07-09 (b)

### Fixed

- **`scripts/setup_vertex_search.py`** — `create_data_store()` and `create_engine()` failed with `google.api_core.exceptions.DeadlineExceeded: 504` because the initial gRPC calls used the library's default timeout (~60 s), which is too short for Vertex AI Search LRO-initiating RPCs on cold starts or under load. Added explicit `timeout=300` and `google.api_core.retry.Retry` with exponential backoff (2 s → 30 s, 120 s deadline) on `DeadlineExceeded` and `ServiceUnavailable` to all three provisioning steps (`create_data_store`, `update_schema`/`create_schema`, `create_engine`). Also raised `operation.result()` timeout from 120 s to 300 s for `create_data_store` and `create_engine`.
- **`ingestion/indexer.py`** — applied the same `timeout` + `Retry` treatment to `import_documents()`, `get_operation()` (LRO polling), `delete_document()`, and `list_documents()`, which were all using default gRPC deadlines and had no retry logic for transient failures. These calls are exercised by `scripts/batch_ingest.py` and `scripts/purge_datastore.py`.

---

## 2026-07-09

### Added

- **`config/schema_loader.py`** — `SchemaVocabulary`, a structured loader that parses `config/metadata_schema.json` (the authoritative psychotherapy RTA/ASA schema) and exposes its enums, array-field membership, nullability, defaults, required-field list, and a schema-driven `coerce()` method. This makes the metadata controlled vocabulary single-sourced from the JSON schema instead of being duplicated in Python.
- **`tests/test_schema_loader.py`** — coverage for loading, introspection, defaults, and coercion (including that removed fields `entities`/`evidence_level` are absent and that unknown keys are dropped).

### Changed

- **`ingestion/metadata_gen.py`** — removed the hard-coded biomedical constants `_VALID_DOMAINS`, `_VALID_DOC_TYPES`, and `_VALID_EVIDENCE_LEVELS`. `_validate_and_coerce()` now delegates to `SchemaVocabulary.coerce()` (schema-driven enum/array/integer coercion; drops keys not in the schema). `_build_extraction_prompt()` now emits a schema-derived enum legend and RTA/ASA extraction guidance (domain-vs-modality, missingness inference, patient-facing exclusion) from the schema `notes`. `_fallback_extraction()` no longer references the removed fields.
- **`models.py`** — `ChunkMetadata` rewritten from the old biomedical model to mirror all 37 psychotherapy schema fields with schema-aligned defaults; removed `entities` and `evidence_level` per `metadata_schema.json` `notes.removed_fields`.
- **`scripts/setup_vertex_search.py`** — `int_fields`/`array_fields` for schema registration are now derived from `SchemaVocabulary` instead of the stale hard-coded `{"keywords", "entities"}` set (which referenced the removed `entities` field and missed every psychotherapy array field).
- **`tests/test_metadata_gen.py`** — generator fixture now loads the real `config/metadata_schema.json` (the empty placeholder schema no longer exercises schema-driven coercion); sample Gemini response uses psychotherapy values and drops `entities`.

### Documentation updates

- **`DISCREPANCIES.md`** — "Metadata schema vs code" bullets marked `#DONE`; added an "Issues encountered during implementation" list (array fields still unregistered as filterable, `doc_type` `""` sentinel, relaxed `required` semantics, `domain` coercion vs persona fallback, deferred `searcher._parse_metadata`).
- **`CLAUDE.md`** — Metadata Generation section and Configuration table note that the controlled vocabulary is loaded from `metadata_schema.json` via `config/schema_loader.py`.

---

## 2026-06-16

### Changed

- **`CorpusWatcher` renamed to `CorpusScanner`; `watcher.py` renamed to `scanner.py`.** `CorpusScanner.scan()` (via `scripts/batch_ingest.py`) is the canonical ingestion path. Observer-based continuous monitoring removed.

### Documentation updates

- **`ingestion/scanner.py`**: Module and class docstrings updated to `CorpusScanner`/`scan()` nomenclature; dead `_observer` attribute removed.
- **`ingestion/__init__.py`**: Import updated to `from ingestion.scanner import CorpusScanner`; package docstring updated.
- **`ingestion/README.md`**: Pipeline diagram entry point updated to `CorpusScanner.scan()`; `__init__.py` export list updated; `scanner.py` section documents `CorpusScanner` only.
- **`ingestion/requirements.txt`**: `watchdog` noted as excluded (not required for `scan()`).
- **`CLAUDE.md`**: Ingest path updated to `CorpusScanner.scan()` via `batch_ingest.py`; observer references removed.
- **`structure.md`**: Data flow diagram, directory layout, and component §1 updated to `scanner.py`/`CorpusScanner.scan()`.
- **`caveats.md`** §5: Watchdog infrastructure bullets removed; scanner-based approach is the only described path.
- **`issues.md`**: `#ALTERNATE` section retitled "One-Time Corpus Scan (Chosen Primary Pattern)"; observer/watcher references removed.
- **`requirements.txt`**: Watchdog section marked optional.
- **`RAGGuidance.lean`**: `catchupScan` renamed to `corpusScan`; `CorpusWatcher` references updated to `CorpusScanner.scan()`.

---

## 2026-06-08

### Added

- **`ingestion/README.md`** — per-file documentation of the ingestion package: pipeline diagram (`corpus/ PDF → watcher → extractor → chunker → metadata_gen → uploader → indexer → Vertex AI Search`), class/method tables, internal flow descriptions, data type ownership table, and configuration map.

- **`ingestion/requirements.txt`** — scoped dependency list covering only `ingestion/*.py` direct imports. Excludes `google-cloud-aiplatform` (query/generation path only), `tqdm`/`click` (scripts only), and pytest. Includes a note that `watchdog` is not required when using the `#ALTERNATE` one-time scan path.

- **`ingestion/extractor.py`** — full implementation of `PDFExtractor`:
  - `extract()`: chooses pdfplumber or Document AI based on `use_document_ai` flag and text-layer quality check; falls back gracefully if Document AI is unconfigured.
  - `_has_text_layer()`: avg chars/page heuristic against `min_text_chars_per_page`.
  - `_extract_with_pdfplumber()`: deferred import, page-by-page extraction via `_parse_pdfplumber_page`.
  - `_extract_with_document_ai()`: streams request bytes to the configured processor; reconstructs per-page text from `text_anchor.text_segments` offsets into the flat `document.text` string.
  - `_parse_pdfplumber_page()`: extracts text, tables, and figure presence.
  - `_extract_tables()`: uses `page.find_tables()` to capture both row data and bounding boxes in `{"rows": ..., "bbox": ...}` format.
  - `_compute_doc_id()`: SHA-256 hex digest of PDF bytes, streamed in 64 KB chunks; added as a private helper (not in original stub) since `extract()` requires a stable `doc_id` before constructing `ExtractedDocument`.
  - `ExtractionError`: defined in module (referenced in stub docstrings but never declared).

### Documentation updates

- **`#ALTERNATE` — one-time corpus scan** added across five files:
  - `ingestion/README.md`: callout block under `watcher.py` with minimal usage snippet and deployment scenarios.
  - `CLAUDE.md`: inline paragraph in the Architecture / Ingest path section.
  - `issues.md`: full `#ALTERNATE` entry at the same level as P1–P5, covering the operational problem with the continuous watcher, how `catchup_scan()` satisfies the alternate path, and the human judgment call (latency tolerance is a product decision, not a technical one).
  - `caveats.md`: bullet appended to the watchdog caveat in §5, cross-referencing `issues.md #ALTERNATE`.
  - `structure.md`: paragraph appended to component §1 (Watcher).
