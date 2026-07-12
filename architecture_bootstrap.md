# Architecture Bootstrap — Instructions for Implementing Agents

Authoritative, action-oriented reconciliation of `DISCREPANCIES.md` for anyone
(human or agent) continuing this project. Read this **before** touching
`scripts/setup_vertex_search.py`, `retrieval/searcher.py`, or the schema. It
records the decisions already made, the ones still open, and the exact
verification gate before the one-and-only corpus ingest.

Companion docs: `metadata_summary.md` (risk catalogue with clinician + technical
framing), `discovery_engine_comparison.md` (API-surface analysis),
`config/metadata_schema.json` (source of truth for the vocabulary).

---

## 0. Two documents conflict. This one wins on the array question.

`schema_notes.md` and `discovery_engine_comparison.md` give **opposite**
instructions for where per-field indexing flags go on `type: array` fields:

| Source | Array flag placement | Correct? |
|---|---|---|
| `schema_notes.md` §"Strict Array Constraint" | property level, **never** inside `items` | ❌ **Wrong** |
| `discovery_engine_comparison.md` §2b + shipped code | inside the `items` leaf | ✅ **Right** |

Google's live documentation (*Configure field settings*, *Provide or auto-detect
a schema*) shows array flags **inside `items`** (the `amenities` example). The
project verified the same empirically against `google-cloud-discoveryengine==0.20.0`.

**Directive:** For arrays of primitives, put `retrievable`/`indexable`/
`searchable` inside `items`. Treat `schema_notes.md` §"Strict Array Constraint"
as **incorrect and superseded**. The rest of `schema_notes.md` (valid flag list,
vector-embedding `dimension` rule, nested-object leaf placement, system key
fields) is fine. Do **not** "fix" `_create_discoveryengine_schema()` to match
`schema_notes.md`'s array rule — that would silently kill every list-tag filter
(`therapeutic_modality`, `session_event_tags`, `clinical_presentation`,
`risk_dimension_tags`, ...) and break the RTA event filter. This is
clinical-safety-relevant, not cosmetic.

`schema_notes.md` should be annotated or corrected so a future agent does not
re-introduce the bug (left as an editorial action, not done here to preserve the
original reference verbatim).

---

## 1. Done and verified (removed from `DISCREPANCIES.md` this pass)

Confirmed present/correct in the codebase; the corresponding `#DONE` bullets were
deleted from `DISCREPANCIES.md`:

- `ingestion/watcher.py` deleted (file absent; `ingestion/__init__.py` imports
  only `scanner`).
- `ingestion/requirements.txt` no longer references `CorpusWatcher.catchup_scan()`.
- `ingestion/metadata_gen.py` — biomedical constants `_VALID_DOMAINS`/
  `_VALID_DOC_TYPES`/`_VALID_EVIDENCE_LEVELS` gone; `_validate_and_coerce()`
  delegates to `SchemaVocabulary.coerce()`; prompt is schema-derived; fallback
  drops `entities`/`evidence_level`.
- `models.py::ChunkMetadata` mirrors all 37 schema fields; `entities` /
  `evidence_level` removed.
- Array fields registered filterable via the schema-annotation path (now folded
  into `_create_discoveryengine_schema()`).

## 2. Changed this pass

- **`scripts/setup_vertex_search.py`** — `_annotate_schema_for_indexing()`
  replaced by **`_create_discoveryengine_schema()`**, which (a) keeps the correct
  `items`-leaf annotation for arrays and (b) additionally **collapses nullable
  union types** (`["string","null"]` / `["integer","null"]`) to a single
  concrete type via `_concrete_type()`, because Discovery Engine rejects a
  list-valued `type`. Affects `year_published`, `sample_size`,
  `practice_recommendation_level`, `training_level_required`, `study_type`. The
  emitted document is a clean field-config schema (`$schema`, `type`,
  `properties`, `required`); source-schema `notes`/`additionalProperties`/`title`/
  `description` scaffolding is dropped. `register_schema()` now calls it.

---

## 3. Open items — require a decision or implementation (migrated from `DISCREPANCIES.md`)

Ordered by blast radius. Items 3.1–3.2 gate ingestion correctness; 3.3–3.5 gate
the query path.

### 3.1 `doc_type` `""` sentinel is not an enum member — **decide before ingest**
Unknown `doc_type` coerces to `""`, absent from the schema enum. Choose one and
apply consistently in `SchemaVocabulary` + any query-time `doc_type` filter:
- (a) add an `other`/`unknown` enum member and default to it, or
- (b) keep `""` and document that all `doc_type` filtering must be exclusion-based
  (`doc_type != "front_matter"`), never `doc_type = <member>` equality that
  assumes coverage.
Recommendation: (a) — an explicit `other` member is filter-safe and removes the
"empty string that isn't in the enum" foot-gun. Note this touches the schema, so
it must land before the one-shot ingest.

### 3.2 Front-matter filtering is not wired — **decide before ingest**
`ChunkerConfig.skip_doc_types` / `front_matter_indicators` are loaded but unused
by `ContextAwareChunker`. Either wire them into the structural splitter so
front-matter chunks are skipped at ingestion, **or** commit to a query-time
`doc_type != "front_matter"` pre-filter — but (b) depends on Gemini reliably
assigning `front_matter`, which 3.1's `""` sentinel undercuts. Prefer wiring the
chunker; it removes the dependency on extraction accuracy for a safety-adjacent
exclusion.

### 3.3 `retrieval/searcher.py::_parse_metadata` must round-trip all 37 fields
When implementing the query path, reconstruct `ChunkMetadata` (incl. the 16 array
fields) from the flat `structData` dict returned on results. Every field is
`retrievable`, so the data is present; the parser must handle arrays and the
nullable scalars. Deferred until the query path is built.

### 3.4 `SearchFilter` must gain array-membership support + the two hard pre-filters
`SearchFilter` is scalar-only today. Extend it and `_build_filter_expression` to
emit AIP-160 `ANY(...)` clauses for array fields, and to **always** AND-in the
non-negotiable safety pre-filters:
```
corpus_scope != "asa_only" AND target_audience != "patient"
```
These are **pre-filters, not ranking penalties** (`notes.routing_safety`). The
`homework_resource` path is the only documented exception for
`target_audience = "patient"`. Implementing either as a boost is a safety defect.

### 3.5 RTA event routing is deterministic only if tags exist
`event → tag → filter` is only as reliable as ingestion tagging. `session_event_tags`
defaults to `["none"]` and coercion drops near-miss tokens (see
`metadata_summary.md` §3). Add a labeling spot-check / eval on a representative
sample **before** the one-shot ingest; re-tagging costs a full re-ingest.

### 3.6 Minor / documented (leave as-is unless touched)
- `domain` invalid → coerces to `other`; persona fallback token is
  `psychotherapy_general`. Both route to the default persona. No action.
- `ChunkMetadata` relaxes schema `required` by design (fallback must not
  hard-fail). No action.
- Doc drift already noted in `DISCREPANCIES.md` (`ingestion/README.md`
  ChunkerConfig table, uploader `_serialize_chunk` sample, `caveats.md`
  `evidence_level`). Low priority; fix opportunistically.

---

## 4. Verification gate — run before the single `batch_ingest.py`

The schema is immutable for the corpus lifetime. Do all of this first:

1. **Dry-run + read the emitted JSON.**
   `PYTHONPATH=. python scripts/setup_vertex_search.py --dry-run` and confirm the
   logged schema shows, for every array field, flags on the `items` node and
   **no** list-valued `type` anywhere.
2. **Live smoke test on a throwaway DataStore.** Register the schema, import 2–3
   representative chunks, then issue a `SearchService.Search` with
   `filter="session_event_tags: ANY(\"rupture_repair\")"` and a `facetSpec` on
   `therapeutic_modality`. If the filter returns the tagged chunk and the facet
   enumerates values, `indexable` placement is correct. If it errors or returns
   empty, placement is wrong — do **not** proceed to the real ingest.
3. **Confirm the two safety pre-filters** exclude `asa_only` / `target_audience =
   patient` chunks server-side (add one of each to the smoke set).
4. **Tagging eval** (3.5) on a labeled sample; check `session_event_tags`,
   `therapeutic_modality`, `clinical_presentation` precision/recall.
5. Only then run `preflight_check.sh` → `setup_vertex_search.py` →
   `batch_ingest.py`.

---

## 5. DO / DON'T for agents

- **DO** treat `config/metadata_schema.json` (+ `SchemaVocabulary`) as the single
  source of truth for the vocabulary; never hard-code enums.
- **DO** keep indexing config inside the `json_schema` document; there is no
  writable `FieldConfig` path (`Schema.field_configs` is `OUTPUT_ONLY`).
- **DO** put array flags on `items` (§0).
- **DON'T** follow `schema_notes.md`'s array-flag rule.
- **DON'T** implement `corpus_scope` / `target_audience` exclusions as ranking
  signals.
- **DON'T** change the schema after ingest without a full purge + re-ingest.
- **DON'T** trust Gemini for provenance fields (`doc_id`/`page_*`/`chunk_index`);
  they are always overridden from the `Chunk`.
