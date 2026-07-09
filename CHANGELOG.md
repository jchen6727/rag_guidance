# Changelog

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
