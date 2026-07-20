# ingestion/ — Developer Guide (Internal-Facing)

**Audience:** technical auditors / architects.
**Scope:** the implemented ingest pipeline: `extractor → chunker → metadata_gen → uploader (GCS) → indexer (Vertex AI Search)`, orchestrated by `CorpusScanner` / `scripts/batch_ingest.py`.
**Governed by:** `ORCHESTRATOR.md`. Consumes vocabulary from `config/` (currently `metadata_schema.json`).
**Last reconciled:** 2026-07-20.

---

## Feedback log (newest first)

<!-- Developers: prepend dated feedback here. -->

*(no developer feedback recorded yet)*

`<!-- ▲ unprocessed above this line ▲ -->`

---

## 1. Pipeline map

```
corpus/*.pdf
  │  compute doc_id = SHA-256(pdf bytes)                    [uploader.compute_doc_id]
  ├─ extractor.extract(pdf)      → ExtractedDocument(pages) [pdfplumber; Document AI optional]
  ├─ chunker.chunk(doc)          → list[Chunk]              [structural split → semantic sub-split]
  ├─ metadata_gen.generate(chunk)→ ChunkMetadata           [Gemini once/chunk → coerce vs schema]
  ├─ filter skip_doc_types                                 [batch_ingest.py:114]
  ├─ uploader.upload_pdf / upload_chunks → GCS URIs
  └─ indexer.import_chunks → LRO ; wait_for_import         [Vertex AI Search ImportDocuments]
```

- **Chunk identity:** `chunk_id = f"{doc_id}_{chunk_index:05d}"` — used as the DataStore document ID, must be stable across re-ingestion.
- **Provenance override:** `doc_id`, `page_start`, `page_end`, `chunk_index` are always overridden from the `Chunk`, never trusted from Gemini output. `source_file` is overridden in `batch_ingest.py:107`.
- **Failure posture:** metadata generation never hard-fails — `metadata_gen.generate` falls back to `_fallback_extraction(chunk)` on any Gemini/JSON error. Failures are counted (`n_metadata_failures`) but do not abort the file.
- **Manifest:** `.ingestion_manifest.json` (basename → doc_id), written atomically. Re-runs skip files already present unless `--force`. No manifest today ⇒ first ingest processes all 5 corpus PDFs.

## 2. Vocabulary dependency (the important cross-cut)

`metadata_gen.py` builds the extraction prompt from the schema it loads: the `properties` JSON, an enum legend (`_enum_legend` via `SchemaVocabulary`), and `_extraction_guidance()` which pulls `notes.domain_vs_modality`, `notes.routing_safety`, plus a `missingness` instruction.

- **#NOTE(schema-wired)** It loads `config/metadata_schema.json` (37 fields) — see `config/dev_document.md §2`. So ingestion currently elicits ASA + provenance fields and reads the **stale `notes.routing_safety`** and a `missingness` inference instruction into the prompt.
- **#TODO** When the config-layer `#TODO(stale-notes)` and `#TODO(schema-migration)` land, this prompt text changes automatically (it is schema-derived) — no ingestion code change needed, but re-verify `_extraction_guidance()` doesn't reference notes that were deleted (it calls `notes.get(...)` with defaults, so deletion degrades gracefully to empty strings — confirm).

## 3. Known gaps / defects

- **#PARTIAL(front-matter)** `chunk_config.yaml` defines `skip_doc_types` and `front_matter_indicators`. Only `skip_doc_types` is consumed — `batch_ingest.py:114` filters chunks whose `metadata.doc_type ∈ skip_doc_types` (e.g. `front_matter`). But **`front_matter_indicators` is never used by `ContextAwareChunker`** — there is no structural front-matter pre-tagging. Front matter is only dropped if Gemini happens to tag it `front_matter`, which is unreliable. This is the "junk passages" risk the clinician doc flags.
  - **#NOTE** `rta_v1.json` `doc_type` enum has **no `front_matter` value** (only `treatment_manual/textbook/clinical_guideline/other`). So under a future migration to `rta_v1.json`, the `skip_doc_types: [front_matter]` filter would match nothing and drop no chunks. Front-matter handling must be redesigned before/with that migration.
- **#NOTE** `ingestion/watcher.py` is a superseded stub replaced by `scanner.py`; treat as dead (per `CLAUDE.md`).
- **#NOTE** No out-of-vocab validation gate at write time (arrays). `additionalProperties:false` blocks unknown keys, not out-of-vocab array members. `summary.md §3.3` specifies the post-extraction gate; not implemented.
- **#TODO** `generate_batch` is sequential with a fixed delay; `metadata_gen.py` notes >1000 chunks should move to Vertex AI Batch Prediction. Fine for the 5-PDF first ingest.

## 4. First-ingest readiness (for the test run)

Preconditions and the recommended sequence live in `ingestion/agentic_document.md §2` and `scripts/agentic_document.md`. Summary of the state:

- **#DONE** Pipeline code implemented and importable.
- **#DONE** 5 real PDFs staged in `corpus/`.
- **#TODO** GCP env not verified from here — requires `.env` populated and `scripts/setup_vertex_search.py` run (DataStore + schema registration) **before** first import.
- **#TODO(schema-migration)** Decide the ingest schema first (`config/agentic_document.md §2`). A first ingest inherits whichever schema the code loads.

## 5. Review points (kept current)

- **#PARTIAL(front-matter)** Owner: ingestion dev. Done = `front_matter_indicators` wired into the structural pass OR a documented decision to rely on doc_type + a front-matter redesign compatible with the target schema.
- **#TODO(write-validation)** Owner: ingestion dev. Done = post-extraction enum/pairing validation with a QA-queue route (`summary.md §3.3`).
- **#TODO(schema-migration)** tracked in `config/`; ingestion is a downstream consumer.

---

## Staleness note

- Re-verify §2 (which schema the prompt uses) against `settings.metadata_schema_path` each session.
- The front-matter gap (§3) interacts with the schema migration — recheck when `rta_v1.json` becomes the loaded schema.
- Reconcile if `config/CHANGELOG.md` or a repo `CHANGELOG.md` gains a newer entry than the date above.
