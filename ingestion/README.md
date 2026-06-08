# ingestion/

End-to-end pipeline for extracting, chunking, annotating, and indexing PDF documents into Vertex AI Search.

---

## Pipeline Overview

```
corpus/ PDF
    │
    ▼
watcher.py          CorpusWatcher detects new/modified PDFs
    │  pipeline_callback(path)
    ▼
extractor.py        PDFExtractor.extract(path) → ExtractedDocument
    │
    ▼
chunker.py          ContextAwareChunker.chunk(doc) → list[Chunk]
    │
    ▼
metadata_gen.py     MetadataGenerator.generate(chunk) → ChunkMetadata (per chunk)
    │                 attached to chunk.metadata
    ▼
uploader.py         GCSUploader.upload_pdf()    → gs://<bucket>/pdfs/<doc_id>.pdf
                    GCSUploader.upload_chunks() → gs://<bucket>/chunks/<doc_id>.jsonl
    │
    ▼
indexer.py          VertexSearchIndexer.import_chunks(jsonl_uri) → LRO op name
                    VertexSearchIndexer.wait_for_import(op_name) → ImportResult
    │
    ▼
Vertex AI Search DataStore (queryable)
```

The watcher triggers the pipeline on file events. The batch script (`scripts/batch_ingest.py`) drives the same pipeline without the watcher.

---

## Files

### `__init__.py`

Exports the six public classes in call order: `CorpusWatcher`, `PDFExtractor`, `ContextAwareChunker`, `MetadataGenerator`, `GCSUploader`, `VertexSearchIndexer`. No logic; import from here rather than the individual modules.

---

### `watcher.py`

**Purpose:** Monitor `corpus/` for new PDFs and dispatch them through the ingestion pipeline.

> **#ALTERNATE — One-time corpus scan (no watchdog)**
>
> Instead of starting a long-lived `Observer`, call `CorpusWatcher.catchup_scan()` directly and then exit. This performs a single pass over `corpus/`, calls `is_processed()` against the manifest for each PDF, and invokes the `pipeline_callback` only for files not yet recorded. No background thread, no `PDFEventHandler`, no signal handling required.
>
> ```python
> watcher = CorpusWatcher(corpus_dir, manifest_path, pipeline_fn)
> watcher._load_manifest()   # load existing state
> watcher.catchup_scan()     # process new files, update manifest
> # exit — no observer started
> ```
>
> This pattern is preferable for:
> - **CI/CD pipelines** — run ingestion as a one-shot job step, not a daemon
> - **Scheduled cron jobs** — trigger a scan on a timer rather than maintaining a persistent process
> - **Container deployments** — ephemeral containers where a blocking observer would prevent clean shutdown
> - **Environments where `watchdog` inotify limits are a concern** (each watched directory consumes a kernel inotify watch)
>
> The trade-off is latency: files added between scheduled runs are not processed until the next invocation, whereas the continuous watcher reacts within seconds. `scripts/batch_ingest.py` is the existing entry point that uses this pattern.

**Key classes:**

| Class | Role |
|---|---|
| `PDFEventHandler` | Watchdog `FileSystemEventHandler` subclass; filters for `.pdf` extensions and invokes a callback |
| `CorpusWatcher` | Owns the observer, the manifest, and the catch-up scan |

**Manifest:** A JSON file (`basename → doc_id`) that persists across restarts so already-processed files are skipped. Written atomically (temp-file + rename) on every update.

**Startup sequence:**
1. `_load_manifest()` — reads or creates the manifest file
2. `catchup_scan()` — processes any PDFs in `corpus/` absent from the manifest, alphabetically
3. Starts the watchdog `Observer` on `corpus/`
4. Blocks; `stop()` can be called from a signal handler

**Dependencies:** `watchdog`, `pathlib`, stdlib `json`; calls the `pipeline_callback` injected at construction (no direct import of other ingestion modules).

**Production note:** Replace with a GCS Eventarc trigger for cloud deployments — this watcher is not fault-tolerant across host restarts.

---

### `extractor.py`

**Purpose:** Convert a PDF file into an `ExtractedDocument` (list of `Page` objects with text and table data).

**Key class:** `PDFExtractor`

**Extraction strategy:**
- **Primary:** `pdfplumber` — layout-aware, handles multi-column text and tables.
- **Fallback:** Google Document AI OCR — used when pdfplumber yields fewer than `min_text_chars_per_page` average characters per page (scanned PDFs without a text layer).

**Public method:** `extract(path: Path) → ExtractedDocument`

| Private method | Purpose |
|---|---|
| `_has_text_layer(doc)` | Heuristic check: avg chars/page ≥ threshold → True |
| `_extract_with_pdfplumber(path)` | pdfplumber extraction path; sets `extraction_method = "pdfplumber"` |
| `_extract_with_document_ai(path)` | OCR path via Document AI; sets `extraction_method = "document_ai"` |
| `_parse_pdfplumber_page(page, page_num)` | Converts a pdfplumber page object to the internal `Page` dataclass |
| `_extract_tables(page)` | Returns table rows as `{"rows": [...], "bbox": tuple}` dicts |

**Dependencies:** `pdfplumber`, `google.cloud.documentai`, `models.ExtractedDocument`, `models.Page`

**Cost note:** Document AI OCR costs ~$1.50/1000 pages — gate behind `_has_text_layer`.

---

### `chunker.py`

**Purpose:** Split an `ExtractedDocument` into a list of `Chunk` objects suitable for embedding and retrieval.

**Key classes:**

| Class | Role |
|---|---|
| `ChunkerConfig` | Dataclass holding all tuning parameters |
| `ContextAwareChunker` | Two-pass chunking logic |

**ChunkerConfig fields:**

| Field | Default | Meaning |
|---|---|---|
| `max_tokens` | 512 | Hard ceiling per chunk |
| `min_tokens` | 64 | Fragments below this are merged with their neighbor |
| `overlap_tokens` | 64 | Token overlap between consecutive chunks for context continuity |
| `semantic_similarity_threshold` | 0.75 | Cosine similarity below which a sentence boundary becomes a chunk boundary |
| `embedding_model` | `all-MiniLM-L6-v2` | sentence-transformers model for semantic boundary detection |
| `header_patterns` | 3 regexes | Chapter/section headers, numbered sections, ALL CAPS |
| `skip_doc_types` | `front_matter`, `index`, `bibliography` | `doc_type` values excluded from output |

**Two-pass algorithm:**
1. **Structural pass** (`_structural_split`): Scan each page for lines matching `header_patterns`. Group pages into named sections; pre-header pages become `"preamble"`.
2. **Semantic pass** (`_semantic_split`): Within each section, embed sentences with sentence-transformers, find boundaries where adjacent-sentence cosine similarity drops below threshold, then merge spans respecting `max_tokens`/`min_tokens` and add overlap.

**Chunk ID format:** `"{doc_id}_{chunk_index:05d}"` — stable across re-ingestion; used as the Vertex AI Search DataStore document ID.

**Dependencies:** `sentence-transformers`, `numpy`, `models.Chunk`, `models.ExtractedDocument`, `models.Page`

**Known issue:** `ChunkerConfig` has Python defaults but is not yet loaded from `config/chunk_config.yaml`. A `ChunkerConfig.from_yaml(path)` classmethod is needed to bridge them (see CLAUDE.md Known Issues #1).

---

### `metadata_gen.py`

**Purpose:** Enrich each `Chunk` with structured `ChunkMetadata` via a Gemini LLM call, falling back to rule-based heuristics on failure.

**Key class:** `MetadataGenerator`

**Key exception:** `GeminiExtractionError` — raised when all retries are exhausted.

**Public methods:**

| Method | Description |
|---|---|
| `generate(chunk, context_window)` | Single-chunk metadata extraction with retry/backoff |
| `generate_batch(chunks, context_window, delay)` | Sequential batch with configurable inter-call delay for rate limiting |

**Internal flow for `generate()`:**
1. `_build_extraction_prompt` — injects the JSON schema from `config/metadata_schema.json` + context window + chunk text
2. `_call_gemini` — sends prompt with `response_mime_type="application/json"`; retries up to `_MAX_RETRIES=3` with exponential backoff (base 2s)
3. `_validate_and_coerce` — parses response dict into `ChunkMetadata`; coerces common type mismatches (e.g. `"2019"` → `int`); always overrides `doc_id`, `page_start`, `page_end`, `chunk_index` from the `Chunk` object, not from Gemini output
4. On any failure: `_fallback_extraction` — rule-based heuristics (first line as title, high-frequency capitalized terms as keywords)

**Dependencies:** `google.generativeai`, `config/metadata_schema.json`, `models.Chunk`, `models.ChunkMetadata`

**Rate limit:** Gemini 1.5 Pro standard quota is ~360 RPM. For batches >1000 chunks, consider Vertex AI Batch Prediction.

---

### `uploader.py`

**Purpose:** Upload the raw PDF and serialized chunk JSONL to Google Cloud Storage, idempotently.

**Key class:** `GCSUploader`

**GCS layout:**
```
gs://<bucket>/pdfs/<doc_id>.pdf
gs://<bucket>/chunks/<doc_id>.jsonl
```

**`doc_id`:** SHA-256 hex digest of the PDF file bytes — stable across re-uploads. The same file always maps to the same GCS paths.

**Public methods:**

| Method | Returns |
|---|---|
| `compute_doc_id(path)` | 64-char SHA-256 hex string |
| `is_already_uploaded(doc_id)` | `True` if both GCS objects exist (HEAD check, no download) |
| `upload_pdf(local_path, doc_id)` | `gs://<bucket>/pdfs/<doc_id>.pdf` |
| `upload_chunks(chunks, doc_id)` | `gs://<bucket>/chunks/<doc_id>.jsonl` |

**Chunk serialization (`_serialize_chunk`)** produces the Vertex AI Search unstructured import format:
```json
{
  "id": "<chunk_id>",
  "structData": { ...ChunkMetadata fields... },
  "content": {"mimeType": "text/plain", "uri": ""},
  "jsonData": "<chunk text>"
}
```

`upload_pdf` and `upload_chunks` are idempotent — both skip the upload and return the existing URI if `is_already_uploaded` returns True.

**Dependencies:** `google.cloud.storage`, `hashlib`, `models.Chunk`, `models.ChunkMetadata`

---

### `indexer.py`

**Purpose:** Import the chunk JSONL from GCS into a Vertex AI Search DataStore and track the async operation to completion.

**Key class:** `VertexSearchIndexer`

**Public methods:**

| Method | Returns |
|---|---|
| `import_chunks(gcs_jsonl_uri, doc_id)` | LRO operation name string |
| `wait_for_import(operation_name, poll_interval, timeout)` | `ImportResult` with success/failure counts |
| `delete_document(chunk_id)` | `None`; use before re-importing to avoid duplicates |
| `list_documents(page_size)` | List of document ID strings (handles pagination) |

**Import mechanics:**
- Uses `ImportDocuments` with `FULL` reconciliation mode (safer than `INCREMENTAL` on retry).
- `wait_for_import` polls every 15 s (default) up to 600 s.
- The DataStore region (`location`) is **immutable** after creation — must match `GCP_LOCATION` from `config/settings.py`.

**Re-ingestion pattern:** Call `delete_document(chunk_id)` for each affected chunk before re-importing. For full corpus refresh, use `scripts/purge_datastore.py --confirm`.

**Dependencies:** `google.cloud.discoveryengine_v1beta`, `models.ImportResult`

**Prerequisite:** The DataStore schema must be registered via `scripts/setup_vertex_search.py` before the first import. Chunks imported before schema registration silently drop unregistered metadata fields.

---

## Data Types (from `models.py`)

| Type | Kind | Produced by | Consumed by |
|---|---|---|---|
| `Page` | dataclass | `PDFExtractor` | `ContextAwareChunker` |
| `ExtractedDocument` | dataclass | `PDFExtractor` | `ContextAwareChunker` |
| `Chunk` | dataclass | `ContextAwareChunker` | `MetadataGenerator`, `GCSUploader` |
| `ChunkMetadata` | Pydantic | `MetadataGenerator` | `GCSUploader` (serialized to JSONL) |
| `ImportResult` | dataclass | `VertexSearchIndexer` | caller / batch script |

`ChunkMetadata` is Pydantic (not a plain dataclass) because it crosses a GCP API boundary and must be validated before DataStore import. All other pipeline types are dataclasses.

---

## Configuration

| File | Consumed by |
|---|---|
| `config/settings.py` | All GCP clients (project ID, bucket, location, DataStore ID) |
| `config/metadata_schema.json` | `MetadataGenerator` (prompt construction) and `setup_vertex_search.py` (schema registration) |
| `config/chunk_config.yaml` | Intended for `ChunkerConfig`; not yet wired (see Known Issues) |
