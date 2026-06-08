# Caveats, Limitations, and Known Constraints

---

## 1. Vertex AI Search (Discovery Engine)

### Data Store Limitations
- **Unstructured DataStore only supports predefined schema fields for filtering.** Custom metadata fields must be registered via `UpdateSchema` before import — documents indexed before schema registration may silently drop those fields.
- **Import is asynchronous and non-atomic.** The `ImportDocuments` LRO (long-running operation) can take minutes to hours for large corpora; there is no per-document status during the operation, only a final summary. Plan for eventual consistency between ingestion and searchability.
- **No direct document-level updates.** To update a chunk (e.g., re-generated metadata), you must delete and re-import; there is no patch/upsert at the chunk level in unstructured stores.
- **DataStore region is immutable post-creation.** Choose `us` or `eu` at setup time; migrating later requires full re-ingestion.
- **Free tier limits are low.** Vertex AI Search is billed per query and per indexed GB. For large corpora (hundreds of textbooks) and high query volume, costs can escalate sharply — budget accordingly.
- **Semantic/vector search requires `enterprise` edition** of Vertex AI Search. The default edition provides keyword search only. Confirm edition at DataStore creation.

### Search Behavior
- **Hybrid search (semantic + keyword) is not exposed as a toggle** in the standard `SearchRequest`; it is controlled by engine configuration and relevance tuning settings in the console or via `UpdateServingConfig`. Test with representative queries before deploying.
- **Metadata filter expressions use a restricted syntax** (similar to Google AIP-160 filter strings). Complex boolean logic across many fields can produce unexpected results; validate filter expressions explicitly.
- **Top-K results are capped at 100 per query.** For tasks requiring exhaustive retrieval (e.g., building a summary over an entire textbook chapter), multiple paginated queries are required.

---

## 2. Gemini API (Metadata Generation + Response)

### Context Windows and Costs
- **Gemini 1.5 Pro supports 1M token context**, but pricing scales linearly. Sending full documents for metadata generation is expensive; always send the chunk + a small surrounding window, not the full PDF text.
- **Gemini output is non-deterministic.** The same chunk sent twice may produce slightly different metadata. Apply temperature=0 and structured output (JSON mode / response schema) to maximize consistency, but expect occasional schema violations that require fallback handling.
- **JSON mode does not guarantee valid JSON on every call.** Always wrap Gemini structured-output calls in a try/parse/retry loop with a fallback rule-based extractor.
- **Rate limits** vary by project tier: `gemini-1.5-pro` is typically capped at 360 RPM on standard quotas. Large batch ingestion (hundreds of thousands of chunks) will require exponential backoff and possibly Vertex AI Batch Prediction instead of online inference.

### Hallucination Risk in Metadata
- Gemini can hallucinate field values (e.g., inventing a publication year, fabricating an author name) for ambiguous or poorly formatted PDFs. Treat Gemini-generated metadata as **suggested, not authoritative** — implement a human review queue for high-confidence-required fields like `evidence_level` and `year_published`.

### Grounding and Citations
- **Vertex AI Search grounding for Gemini is a separate feature** from using the search results as context. Grounding attaches source references to model output chunks, but the mapping is approximate — a cited "source" may span a passage broader than the actual fact. Users should be warned that citations indicate the retrieved passage, not necessarily the exact sentence.
- **Native grounding does not return page numbers.** Page-level citations require propagating `page_start`/`page_end` through the chunk metadata and re-associating them post-retrieval; this requires custom logic in `citation_builder.py`.

---

## 3. PDF Extraction

- **Multi-column layouts** (common in medical journals) are frequently mis-read by `pdfplumber` as merged or interleaved text from both columns. Test extraction on a representative sample of your corpus before committing to a single extractor.
- **Tables and figures** are not extractable as structured data by default. `pdfplumber` can extract table cells but loses row/column semantics for merged cells. Equations and molecular diagrams are entirely opaque to text extractors.
- **Scanned PDFs** (many older textbooks) produce no text layer. Document AI OCR adds latency (~3–10s/page) and cost (~$1.50/1000 pages). Gate Document AI usage behind a text-layer detection check.
- **PDF specification is extremely permissive.** Some PDFs encode text in custom glyph maps or embed fonts without Unicode mappings, producing garbled or empty extraction. No automated fix exists; flag these for manual review.
- **Copyright.** Ingesting full-text commercial textbooks may violate publisher licenses. Confirm institutional/site license terms before ingesting. The pipeline should log source files and access terms.

---

## 4. Chunking

- **Chunk size is a fundamental trade-off.** Small chunks (128–256 tokens) improve retrieval precision but lose context; large chunks (1024+ tokens) preserve context but dilute relevance scores and increase generation context length. There is no universal optimal size — tune per document type.
- **Section header detection is heuristic.** Font-size-based and regex-based header detection breaks on inconsistent PDF formatting. A significant fraction of chunks will have wrong or missing `chapter` metadata without manual corpus-specific tuning.
- **Semantic chunking requires embedding inference** per sentence, which is slow (~50–200ms per sentence on CPU). For large corpora, run the embedding step on GPU or pre-compute embeddings offline.
- **Cross-chunk references** (e.g., "as shown in Table 3.2 above") lose meaning after chunking. The retriever will return individual chunks without the referenced content unless a parent-document retrieval strategy is implemented.

---

## 5. Infrastructure and Operations

- **IAM over-provisioning risk.** The service account needs broad permissions across GCS, Vertex AI, Document AI, and Discovery Engine. Use a dedicated service account with least-privilege per component; do not reuse a project-level owner account.
- **No built-in deduplication.** If the same PDF is placed in `corpus/` twice (different filename or after a rename), the pipeline will ingest it as a new document. The content-hash manifest in `uploader.py` mitigates this but only within a single ingestion run — implement cross-run hash checks in a persistent store.
- **GCS egress costs.** Reading large JSONL chunk files for re-indexing and downloading PDFs for re-extraction incurs egress charges if processed outside the DataStore's region. Co-locate all GCP services in the same region.
- **Watchdog is a local process.** The watcher is not fault-tolerant; if the host machine restarts, files dropped during the outage will not be processed unless a catch-up scan on startup is implemented. For production, replace with a GCS event-driven trigger (Cloud Functions + Eventarc) instead.
- **#ALTERNATE — skip the watcher entirely.** `CorpusWatcher.catchup_scan()` performs a single manifest-aware pass over `corpus/` and exits — no `Observer`, no `PDFEventHandler`, no background thread. This is strictly safer for CI/CD pipelines, Kubernetes `Job`s, and scheduled cron-based deployments. The only cost is ingestion latency: files added between runs are not processed until the next invocation. See `issues.md #ALTERNATE` for the full trade-off discussion.

---

## 6. Response Quality

- **Retrieval quality gates response quality.** If the top-K retrieved chunks are irrelevant or misleadingly similar in embedding space, Gemini will hallucinate despite the "use only retrieved passages" instruction. Evaluate retrieval precision independently before evaluating end-to-end response quality.
- **Expert persona framing does not change the model's knowledge boundary.** The persona increases the formality and structure of responses but does not make the model more accurate. All factual claims still depend on what was retrieved.
- **Citation completeness is not guaranteed.** Gemini may synthesize across multiple chunks without citing all of them. The citation list reflects grounding metadata, not a true audit trail of every source sentence.
