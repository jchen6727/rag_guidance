# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Status

**All source files are intentional stubs.** Every method body is `raise NotImplementedError`. The scaffolding, type signatures, docstrings, and config files are complete and authoritative — implementation has not started. Do not treat stub bodies as bugs.

## Commands

**Install dependencies** (Python 3.11+ required):
```bash
pip install -r requirements.txt
# CPU-only pytorch (avoids large GPU download):
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

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

**Ingest path** (triggered by watcher or batch script):
```
corpus/ PDF → extractor → chunker → metadata_gen → uploader (GCS) → indexer (Vertex AI Search)
```

**#ALTERNATE — One-time corpus scan:** Instead of running a continuous `CorpusWatcher` (which requires a live `Observer` process and `PDFEventHandler`), call `CorpusWatcher.catchup_scan()` directly and exit. This does a single pass over `corpus/`, checks each PDF against the manifest via `is_processed()`, and processes only new files. No watchdog daemon, no signal handling. Preferred for CI/CD jobs, cron-scheduled containers, or any environment where a blocking observer is inappropriate. `scripts/batch_ingest.py` already uses this pattern.

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
| `config/chunk_config.yaml` | Chunking parameters (token budget, similarity threshold, header patterns); **not yet wired to `ChunkerConfig`** — see Known Issues |
| `config/prompt_config.yaml` | Expert persona templates for 9 medical/scientific domains; `PromptBuilder` selects by domain key, falls back to `default` |

### Chunking Strategy (`ingestion/chunker.py`)

Two-pass approach — structural split first (section headers via regex), then semantic sub-split within sections (sentence-transformer cosine similarity, threshold from `ChunkerConfig.semantic_similarity_threshold`). The embedding model is lazy-loaded on first call. See `issues.md P1` for the full trade-off discussion — chunking quality gates all downstream retrieval.

### Metadata Generation (`ingestion/metadata_gen.py`)

Gemini is called once per chunk. The response is validated against `ChunkMetadata` with type coercion (common case: `year_published` arrives as string). Falls back to `_fallback_extraction()` on any Gemini failure — ingestion never hard-fails due to a bad API response. The `doc_id`, `page_start`, `page_end`, and `chunk_index` fields are **always overridden from the `Chunk` object**, never trusted from Gemini output.

### Vertex AI Search Indexer (`ingestion/indexer.py`)

`ImportDocuments` is an async LRO. `wait_for_import()` polls until completion. There is no per-document upsert — updating a chunk requires `delete_document()` then re-import. The DataStore region is immutable after creation; set `GCP_LOCATION` correctly before running `setup_vertex_search.py`.

### Citation Path

`ResponseGenerator.generate()` returns a `GeneratedResponse` with raw `Attribution` objects from Gemini grounding metadata. A separate call to `CitationBuilder.build()` converts these to numbered `Citation` objects. **`CitationBuilder` is not imported in `response_gen.py`** — the caller is responsible for this step (see Known Issues). Page-level citations require looking up `page_start`/`page_end` from `SearchResult.metadata` since Vertex AI grounding does not return page numbers.

## Known Issues (Before Implementing)

These are confirmed defects in the scaffolding that must be resolved:

1. **`ChunkerConfig` is not loaded from YAML.** The class has Python defaults; `chunk_config.yaml` is a separate document. Add a `ChunkerConfig.from_yaml(path)` classmethod to bridge them, or remove the YAML claim from the docstring.

2. **`{n_passages}` template variable undocumented.** `config/prompt_config.yaml` uses `{n_passages}` in `retrieval_instruction` but it is absent from the variable legend at the top of the file. `PromptBuilder` must inject it.

3. **`CitationBuilder` import missing from `response_gen.py`.** The `generate()` docstring implies it delegates to `CitationBuilder` internally, but no import exists. Decide: does `ResponseGenerator` own the citation step, or does the caller chain `CitationBuilder` separately? The current `generation/__init__.py` exports both as peers, suggesting the latter.

4. **No query-time entry point.** `scripts/batch_ingest.py` covers the ingest path. The query path (searcher → prompt_builder → response_gen → citation_builder) has no equivalent runner or `pipeline.py`.

5. **`tests/fixtures/` directory missing.** Referenced in `test_extractor.py` lines 5 and 26 (`FIXTURES_DIR`). Create it and populate with representative PDFs before implementing extractor tests.

6. **No `conftest.py`.** `make_chunk()` and similar helpers are duplicated across test files. Consolidate into `tests/conftest.py` when implementing tests.

## GCP Resource Order Dependency

`setup_vertex_search.py` → (register schema) → `batch_ingest.py`

The DataStore schema **must be registered before the first import**. Chunks indexed before schema registration silently drop unregistered metadata fields. Changing `metadata_schema.json` after ingestion requires `purge_datastore.py --confirm` followed by full re-ingestion.

## Session Notes

`journal/` is git-ignored. Per-session notes including the project autopsy (architecture decisions, known defects, prompt improvement recommendations) are stored at `journal/notes_6_8/autopsy.md`.
