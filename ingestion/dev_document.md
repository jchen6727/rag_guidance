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

`metadata_gen.py` builds the extraction prompt from the schema it loads: the `properties` JSON, an enum legend (`_enum_legend` via `SchemaVocabulary`), and `_extraction_guidance()`.

- `#DONE(schema-wired)[2026-07-20]` It now loads `config/rta_v1.json` (23 fields) via `settings.metadata_schema_path`. `_extraction_guidance()` was rewritten to the `directionality`+`applies_when` model (removed the `missingness`/`practice_recommendation_level`/`routing_safety` prompt text). Enum legend now includes the constrained `applies_when` vocabulary, so Gemini is told the allowed state/event/presentation tokens. Cross-ref `config/dev_document.md §2`.
- `#NOTE[2026-07-20]` The prompt is schema-derived, so future enum/description edits in `rta_v1.json` flow through automatically — but re-verify `_extraction_guidance()` after any `notes` key rename (it uses `notes.get(...)` with defaults, so a missing key degrades to empty, not an error).

## 3. Known gaps / defects

- `#TODO(front-matter)[2026-07-20]` **Live gap since the migration.** `rta_v1.json` `doc_type` has **no `front_matter` value** (only `treatment_manual/textbook/clinical_guideline/other`), so `chunk_config.yaml`'s `skip_doc_types: [front_matter]` filter at `batch_ingest.py:114` now matches nothing — **front matter is no longer dropped at all.** (Separately, `front_matter_indicators` was never wired into `ContextAwareChunker`, so there is no structural pre-tagging either.) Mitigation options: (a) add a structural front-matter pass keyed on `front_matter_indicators`; (b) re-introduce a `front_matter` doc_type/skip mechanism compatible with `rta_v1.json`; or (c) accept leakage for the first run and spot-check. Decide before a production ingest.
- `#NOTE[2026-07-20]` `ingestion/watcher.py` is a superseded stub replaced by `scanner.py`; treat as dead (per `CLAUDE.md`).
- `#NOTE(write-validation)[2026-07-20]` No out-of-vocab validation gate at write time (arrays). `additionalProperties:false` blocks unknown keys, not out-of-vocab array members. `summary.md §3.3` specifies the post-extraction gate; not implemented.
- `#TODO[2026-07-20]` `generate_batch` is sequential with a fixed delay; `metadata_gen.py` notes >1000 chunks should move to Vertex AI Batch Prediction. Fine for the 5-PDF first ingest.

## 4. First-ingest readiness (for the test run)

Preconditions and the recommended sequence live in `ingestion/agentic_document.md §2` and `scripts/agentic_document.md`. Summary of the state:

- `#DONE[2026-07-20]` Pipeline code implemented and importable.
- `#DONE[2026-07-20]` 5 real PDFs staged in `corpus/`.
- `#DONE(schema-migration)[2026-07-20]` Active schema resolved = `config/rta_v1.json` (`config/agentic_document.md §2`). The first ingest will tag against it.
- `#TODO[2026-07-20]` GCP env not verified from here — requires `.env` populated and `scripts/setup_vertex_search.py` run (DataStore + schema registration) **before** first import.

## 5. Review points (kept current)

- `#TODO(front-matter)[2026-07-20]` Owner: ingestion dev. Live gap: `skip_doc_types` is a no-op under `rta_v1.json` (no `front_matter` doc_type) and `front_matter_indicators` was never wired. Done = a front-matter pass wired into the structural split OR a documented accept-and-spot-check decision.
- `#TODO(write-validation)[2026-07-20]` Owner: ingestion dev. Done = post-extraction enum/pairing validation with a QA-queue route (`summary.md §3.3`). High-stakes ⇒ MIU required.
- `#DONE(schema-migration)[2026-07-20]` Ingestion consumes `rta_v1.json`; verified end-to-end.

---

## Staleness note

- Re-verify §2 (which schema the prompt uses) against `settings.metadata_schema_path` each session.
- The front-matter gap (§3) interacts with the schema migration — recheck when `rta_v1.json` becomes the loaded schema.
- Reconcile if `config/CHANGELOG.md` or a repo `CHANGELOG.md` gains a newer entry than the date above.
