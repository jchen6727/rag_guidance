# Discovery Engine API Comparison — Schema Field Indexing

How the Vertex AI Search (Discovery Engine) client-library surface you choose, and
the mechanism you use to register field indexing, affect this project's **metadata
structure**, **ingestion**, and **search / RAG** behavior.

All facts below were verified empirically against `google-cloud-discoveryengine==0.20.0`
(the installed version; requirements pin `>=0.11.11`).

---

## 1. The three client surfaces

The library ships three generated surfaces from one install:

| Import | `Schema` proto fields | `FieldConfig` type | `Schema.field_configs` |
|---|---|---|---|
| `discoveryengine_v1` (GA) | `name`, `struct_schema`, `json_schema` | **absent** | **absent** |
| `discoveryengine_v1beta` | `name`, `struct_schema`, `json_schema` | **absent** | **absent** |
| `discoveryengine_v1alpha` | `name`, `struct_schema`, `json_schema`, `field_configs` | **present** | present, but **`OUTPUT_ONLY`** |

This project uses **`discoveryengine_v1` (GA)** in `scripts/setup_vertex_search.py`,
`ingestion/indexer.py`, `retrieval/searcher.py`, and `scripts/verify_context.py`.
Every symbol the code touches (DataStore / Schema / Engine creation, `ImportDocuments`,
`ListDocuments`, `SearchService.Search`) exists identically on all three surfaces, so
nothing here needs beta or alpha. See CHANGELOG 2026-07-09 (f) for the v1beta→v1 switch.

---

## 2. Two ways to configure field indexing — only one is writable

### 2a. `FieldConfig` objects (v1alpha only) — **NOT usable for registration**

The originally-proposed code:

```python
from google.cloud.discoveryengine_v1alpha import types as discoveryengine_alpha

config = discoveryengine_alpha.FieldConfig(
    filterable=discoveryengine_alpha.FieldConfig.FilterableOption.FILTERABLE_ENABLED,
    retrievable=discoveryengine_alpha.FieldConfig.RetrievableOption.RETRIEVABLE_ENABLED,
    searchable=discoveryengine_alpha.FieldConfig.SearchableOption.SEARCHABLE_ENABLED,
)
```

fails for **three** independent reasons:

1. **`filterable` is not a field.** Constructing this raises
   `ValueError: Unknown field for FieldConfig: filterable`. The real proto fields are
   `field_path` (Required), `field_type` (Output only), `indexable_option`,
   `searchable_option`, `retrievable_option`, `dynamic_facetable_option`,
   `completable_option`, `recs_filterable_option`, `key_property_type`.
2. **"Filterable" in Search = `indexable_option`.** The docstring for `indexable_option`:
   *"field values are indexed so that it can be filtered or faceted in
   SearchService.Search."* The `FilterableOption` enum that exists belongs to
   `recs_filterable_option`, which is a **Recommendations** filter — a different product
   surface, not Search.
3. **`Schema.field_configs` is `OUTPUT_ONLY`.** It is a read-back of the configuration
   the server *derived* from the schema document; it is ignored/rejected as an input to
   `UpdateSchema`. `FieldConfig.field_type` is likewise `OUTPUT_ONLY`.

A *correctly* constructed alpha `FieldConfig` (for reference only — still not writable):

```python
fc = discoveryengine_alpha.FieldConfig
config = discoveryengine_alpha.FieldConfig(
    field_path="domain",
    indexable_option=fc.IndexableOption.INDEXABLE_ENABLED,     # ← "filterable"
    retrievable_option=fc.RetrievableOption.RETRIEVABLE_ENABLED,
    searchable_option=fc.SearchableOption.SEARCHABLE_ENABLED,
)
```

Because `field_configs` is output-only, this object still cannot be submitted to
register indexing. **Moving to v1alpha buys nothing for this project.**

### 2b. `json_schema` annotations (GA) — **the mechanism we use**

Indexing is configured by embedding keywords **inside the schema document** and
submitting it as `Schema.json_schema`. This is what `_annotate_schema_for_indexing()`
in `scripts/setup_vertex_search.py` produces. Per-property keywords:

| Keyword | Effect | Applied to |
|---|---|---|
| `retrievable: true` | field is returned on the result document | every field (needed for citations + `ChunkMetadata` round-trip) |
| `indexable: true` | field is usable in AIP-160 **filter expressions** and facets ("filterable") | every field except `missingness` |
| `searchable: true` | field contributes to full-text search | **string leaves only** (not integer/number/boolean) |

For `type: array` fields the keywords attach to the **element (`items`)** leaf, e.g.:

```jsonc
"therapeutic_modality": {
  "type": "array",
  "items": { "type": "string", "enum": ["CBT", "DBT", ...],
             "retrievable": true, "indexable": true, "searchable": true }
}
```

This is the step that closes the "array fields not filterable" gap (DISCREPANCIES.md).

---

## 3. Effect on **metadata structure**

- The 37-field `metadata_schema.json` (`config/schema_loader.py::SchemaVocabulary`) is
  the single source of truth. `_annotate_schema_for_indexing()` deep-copies it and layers
  the indexing keywords on top — the source schema is never mutated, and the controlled
  vocabulary (enums, array membership, defaults) is untouched.
- **Scalars** (`domain`, `doc_type`, `page_start`, `year_published`, …) get their keywords
  on the property node. **16 array fields** get theirs on the `items` node, so each array
  element value becomes an individually-filterable token.
- **`missingness` is intentionally `retrievable` only, not `indexable`** — per
  `notes.vertex_ai_search` it is informational (surfaced alongside results) and is not a
  filter dimension. This keeps it out of the filterable-field budget.
- Result of the current schema: **36 indexable**, **28 searchable** (string leaves),
  **37 retrievable** fields.

---

## 4. Effect on **ingestion**

Ingestion is a **single batch event**, which is why the registration mechanism matters:

```
setup_vertex_search.py  (register schema ONCE, before any import)
        │   create DataStore → register annotated json_schema → create Engine
        ▼
batch_ingest.py  →  one ImportDocuments LRO over corpus/  →  DataStore
```

- **Registration is pre-import and one-time.** The annotated `json_schema` is submitted by
  `register_schema()` before `batch_ingest.py` runs the single `ImportDocuments`. Fields
  not marked `indexable` at this point are stored but never filterable.
- **Schema is effectively immutable for the corpus lifetime.** Changing metadata (adding a
  filter field, re-tagging) requires `purge_datastore.py --confirm` → clear GCS/DataStore →
  full re-ingest with new JSON tags. There is no per-document upsert (`indexer.py`), and
  chunks imported *before* schema registration silently drop unregistered fields
  (`CLAUDE.md`, GCP Resource Order Dependency).
- **Implication:** getting the annotation set correct up front is the entire game. Because
  it is a single schema-document operation, the GA `json_schema` path expresses everything
  in exactly the one step this architecture uses — there is no runtime or per-document
  config call that a v1alpha `FieldConfig` object could contribute to.

---

## 5. Effect on **search / RAG**

- **Server-side pre-filtering is the point.** The query path (`retrieval/searcher.py`,
  currently stubbed) narrows the corpus with AIP-160 filter expressions before ranking,
  e.g. scalar `domain = "dialectical_behavior"` and array
  `therapeutic_modality: ANY("DBT")` / `session_event_tags: ANY("crisis")`. These only work
  if the referenced fields are `indexable`.
- **Without array-field registration (the old bug):** filters over `therapeutic_modality`,
  `session_event_tags`, `risk_dimension_tags`, `clinical_presentation`, etc. match nothing
  or error, so retrieval collapses to unscoped full-text search. `BOOTSTRAP.md`: this is
  the condition under which "the RTA event filter does not function." For a system meant to
  keep guidance inside a clinician's trained modality (RTA/ASA), that is a
  clinical-safety-relevant regression, not a cosmetic one.
- **Retrievable vs. filterable:** even under the old bug the array *values* were returned
  (they were retrievable), so post-hoc client-side filtering was technically possible — but
  that means retrieving-then-discarding, with no ability to bound `top_k` to the correct
  subset before ranking. Precision/recall on scoped queries suffer and cost rises.
- **`missingness` in RAG:** returned with results (retrievable) so the generator can surface
  representation gaps, but never a filter dimension — matching its informational role.
- **Citations:** `retrievable` on all fields lets `_parse_metadata` reconstruct
  `ChunkMetadata` (incl. `page_start`/`page_end`) from `structData`, which
  `CitationBuilder` needs for page-level citations (Vertex grounding does not return pages).

---

## 6. Front-end → Discovery Engine interaction (RTA)

This section traces how a front-end signal becomes a Discovery Engine query so that the
**RTA (real-time, in-session) prompt is grounded on only the correct documents**. Two signal
sources drive RTA: an **explicit therapist selection** and a **lightweight monitor event**.
Both resolve to the same thing — a set of AIP-160 **pre-filters** applied to
`SearchService.Search` — which is only possible because the referenced metadata fields were
registered `indexable` (§2b, §3).

### 6.1 The pipeline

```
Front-end signal                       Discovery Engine                         Prompt
─────────────────                      ────────────────                         ──────
therapist picks "CBT / depression"  ┐
                                    ├─► SearchFilter ─► _build_filter_expression ─► filter=
lightweight monitor: "rupture"      ┘        (retrieval/searcher.py)                 │
                                                                                     ▼
                                             CorpusSearcher.search(query, top_k, filters)
                                                       │  (indexable fields only)
                                                       ▼
                                             ranked SearchResult[]  (retrievable fields)
                                                       │
                                                       ▼
                                    PromptBuilder: persona = domain, {n_passages} injected,
                                    retrieval_instruction_rta block  ──►  ResponseGenerator
```

### 6.2 Explicit selection — "this session is CBT for depression"

The therapist's picker values map to metadata **filters**, not free-text. `SearchFilter`
(today scalar-only) is extended for the chunk-level array fields, and the searcher emits an
AIP-160 pre-filter:

```
therapeutic_modality: ANY("CBT") AND clinical_presentation: ANY("depression")
    AND corpus_scope != "asa_only" AND target_audience != "patient"
```

- `therapeutic_modality: ANY("CBT")` and `clinical_presentation: ANY("depression")` are the
  scope: only chunks tagged with that modality **and** presentation are eligible. `ANY(...)`
  is the repeated-field membership operator — it works **only because array fields are now
  `indexable`** (the fix in §2b; before, this clause matched nothing).
- `domain` (document-level) is passed to `PromptBuilder`, which selects the persona
  (`cognitive_behavioral` → the CBT persona; a miss falls back to `psychotherapy_general`).
  So the *retrieved passages* and the *voice/scope of the answer* are both bound to CBT.

### 6.3 Monitor event — "a therapeutic rupture is detected"

A lightweight in-session monitor emits an event tag rather than a query. That tag is a value
in the `session_event_tags` enum, and the front-end turns it into an additional pre-filter,
combined with the still-active session scope from §6.2:

```
session_event_tags: ANY("rupture_withdrawal", "rupture_repair")
    AND therapeutic_modality: ANY("CBT")
    AND corpus_scope != "asa_only" AND target_audience != "patient"
```

- The monitor detects a *rupture* → the filter narrows to chunks that actually discuss rupture
  withdrawal/repair, so the RTA guidance is about **repairing the alliance now**, not generic
  CBT content. A detected `crisis_escalation` would instead pull `session_event_tags:
  ANY("crisis_escalation")` and, if the monitor also flags risk, `risk_dimension_tags:
  ANY("suicide_ideation_chronic")` — routing the prompt to safety material.
- Event → tag → filter is deterministic; the monitor never has to phrase a query, and the
  event can only ever retrieve documents that were tagged for that event.

### 6.4 The two hard RTA pre-filters (non-negotiable)

Per `metadata_schema.json` `notes.routing_safety`, these are **correctness constraints**, not
ranking hints — they are always ANDed into every RTA filter:

- **`corpus_scope != "asa_only"`** — after-session-only material must never enter a real-time
  in-session answer.
- **`target_audience != "patient"`** — patient-facing handouts are excluded from all retrieval
  **except** the `analysis_function = "homework_resource"` path.

Because these are `indexable` scalar fields, they are enforced server-side *before* ranking, so
excluded documents never even reach the prompt. Implementing them as ranking penalties instead
would be a safety defect.

### 6.5 Why this guarantees "correct documents only"

The RTA prompt is assembled from `top_k` `SearchResult`s that already passed the pre-filter, so
the `retrieval_instruction_rta` block (with `{n_passages}` = the count) can only cite in-scope,
in-modality, event-appropriate, audience-safe passages. The correctness chain is:
**indexable metadata → server-side pre-filter → bounded result set → grounded prompt.** Break
the first link (a field not registered `indexable`, or a chunk mis-tagged at ingestion) and the
filter silently admits the wrong documents or drops the right ones — see `presentation.md`.

---

## 7. Decision & rationale

| Option | Verdict |
|---|---|
| Stay on v1beta with `FieldConfig` | ✗ `FieldConfig`/`field_configs` don't exist in v1beta |
| Switch to v1, keep `FieldConfig` | ✗ same — absent in v1; raises `AttributeError` |
| Move to **v1alpha**, submit `FieldConfig` objects | ✗ `Schema.field_configs` is `OUTPUT_ONLY`; not writable. Also relies on a preview surface |
| **Stay on v1 (GA), annotate `json_schema`** | ✓ **chosen** — GA-stable, single pre-import step, covers scalars + arrays, no preview dependency |

**Chosen:** GA `discoveryengine_v1` + `json_schema` indexing annotations
(`_annotate_schema_for_indexing()`), which fits the single-batch ingestion model exactly
and requires no alpha/beta surface.

---

## 8. Constraints & gotchas

- `searchable` is valid only for **string** leaves; do not set it on integer/number/boolean
  (the annotator guards this).
- Discovery Engine enforces per-datastore limits on the count of indexable/searchable/
  retrievable fields; 37 fields is well within them, but adding many more may hit a cap.
- Schema edits are **not retroactive** — they require purge + full re-ingest.
- Regional endpoint routing still applies (`_client_options()`); an unmatched
  `GCP_LOCATION` sinkholes regardless of API surface (CHANGELOG 2026-07-09 (e)).
- If the future query path needs a genuinely preview-only capability (certain
  `SearchRequest.ContentSearchSpec` summary/answer options), scope the v1beta/v1alpha import
  to *that* client only; keep provisioning + ingestion on v1.
