# Changelog

---

## 2026-06-16

### Changed

- **Primary ingestion pattern is now one-time corpus scan.** `CorpusWatcher.catchup_scan()` (via `scripts/batch_ingest.py`) replaces the continuous `watchdog` observer as the canonical ingestion path. The observer-based path (`CorpusWatcher.start()`) remains in the module for local development but is no longer the default.

### Documentation updates

- **`ingestion/watcher.py`**: Module docstring rewritten to lead with one-time scan usage; `CorpusWatcher` class docstring updated to show `catchup_scan()` as primary lifecycle; `start()` docstring notes it is the observer-based path only; `catchup_scan()` docstring drops "before the live observer starts" framing.
- **`ingestion/__init__.py`**: Package docstring updated to note `CorpusWatcher.catchup_scan()` as primary entry point.
- **`ingestion/README.md`**: Pipeline diagram entry point changed from `watcher.py` to `batch_ingest.py`; watcher.py section restructured with primary/optional usage split; `PDFEventHandler` demoted to optional row in class table; `watchdog` noted as not required for the primary path.
- **`ingestion/requirements.txt`**: Added comment explaining `watchdog` is excluded because it is not required for `catchup_scan()`.
- **`CLAUDE.md`**: Ingest path description updated from "triggered by watcher or batch script" to `CorpusWatcher.catchup_scan()` via `batch_ingest.py`; `#ALTERNATE` paragraph rewritten as the primary description.
- **`structure.md`**: Data flow diagram entry point updated; `watcher.py` directory comment updated; component §1 description rewritten as "Corpus Scanner"; watchdog APIs table entry marked optional.
- **`caveats.md`** §5: Bullet order reversed — one-time scan is now the lead recommendation; observer-based path noted as the non-fault-tolerant option.
- **`issues.md`** `#ALTERNATE` section: Renamed to "Chosen Primary Pattern"; decision noted; rationale and latency trade-off preserved as informational.
- **`requirements.txt`**: Watchdog section heading changed to "Filesystem Watching (optional)"; comment clarifies it is for the observer-based path only.

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
