# Ingestion Tutorial

End-to-end walkthrough for uploading PDFs into the RAG guidance pipeline.
After completing this tutorial, your PDFs will be chunked, enriched with
Gemini-generated metadata, stored in GCS, and indexed in Vertex AI Search.

---

## Prerequisites

**Python 3.11+** and all dependencies installed:

```bash
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu  # CPU-only PyTorch
```

**GCP project** with the following APIs enabled:
- Vertex AI (for Gemini metadata generation)
- Cloud Storage
- Discovery Engine (Vertex AI Search)
- Document AI *(optional — only needed for scanned/image-only PDFs)*

**Authentication** — Application Default Credentials work for GCP-hosted
environments. For local development:

```bash
gcloud auth application-default login
```

---

## Step 1 — Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in:

```
GCP_PROJECT_ID=your-gcp-project-id
GCP_LOCATION=global
GCS_BUCKET_NAME=your-rag-corpus-bucket
VERTEX_SEARCH_DATASTORE_ID=rag-guidance-datastore
VERTEX_SEARCH_ENGINE_ID=rag-guidance-engine
GEMINI_API_KEY=                  # leave blank to use ADC
```

Load the variables into your shell:

```bash
source .env  # or: export $(grep -v '^#' .env | xargs)
```

---

## Step 2 — Provision GCP resources (run once)

This creates the Vertex AI Search DataStore and registers the metadata schema.
**Run this before any ingestion.** Chunks indexed before schema registration
silently drop their metadata fields.

```bash
# Preview what will be created
PYTHONPATH=. python scripts/setup_vertex_search.py --dry-run

# Execute (takes ~1–2 minutes for resource creation)
PYTHONPATH=. python scripts/setup_vertex_search.py
```

Expected output:
```
INFO Step 1/3: Creating DataStore...
INFO DataStore created: projects/.../dataStores/rag-guidance-datastore
INFO Step 2/3: Registering schema...
INFO Schema created: .../schemas/default_schema
INFO Step 3/3: Creating Search Engine...
INFO Search Engine created: .../engines/rag-guidance-engine
INFO Done. Resources:
INFO   DataStore: projects/.../dataStores/rag-guidance-datastore
INFO   Engine:    projects/.../engines/rag-guidance-engine
```

---

## Step 3 — Place PDFs in the corpus directory

The default corpus directory is `corpus/` (set via `CORPUS_DIR` env var).
PDFs already present in the repo:

```
corpus/
  APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf
  Comprehensive-CBT-for-Social-Phobia-Manual.pdf
  PE_for_PTSD_2022.pdf
```

Add your own PDFs by copying them there:

```bash
cp /path/to/your/document.pdf corpus/
```

---

## Step 4 — Dry-run to preview

Before touching GCS or Vertex AI Search, verify the extract → chunk → metadata
steps work locally:

```bash
PYTHONPATH=. python scripts/batch_ingest.py --dry-run
```

Sample output:
```
2026-06-16 10:00:01 INFO Found 3 PDF(s) to ingest.
2026-06-16 10:00:01 INFO DRY RUN: upload and index steps will be skipped.
2026-06-16 10:00:01 INFO Processing: PE_for_PTSD_2022.pdf
2026-06-16 10:00:02 INFO   doc_id: a3f9c1b2e4...
2026-06-16 10:00:04 INFO   Extracted 87 page(s)
2026-06-16 10:00:06 INFO   Produced 134 chunk(s)
2026-06-16 10:00:08 INFO   Generating metadata for 134 chunk(s)...
2026-06-16 10:02:15 INFO   [DRY RUN] Skipping upload and index steps.
...

======================================================================
Ingestion Summary  (3 file(s))
======================================================================
[OK  ] PE_for_PTSD_2022.pdf
       doc_id  : a3f9c1b2e4d56f78...
       chunks  : 134  (metadata failures: 0)
       pdf     :
       chunks  :
       import  : 0 ok / 0 failed
       elapsed : 74.3s
...
```

A metadata failure count above 0 means Gemini failed for those chunks and
fallback rule-based extraction was used. This does not block ingestion.

---

## Step 5 — Ingest all PDFs in corpus/

```bash
PYTHONPATH=. python scripts/batch_ingest.py
```

The script processes each PDF in alphabetical order, skipping any already
recorded in the manifest (`.ingestion_manifest.json`). Each file goes through:

1. SHA-256 content hash → `doc_id`
2. PDF text extraction via `pdfplumber` (OCR fallback to Document AI if no text layer)
3. Two-pass chunking: structural split on section headers → semantic sub-split on embedding similarity
4. Gemini metadata generation per chunk (with exponential-backoff retry)
5. Upload PDF and chunk JSONL to `gs://<bucket>/pdfs/` and `gs://<bucket>/chunks/`
6. Import chunks into Vertex AI Search via async LRO
7. Wait for import to complete before moving to the next file

On success, the file is recorded in `.ingestion_manifest.json`:
```json
{
  "PE_for_PTSD_2022.pdf": "a3f9c1b2e4d56f78..."
}
```

---

## Step 6 — Ingest a single PDF

```bash
PYTHONPATH=. python scripts/batch_ingest.py --file corpus/PE_for_PTSD_2022.pdf
```

To force re-ingestion of a file already in the manifest:

```bash
PYTHONPATH=. python scripts/batch_ingest.py --file corpus/PE_for_PTSD_2022.pdf --force
```

---

## Manifest and idempotency

Re-running `batch_ingest.py` without `--force` is safe — files already in the
manifest are skipped. The manifest is updated atomically after each successful
file so partial runs are resumable:

```bash
# Interrupted run — only the remaining files are processed on re-run
PYTHONPATH=. python scripts/batch_ingest.py
```

---

## Purging the DataStore

Use `purge_datastore.py` when schema or chunking parameters have changed and
a full re-index is needed. The `--confirm` flag is required to prevent accidents.

```bash
# Delete a single document's chunks (by doc_id SHA-256 hash)
PYTHONPATH=. python scripts/purge_datastore.py \
  --doc-id a3f9c1b2e4d56f78... \
  --confirm

# Wipe everything and immediately re-ingest
PYTHONPATH=. python scripts/purge_datastore.py --confirm --reingest

# Preview without deleting
PYTHONPATH=. python scripts/purge_datastore.py --confirm --dry-run
```

After purging, re-run `batch_ingest.py --force` to re-populate from the local
corpus directory.

---

## Chunking configuration

Chunking parameters live in `config/chunk_config.yaml` and are loaded at
startup via `ChunkerConfig.from_yaml()`. Key knobs:

| Parameter | Default | Effect |
|---|---|---|
| `max_tokens` | 512 | Hard token ceiling per chunk |
| `min_tokens` | 64 | Fragments smaller than this are merged with the next chunk |
| `overlap_tokens` | 64 | Tokens prepended from the previous chunk's tail |
| `semantic_similarity_threshold` | 0.75 | Lower = more splits; higher = larger chunks |
| `embedding_model` | `all-MiniLM-L6-v2` | Sentence embedding model for boundary detection |

Changing these parameters after ingestion requires `purge_datastore.py --confirm`
followed by a full re-ingest.

To load a custom config at runtime, modify `batch_ingest.py` to pass the config
explicitly:

```python
from ingestion.chunker import ChunkerConfig, ContextAwareChunker
config = ChunkerConfig.from_yaml(Path("config/chunk_config.yaml"))
chunker = ContextAwareChunker(config)
```

---

## Metadata schema

`config/metadata_schema.json` defines the fields extracted by Gemini and
registered as filterable attributes in Vertex AI Search. Key fields:

| Field | Type | Description |
|---|---|---|
| `domain` | enum | Medical/scientific specialty (e.g. `psychiatry`, `cardiology`) |
| `doc_type` | enum | `textbook`, `clinical_guideline`, `research_paper`, etc. |
| `title` | string | Inferred document or chapter title |
| `keywords` | list | Key terms extracted from the chunk |
| `year_published` | int | Publication year |
| `evidence_level` | enum | GRADE evidence level (`A`/`B`/`C`/`D`) if applicable |

Schema changes require `setup_vertex_search.py` to re-register the schema,
followed by `purge_datastore.py --confirm` and full re-ingestion.

---

## GCP resource order

```
setup_vertex_search.py   →   (register schema)   →   batch_ingest.py
```

Ingestion before schema registration will silently drop all metadata fields
from the indexed documents.

---

## Troubleshooting

**`EnvironmentError: Required environment variable 'GCP_PROJECT_ID' is not set`**
— Source your `.env` file or export the variable:
```bash
export GCP_PROJECT_ID=your-project-id
```

**`ExtractionError: pdfplumber failed and Document AI is not configured`**
— The PDF has no text layer (scanned image). Set `DOCUMENT_AI_PROCESSOR_ID`
in `.env` to enable OCR fallback.

**High metadata failure count**
— Gemini rate limits may be exceeded for large batches. The generator retries
3 times with exponential backoff and then falls back to rule-based extraction.
For corpora > 1000 chunks, consider Vertex AI Batch Prediction.

**Import LRO timeout**
— The default timeout is 600s. Large batches may need more time. Increase via
the `timeout` parameter on `VertexSearchIndexer.wait_for_import()`.

**`AlreadyExists` on `setup_vertex_search.py`**
— The script is idempotent; this is not an error. Existing resources are
detected and skipped.
