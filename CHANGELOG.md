# Changelog

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
