# RAG Guidance Pipeline — Project Structure

## Overview

An end-to-end pipeline that ingests **psychotherapy** clinical/scientific PDFs (scoped to CBT/DBT/IPT practice), generates AI-guided metadata via Gemini, indexes into Vertex AI Search, and produces expert-persona guidance with citations. It serves two modes: **RTA** (real-time, in-session) and **ASA** (after-session analysis). The authoritative schema and persona set live in `config/metadata_schema.json` and `config/prompt_config.yaml`; see `BOOTSTRAP.md` for the current source-of-truth reading order.

---

## Data Flow

```
/corpus (flat dir to scan)
      │
      ▼
[1. CorpusScanner.scan()] ─────────────────────────
      │ via scripts/batch_ingest.py — new PDF found via manifest check
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
├── prompt/                         # (currently empty)
│
├── rta_prompt/                     # RTA/ASA pipelines + models (stub)
│   ├── models.py                   # PatientContext, RTAResponse, ASAResponse, ...
│   ├── rta/                        # event_detector.py, searcher.py, pipeline.py
│   └── asa/                        # searcher.py, pipeline.py
│
├── ingestion/
│   ├── __init__.py
│   ├── scanner.py                  # Corpus scanner; CorpusScanner.scan() is the primary entry point
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

### 1. Corpus Scanner (`ingestion/scanner.py`)
`CorpusScanner.scan()` scans `corpus/` for new PDFs, checks each against the manifest via `is_processed()`, runs the pipeline for unprocessed files in alphabetical order, and returns. Manifest is written atomically after each file. Cron-scheduled container or a GCS Eventarc trigger. No daemon, no background thread. `scripts/batch_ingest.py` is the entry point.

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
- Metadata filter expressions (e.g., `domain = "cognitive_behavioral"`, `corpus_scope != "asa_only"`)
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

**`config/metadata_schema.json` is authoritative** — it defines ~30 psychotherapy-oriented fields and is the single source of truth for Gemini extraction and DataStore registration. The table below is a representative subset only; consult the JSON for the full field list, enums, and defaults.

| Field | Type | Description |
|---|---|---|
| `doc_id` | string | SHA-256 hash of source PDF |
| `source_file` | string | Original filename |
| `title` | string | Inferred document title |
| `domain` | enum | Document-level orientation (e.g., `cognitive_behavioral`, `dialectical_behavior`, `trauma_focused`, `interpersonal`) |
| `subdomain` | string | Narrower topic (free text) |
| `doc_type` | enum | e.g., `treatment_manual`, `session_transcript`, `clinical_worksheet`, `rct_paper`, `front_matter` |
| `therapeutic_modality` | enum[] | Chunk-level modality tags (CBT/DBT/IPT scope): `CBT`, `DBT`, `CPT`, `PE`, `IPT`, … |
| `corpus_scope` | enum | Hard RTA/ASA routing field: `rta_and_asa` (default) or `asa_only` |
| `session_event_tags` | enum[] | In-session events (primary RTA retrieval trigger) |
| `analysis_function` | enum[] | Post-session functions (primary ASA routing field) |
| `practice_recommendation_level` | enum? | Strength/polarity of recommendation (replaces GRADE `evidence_level`) |
| `page_start` / `page_end` | int | Chunk page range |
| `chunk_index` | int | Sequential index within document |
| `keywords` / `technique_tags` | string[] | Topic terms / named clinical techniques |
| `year_published` | int? | Publication year if extractable |

> Note: the earlier biomedical fields `entities` and GRADE `evidence_level` were **removed**; `domain`/`doc_type` enums were replaced wholesale. `models.py::ChunkMetadata` and `ingestion/metadata_gen.py` are still out of sync with this schema — see `DISCREPANCIES.md`.

---

## Prompt Architecture

### Expert Persona Templates (in `config/prompt_config.yaml`)

Personas are psychotherapy supervisors scoped to CBT/DBT/IPT competence: a `default` persona plus 10 domain-specific personas (`cognitive_behavioral`, `dialectical_behavior`, `trauma_focused`, `interpersonal`, `motivational_interviewing`, `mindfulness_based`, `crisis_intervention`, `therapeutic_alliance`, `clinical_supervision`, `psychopathology_clinical`). `PromptBuilder` selects by `domain` key and falls back to `default` on a miss.

Retrieval instructions are **split by pipeline mode** — `retrieval_instruction_rta` (in-session, terse/actionable) and `retrieval_instruction_asa` (post-session, synthesis) — plus a shared `citation_format`. Template variables include `{domain}`, `{subdomain}`, `{corpus_name}`, `{doc_type_list}`, `{n_passages}`, `{pipeline_mode}`, `{session_event}`, `{therapeutic_modality}`.

### Query Pipeline
1. Caller submits query/context + `pipeline_mode` ("rta" or "asa") + `domain`
2. `prompt_builder.py` selects persona by `domain` and the `rta`/`asa` retrieval instruction block
3. `searcher.py` retrieves top-K chunks, applying hard pre-filters (`corpus_scope != asa_only` for RTA; `target_audience != patient` except homework)
4. Full prompt assembled: persona + retrieval instruction + chunks + query
5. Gemini generates response; grounding metadata mapped to citation list
6. Response + formatted citations returned to caller

> The query path (`retrieval/`, `generation/`, `rta_prompt/`) is still stubbed — see `DISCREPANCIES.md`.
