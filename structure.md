# RAG Guidance Pipeline — Project Structure

## Overview

An end-to-end pipeline that ingests technical/clinical/scientific PDFs, generates AI-guided metadata via Gemini, indexes into Vertex AI Search, and produces expert-persona responses with citations.

---

## Data Flow

```
/corpus (watched dir)
      │
      ▼
[1. Watcher] ──────────────────────────────────────────────
      │ new PDF detected
      ▼
[2. PDF Extractor] (text, tables, page layout)
      │ raw text + structure
      ▼
[3. Context-Aware Chunker] (semantic + structural boundaries)
      │ chunks[]
      ▼
[4. Metadata Generator] ─── Gemini API ──► metadata JSON
      │ enriched chunks[]
      ▼
[5. GCS Uploader] (original PDF + chunk JSONL)
      │
      ▼
[6. Vertex AI Search Indexer] (DataStore import)
      │
      ▼
[Vertex AI Search DataStore] ◄─────────── [Query Engine]
                                                 │
                                    [7. Retrieval + Re-ranker]
                                                 │
                                    [8. Response Generator] ── Gemini API
                                                 │
                                    Response + Citations
```

---

## Directory Layout

```
rag_guidance/
├── corpus/                         # Drop PDFs here for ingestion
├── prompt/                         # Prompt template files
│
├── ingestion/
│   ├── __init__.py
│   ├── watcher.py                  # Watchdog-based directory monitor
│   ├── extractor.py                # PDF text + structure extraction
│   ├── chunker.py                  # Context-aware chunking logic
│   ├── metadata_gen.py             # Gemini metadata generation
│   ├── uploader.py                 # GCS upload (PDF + chunk JSONL)
│   └── indexer.py                  # Vertex AI Search DataStore import
│
├── retrieval/
│   ├── __init__.py
│   ├── searcher.py                 # Vertex AI Search query wrapper
│   └── reranker.py                 # Optional LLM-based re-ranking
│
├── generation/
│   ├── __init__.py
│   ├── prompt_builder.py           # Expert persona prompt assembly
│   ├── response_gen.py             # Gemini generation with grounding
│   └── citation_builder.py        # Source attribution formatting
│
├── config/
│   ├── settings.py                 # Env vars, GCP project IDs, constants
│   ├── metadata_schema.json        # Canonical metadata field definitions
│   ├── prompt_config.yaml          # Persona templates and system prompts
│   └── chunk_config.yaml           # Chunking parameters (size, overlap, strategy)
│
├── scripts/
│   ├── setup_vertex_search.py      # One-time DataStore + Engine provisioning
│   ├── batch_ingest.py             # Bulk ingest existing corpus/
│   └── purge_datastore.py          # Wipe + re-index (dev/reset utility)
│
├── tests/
│   ├── test_extractor.py
│   ├── test_chunker.py
│   ├── test_metadata_gen.py
│   └── test_retrieval.py
│
├── structure.md                    # This file
├── caveats.md
├── issues.md
├── requirements.txt
└── .env.example
```

---

## Component Descriptions

### 1. Watcher (`ingestion/watcher.py`)
Uses `watchdog` to monitor `corpus/` for new or modified PDFs. On detection, triggers the full ingestion pipeline. Tracks processed files via a local manifest to prevent re-ingestion.

**#ALTERNATE — one-time corpus scan:** Call `CorpusWatcher.catchup_scan()` directly and exit. Scans all PDFs in `corpus/` once, checks each against the manifest via `is_processed()`, and runs the pipeline only for new files. No `Observer` started, no `PDFEventHandler` needed, no blocking call. Suitable for CI/CD job steps, cron-scheduled containers, or Kubernetes `Job`s where a persistent daemon is not appropriate. Trade-off: ingestion latency equals the scheduling interval rather than seconds. `scripts/batch_ingest.py` is the existing entry point using this pattern.

### 2. PDF Extractor (`ingestion/extractor.py`)
Extracts text preserving page boundaries, section headers, and table structure. Primary: `pdfplumber` (layout-aware). Fallback: Google Document AI for scanned/complex layouts.

### 3. Context-Aware Chunker (`ingestion/chunker.py`)
Two-pass strategy:
- **Structural pass**: Split on detected section headers, figure captions, and page breaks.
- **Semantic pass**: Sub-split using sentence embeddings (via `sentence-transformers`) to keep semantically coherent units within token budget.
- Maintains `parent_section`, `page_start`, `page_end`, `chunk_index` provenance fields on every chunk.

### 4. Metadata Generator (`ingestion/metadata_gen.py`)
Sends each chunk (with surrounding context window) to Gemini with a structured extraction prompt. Produces fields from `config/metadata_schema.json`. Falls back to rule-based extraction on API failure.

### 5. GCS Uploader (`ingestion/uploader.py`)
Uploads original PDF to `gs://<bucket>/pdfs/<doc_id>.pdf` and chunk JSONL to `gs://<bucket>/chunks/<doc_id>.jsonl`. Preserves idempotency via content hashing.

### 6. Vertex AI Search Indexer (`ingestion/indexer.py`)
Calls the Discovery Engine Data Connector to import the chunk JSONL into an unstructured DataStore. Monitors the import operation for completion/errors.

### 7. Retrieval (`retrieval/searcher.py`)
Wraps Vertex AI Search `SearchService` with:
- Semantic + keyword hybrid search
- Metadata filter expressions (e.g., `domain = "cardiology"`)
- Configurable top-K and minimum relevance score

### 8. Response Generator (`generation/response_gen.py`)
Assembles a prompt using expert persona template + retrieved chunks, then calls Gemini with grounding. Extracts citation pointers from the grounding metadata and passes to `citation_builder.py`.

---

## APIs and SDKs

| Service | Python Package | Purpose |
|---|---|---|
| Vertex AI Search (Discovery Engine) | `google-cloud-discoveryengine>=0.11` | DataStore creation, document import, search queries |
| Vertex AI / Gemini | `google-generativeai>=0.7` or `google-cloud-aiplatform>=1.50` | Metadata extraction, response generation |
| Google Cloud Storage | `google-cloud-storage>=2.14` | PDF + chunk JSONL staging |
| Google Document AI | `google-cloud-documentai>=2.24` | Scanned PDF OCR fallback |
| Watchdog | `watchdog>=4.0` | Local filesystem event monitoring |
| pdfplumber | `pdfplumber>=0.11` | Primary PDF text + table extraction |
| sentence-transformers | `sentence-transformers>=3.0` | Semantic chunking embeddings |
| Pydantic | `pydantic>=2.0` | Config and metadata model validation |

### GCP Services Required
- **Vertex AI Search** — Discovery Engine DataStore + Search Engine (location: `global` or `us`)
- **Vertex AI** — Gemini model access (`gemini-1.5-pro` recommended for long-context metadata generation)
- **Google Cloud Storage** — staging bucket in same region as DataStore
- **Document AI** — optional; requires processor provisioning in the same project
- **IAM Roles** — Service account needs: `Discovery Engine Editor`, `Storage Object Admin`, `Vertex AI User`, `Document AI API User`

---

## Metadata Schema (canonical fields)

Defined in `config/metadata_schema.json`, generated per-chunk by Gemini:

| Field | Type | Description |
|---|---|---|
| `doc_id` | string | SHA-256 hash of source PDF |
| `source_file` | string | Original filename |
| `title` | string | Inferred document title |
| `domain` | string | Specialty domain (e.g., `cardiology`, `oncology`) |
| `subdomain` | string | Narrower topic |
| `doc_type` | enum | `textbook`, `clinical_guideline`, `research_paper` |
| `chapter` | string | Chapter or section name |
| `page_start` | int | First page of chunk |
| `page_end` | int | Last page of chunk |
| `chunk_index` | int | Sequential index within document |
| `keywords` | string[] | Key terms extracted by Gemini |
| `entities` | string[] | Named clinical/scientific entities |
| `evidence_level` | string | Optional: `Grade A`, `Grade B`, etc. |
| `year_published` | int | Publication year if extractable |

---

## Prompt Architecture

### Expert Persona Template (in `config/prompt_config.yaml`)

```
system: |
  You are acting as an expert {domain} specialist with deep knowledge of
  {subdomain}. You have access to a curated corpus of authoritative
  {doc_type} literature. Answer questions with clinical/scientific rigor,
  acknowledging uncertainty where evidence is limited.

retrieval_instruction: |
  Based on the user query, the following passages have been retrieved from
  the {corpus_name} corpus. Use ONLY information contained in these passages
  to formulate your response. Do not draw on outside knowledge.

citation_format: |
  Cite each factual claim inline as [Author/Title, p.{page}] or
  [Source {n}] referencing the numbered source list appended to your response.
```

### Query Pipeline
1. User submits free-text query + optional domain filter
2. `prompt_builder.py` selects persona from `prompt_config.yaml` by domain
3. `searcher.py` retrieves top-K chunks (default K=8)
4. Full prompt assembled: persona + retrieval instruction + chunks + query
5. Gemini generates response; grounding metadata mapped to citation list
6. Response + formatted citations returned to caller
