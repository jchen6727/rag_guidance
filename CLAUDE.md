# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

**Partially implemented.** The **ingest path is fully implemented** (`ingestion/extractor.py`, `chunker.py`, `metadata_gen.py`, `uploader.py`, `indexer.py`, `scanner.py`), along with `models.py`, `config/settings.py`, `scripts/`, and most of `tests/`. The **query path remains stubbed** (`raise NotImplementedError` in every method body): `generation/`, `retrieval/`, and `rta_prompt/`. `ingestion/watcher.py` is a superseded stub (replaced by `scanner.py`) and should be treated as dead. Scaffolding, type signatures, docstrings, and config files are complete and authoritative for the stubbed modules — do not treat those stub bodies as bugs.

**Domain note:** the pipeline targets **psychotherapy guidance for CBT/DBT/IPT-trained clinicians** with two modes, RTA (real-time, in-session) and ASA (after-session). See `BOOTSTRAP.md` and `config/metadata_schema.json`. Parts of this file still describe an older generic-biomedical framing.

## Commands

**Install dependencies** (Python 3.12+ required; rollback floor is 3.11):
```bash
pip install -r requirements.txt
# CPU-only pytorch (avoids large GPU download):
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

`ingestion/requirements.txt` is a scoped subset covering only the ingestion pipeline's direct dependencies (no `google-cloud-aiplatform`, pytest, etc.) — use it when working on the ingestion module in isolation.

**There is no `pyproject.toml`.** All imports are absolute from the project root. Prefix every command with `PYTHONPATH=.`:
```bash
PYTHONPATH=. pytest tests/
PYTHONPATH=. pytest tests/test_chunker.py::TestMakeChunkId::test_format_is_correct -v
PYTHONPATH=. pytest tests/ --cov=ingestion --cov=retrieval --cov=generation
```

**GCP provisioning** (run once before any ingestion):
```bash
cp .env.example .env  # populate before running
PYTHONPATH=. python scripts/setup_vertex_search.py --dry-run   # preview
PYTHONPATH=. python scripts/setup_vertex_search.py             # execute
```

**Ingestion:**
```bash
PYTHONPATH=. python scripts/batch_ingest.py --dry-run          # preview
PYTHONPATH=. python scripts/batch_ingest.py                    # ingest new PDFs
PYTHONPATH=. python scripts/batch_ingest.py --file corpus/x.pdf --force
```

**Purge DataStore** (destructive — requires `--confirm`):
```bash
PYTHONPATH=. python scripts/purge_datastore.py --confirm --dry-run
PYTHONPATH=. python scripts/purge_datastore.py --confirm
```

## Architecture

### Two Distinct Pipelines

**Ingest path** (triggered by `scripts/batch_ingest.py` via `CorpusScanner.scan()`):
```
corpus/ PDF → extractor → chunker → metadata_gen → uploader (GCS) → indexer (Vertex AI Search)
```

Ingestion is a one-time corpus scan: `CorpusScanner.scan()` does a single pass over `corpus/`, checks each PDF against the manifest via `is_processed()`, and processes only new files. No watchdog daemon, no blocking observer, no signal handling.

**Query path** (no entry point exists yet — see Known Issues):
```
query + domain → searcher → [reranker] → prompt_builder → response_gen → citation_builder → GeneratedResponse
```

### Shared Type Layer (`models.py`)

All inter-component data flows through types in `models.py`. The design splits into two groups:
- **Pydantic** (`ChunkMetadata`) — anything that crosses a GCP API boundary; validates before DataStore import
- **Dataclasses** (`Page`, `ExtractedDocument`, `Chunk`, `SearchResult`, `Attribution`, `Citation`, `GeneratedResponse`, `ImportResult`) — in-process pipeline state

The `Chunk.chunk_id` canonical form is `"{doc_id}_{chunk_index:05d}"`. This ID is used as the DataStore document ID, so it must be stable across re-ingestion.

### Configuration

| File | Role |
|---|---|
| `config/settings.py` | Singleton `settings` object; reads env vars lazily; call `settings.validate_all()` at startup |
| `config/metadata_schema.json` | Canonical metadata field definitions; **used both for Gemini extraction prompts and Vertex AI Search schema registration** |
| `config/schema_loader.py` | `SchemaVocabulary` — structured loader that derives the controlled vocabulary (enums, array fields, defaults, coercion) from `metadata_schema.json`. Single source of truth consumed by `metadata_gen.py` and `setup_vertex_search.py` so the code never drifts from the schema |
| `config/chunk_config.yaml` | Chunking parameters (token budget, similarity threshold, header patterns); loaded via `ChunkerConfig.from_yaml()` |
| `config/prompt_config.yaml` | Psychotherapy persona templates (CBT/DBT/IPT scope): `default` plus 10 domain personas; split `retrieval_instruction_rta`/`retrieval_instruction_asa` blocks. `PromptBuilder` selects by domain key, falls back to `default` |

### Chunking Strategy (`ingestion/chunker.py`)

Two-pass approach — structural split first (section headers via regex), then semantic sub-split within sections (sentence-transformer cosine similarity, threshold from `ChunkerConfig.semantic_similarity_threshold`). The embedding model is lazy-loaded on first call. Chunking quality gates all downstream retrieval.

`ChunkerConfig` has Python defaults and is also loaded from `config/chunk_config.yaml` via the `ChunkerConfig.from_yaml()` classmethod. Note `skip_doc_types` and `front_matter_indicators` are defined on `ChunkerConfig` (and in the YAML) but are **not yet consumed** by `ContextAwareChunker` — front-matter filtering is not wired.

### Metadata Generation (`ingestion/metadata_gen.py`)

Gemini is called once per chunk. The response is validated and coerced against the psychotherapy schema via `config/schema_loader.py::SchemaVocabulary` (loaded from `metadata_schema.json` at construction), then instantiated as `ChunkMetadata`. The controlled vocabulary is **not** hard-coded in `metadata_gen.py` — enum validity, array normalization, integer parsing, and defaults all come from the schema, and keys absent from the schema (e.g. the removed `entities`/`evidence_level`) are dropped. Common coercions: `year_published` string→int; single string→list for array fields; unknown `domain`→`other`, unknown `doc_type`→`""`. Falls back to `_fallback_extraction()` on any Gemini failure — ingestion never hard-fails due to a bad API response. The `doc_id`, `page_start`, `page_end`, and `chunk_index` fields are **always overridden from the `Chunk` object**, never trusted from Gemini output.

### Vertex AI Search Indexer (`ingestion/indexer.py`)

`ImportDocuments` is an async LRO. `wait_for_import()` polls until completion. There is no per-document upsert — updating a chunk requires `delete_document()` then re-import. The DataStore region is immutable after creation; set `GCP_LOCATION` correctly before running `setup_vertex_search.py`.

### Citation Path

`ResponseGenerator.generate()` returns a `GeneratedResponse` with raw `Attribution` objects from Gemini grounding metadata. A separate call to `CitationBuilder.build()` converts these to numbered `Citation` objects. **`CitationBuilder` is not imported in `response_gen.py`** — the caller is responsible for this step (see Known Issues). Page-level citations require looking up `page_start`/`page_end` from `SearchResult.metadata` since Vertex AI grounding does not return page numbers.

## Known Issues (Before Implementing)

These are confirmed defects in the scaffolding that must be resolved:

1. **RESOLVED — `ChunkerConfig.from_yaml()` implemented.** `ChunkerConfig` now loads from `chunk_config.yaml`. Remaining gap: `skip_doc_types`/`front_matter_indicators` are loaded but never used by `ContextAwareChunker`.

2. **RESOLVED — `{n_passages}` documented.** `config/prompt_config.yaml` now lists `{n_passages}` in the variable legend and uses it in both `retrieval_instruction_rta` and `retrieval_instruction_asa`. `PromptBuilder` (still a stub) must inject it.

3. **`CitationBuilder` import missing from `response_gen.py`.** The `generate()` docstring implies it delegates to `CitationBuilder` internally, but no import exists. Decide: does `ResponseGenerator` own the citation step, or does the caller chain `CitationBuilder` separately? The current `generation/__init__.py` exports both as peers, suggesting the latter.

4. **No query-time entry point.** `scripts/batch_ingest.py` covers the ingest path. The query path (searcher → prompt_builder → response_gen → citation_builder) has no equivalent runner or `pipeline.py`.

5. **`tests/fixtures/` directory missing.** Referenced in `test_extractor.py` lines 5 and 26 (`FIXTURES_DIR`). Create it and populate with representative PDFs before implementing extractor tests.

6. **No `conftest.py`.** `make_chunk()` and similar helpers are duplicated across test files. Consolidate into `tests/conftest.py` when implementing tests.

## GCP Resource Order Dependency

`setup_vertex_search.py` → (register schema) → `batch_ingest.py`

The DataStore schema **must be registered before the first import**. Chunks indexed before schema registration silently drop unregistered metadata fields. Changing `metadata_schema.json` after ingestion requires `purge_datastore.py --confirm` followed by full re-ingestion.

## Out of Scope

`journal/` is git-ignored personal session notes. Do not read, reference, or treat its contents as authoritative project documentation.
