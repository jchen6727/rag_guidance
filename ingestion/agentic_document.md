# ingestion/ — Agentic Instructions (Internal-Facing)

**Audience:** automated (agentic) developers. Full operational detail.
**Precondition:** ingest `/ORCHESTRATOR.md` first; then `config/agentic_document.md §2` (schema decision) before any real ingest.
**Last reconciled:** 2026-07-20.

---

## Handoff log (newest first)

### 2026-07-20 — RTA schema migration landed (ingestion is a consumer)
- The active schema is now `config/rta_v1.json` (23 fields). `metadata_gen` loads it via `settings.metadata_schema_path`; `_extraction_guidance()` rewritten to `directionality`+`applies_when`. No structural pipeline change (extractor/chunker/uploader/indexer unchanged).
- `#TODO(front-matter)[2026-07-20]` **elevated to live:** `skip_doc_types: [front_matter]` is now a no-op (rta_v1 has no `front_matter` doc_type) — front matter will index unless mitigated. See `dev_document.md §3`.
- **Next agent should:** run the first-ingest dry-run (§2) and inspect front-matter leakage + metadata-failure rate before any real ingest.

### 2026-07-20 — orchestrator bootstrap
- Created this triad. No pipeline code changed.
- Verified pipeline is importable and 5 PDFs are staged; no manifest exists (first ingest is first).
- Left open (now updated above): schema decision (resolved), front-matter, `#TODO(write-validation)`.

`<!-- ▲ latest handoff above ▲ -->`

---

## 1. Operating rules

1. Do not treat `raise NotImplementedError` in `retrieval/`, `generation/`, `rta_prompt/` as bugs — the query path is intentionally stubbed. This directory (ingest) is implemented.
2. `ingestion/watcher.py` is dead (superseded by `scanner.py`). Do not extend it.
3. Ingestion inherits its vocabulary from whatever schema the code loads. Never hard-code enums here.
4. `chunk_id = f"{doc_id}_{chunk_index:05d}"` is the DataStore document ID — never change its shape; re-ingestion depends on stability.
5. Provenance fields (`doc_id`, `page_start`, `page_end`, `chunk_index`, `source_file`) are authoritative from the `Chunk`, not Gemini — preserve those overrides.

## 2. First-ingest runbook (execute in order)

```bash
# 0. Schema decision is RESOLVED: active schema = config/rta_v1.json (config/agentic_document.md §2).

# 1. Env + provisioning (once). Requires populated .env.
cp .env.example .env          # then populate GCP_PROJECT_ID, GCS_BUCKET_NAME, VERTEX_SEARCH_* , GCP_LOCATION
PYTHONPATH=. python scripts/setup_vertex_search.py --dry-run   # preview schema/datastore
PYTHONPATH=. python scripts/setup_vertex_search.py             # create datastore + register schema

# 2. Dry-run ingest — exercises extract→chunk→metadata WITHOUT upload/index.
PYTHONPATH=. python scripts/batch_ingest.py --dry-run

# 3. Inspect dry-run output: chunk counts per file, metadata-failure counts, any junk/front-matter chunks.

# 4. Real ingest (only after dry-run looks sane).
PYTHONPATH=. python scripts/batch_ingest.py

# 5. Verify import counts (success/failed) in the summary table; check .ingestion_manifest.json was written.
```

- **Order dependency:** `setup_vertex_search.py` (register schema) MUST precede `batch_ingest.py`. Chunks indexed before schema registration silently drop unregistered metadata fields (`CLAUDE.md`, `summary.md §4.4`). It registers the active schema (`rta_v1.json`), so `applies_when`/`directionality`/`clinical_measure_tags` are now among the registered filterable fields.
- `#NOTE(state-vocab-values)[2026-07-20]` The `applies_when` state values are provisional (clinician Q2). Adding values later is additive (no purge), but chunks tagged before the change won't carry new values until re-ingested.

## 3. What to watch during the first ingest

- **Metadata failures > 0** → Gemini/JSON errors; those chunks got `_fallback_extraction`. Inspect a few — fallback tags are minimal and may under-label. Not fatal, but note the rate.
- **Front-matter leakage** → `front_matter_indicators` is not wired (`dev_document.md §3`); title/TOC/index pages may be indexed. Spot-check the first chunks of each PDF. If severe, wire front-matter detection before a production ingest.
- **Filterable-array registration** → after `setup_vertex_search.py`, confirm every array field that retrieval will filter on is registered; an unregistered filterable array fails silently at query time.
- **Import LRO errors** → `wait_for_import` surfaces up to 5 error samples; capture them in the handoff log.

## 4. Task queue

- `#TODO(write-validation)[2026-07-20]` Implement the `summary.md §3.3` post-extraction gate: reject out-of-vocab array values, enforce `directionality`↔`applies_when` pairing, route failures to a QA queue (not the index). High-stakes ⇒ MIU required.
- `#TODO(front-matter)[2026-07-20]` Wire `front_matter_indicators` into `ContextAwareChunker`'s structural pass, or redesign front-matter handling for the `rta_v1.json` doc_type set (which has no `front_matter`). Coordinate with `config/`.
- `#TODO[2026-07-20]` If chunk volume grows >1000, switch `generate_batch` to Vertex AI Batch Prediction.

## 5. Update-on-exit checklist

- [ ] Append a dated Handoff log entry (what ran, counts, errors, next step).
- [ ] Flip completed `#TODO → #DONE` here and in `dev_document.md` with a changelog date.
- [ ] If a run produced sample chunks worth clinician review, prepare the sample and update `clinical_document.md §4` (plain language, no code symbols, no GCP resource names).
- [ ] Record the schema actually used for the run in `config/CHANGELOG.md`.

---

## Staleness note

- Re-verify §2 preconditions (env, schema decision) each session — they gate correctness of any ingest.
- The front-matter and write-validation gaps are open; do not assume they are handled.
- Reconcile if a newer `CHANGELOG.md` entry exists than the date above.
