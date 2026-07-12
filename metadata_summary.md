# Metadata & Retrieval Pipeline — Implementation Risks

Scope: problems that can arise when wiring **keyword → corpus retrieval** for the
RTA (real-time, in-session) path and the **ingestion tagging** that feeds it. The
target workflow is: a clinician (or a lightweight in-session monitor) selects a
**therapeutic modality**, a **clinical presentation**, and zero or more
**session event tags**; the searcher turns those into a server-side pre-filter;
Vertex AI Search returns only the chunks that match; the prompt is grounded on
that bounded set.

The whole guarantee rests on one chain:

> **indexable metadata → server-side pre-filter → bounded result set → grounded prompt**

Break the first link (a field not registered `indexable`, a nullable type the
schema server rejects, or a chunk mis-tagged at ingestion) and the filter
silently admits the wrong documents or drops the right ones. Because the corpus
is ingested as a **single immutable batch**, every error below is "baked in"
until a full `purge_datastore.py --confirm` + re-ingest.

Each section has a **For clinicians** explanation and a **Technical** section.

---

## 1. Array-field indexing flags must go *inside* `items` — `schema_notes.md` says the opposite

**This is the highest-severity item.** It is the difference between the RTA
event filter working and silently matching nothing.

### For clinicians

The most important tags in this system are lists: a page can be about *several*
modalities (`therapeutic_modality`), *several* in-session events
(`session_event_tags`), *several* risk dimensions (`risk_dimension_tags`). When
you say "this session is CBT for depression, and a rupture just happened," the
system filters the library down to pages tagged with those exact list values.

For that filter to work, the search engine has to be told **at setup time** that
those list tags are "filterable." There are two places one *could* write that
instruction into the setup file, and only one of them is correct. One of our
internal notes (`schema_notes.md`) tells us to write it in the wrong place. If we
follow that note, the setup will appear to succeed, but every list-tag filter
will match **zero pages** — so when a rupture is detected, the system falls back
to generic search and may surface off-modality or event-irrelevant material at
exactly the moment clinical precision matters most. It fails silently: nothing
errors, the results are just quietly wrong.

### Technical

Vertex AI Search / Discovery Engine configures per-field indexing with keywords
embedded **inside the schema document** (`retrievable`, `indexable`,
`searchable`, `dynamicFacetable`). `Schema.field_configs` is `OUTPUT_ONLY` on
every API surface (v1/v1beta/v1alpha), so there is no programmatic `FieldConfig`
path — this is settled (see `discovery_engine_comparison.md`, `CHANGELOG`
2026-07-10).

The open question is **placement for `type: array` fields**. Two repo documents
disagree:

- `schema_notes.md` → *"CRITICAL ERROR TO AVOID: Never place `retrievable`,
  `indexable`, or `searchable` inside the nested `items` block of an array. …
  Array field flags must reside at the property level."*
- `discovery_engine_comparison.md` §2b and the shipped code → flags go on the
  **`items` leaf**.

Google's live documentation resolves it decisively **in favor of `items`**. From
*Configure field settings* (`generative-ai-app-builder/docs/configure-field-settings`),
the documented example for an array field:

```json
"amenities": {
  "type": "array",
  "items": {
    "completable": true,
    "dynamicFacetable": true,
    "indexable": true,
    "retrievable": true,
    "searchable": true,
    "type": "string"
  }
}
```

and from *Provide or auto-detect a schema*, `keyPropertyMapping` likewise sits
inside `items` for arrays. **`schema_notes.md`'s "Strict Array Constraint" is
inverted and must not be followed for arrays of primitives.** (It is also
internally inconsistent: its own "Document Hierarchy" section says nested leaves
inside `items` *do* take flags.)

Consequence of the wrong placement — the filter clause the RTA path emits,

```
therapeutic_modality: ANY("CBT") AND session_event_tags: ANY("rupture_repair")
```

references fields that Discovery Engine never registered as indexable, so `ANY()`
matches nothing (or errors), and retrieval collapses to unscoped full-text.

**Resolution in code** — `scripts/setup_vertex_search.py::_create_discoveryengine_schema()`
places flags on the correct leaf:

```python
if is_array:
    leaf = prop.setdefault("items", {})          # ← flags go here for arrays
    leaf["type"] = _concrete_type(leaf.get("type"))
else:
    leaf = prop
leaf["retrievable"] = True
if field_name not in _INFORMATIONAL_ONLY_FIELDS:
    leaf["indexable"] = True
    if leaf.get("type") == "string":
        leaf["searchable"] = True
```

Verified output (all 16 array fields): flags land on `items`, not the property.
**Before the one-shot ingest, confirm empirically** (dry-run logs the exact JSON;
better, register against a throwaway DataStore and issue a `facets`/`filter`
query on `session_event_tags`). See `architecture_bootstrap.md` §Verification.

---

## 2. Nullable union types (`["string","null"]`) are not a valid Discovery Engine `type`

### For clinicians

Several tags are optional — a clinical manual has no "sample size," a
theoretical paper has no "study type." In our design file we mark "optional" in a
way that Google's search engine doesn't understand. If we hand it over unchanged,
those optional fields can fail to register — meaning you couldn't filter or sort
by them (e.g. "show me the RCT-backed guidance for this population").

### Technical

`config/metadata_schema.json` uses JSON-Schema's nullable idiom,
`"type": ["string", "null"]` / `"type": ["integer", "null"]`, on five fields:
`year_published`, `sample_size`, `practice_recommendation_level`,
`training_level_required`, `study_type`.

Discovery Engine's schema requires `type` to be a **single** string
(`string`/`number`/`integer`/`boolean`/`array`/`object`/`datetime`/`geolocation`).
A JSON list is not accepted, and it also broke the old `searchable` gate:
`leaf.get("type") == "string"` is `False` for `["string","null"]`, so those
string fields silently missed full-text registration.

**Resolution** — `_concrete_type()` collapses the union to its base type before
annotation:

```python
def _concrete_type(json_type):
    if isinstance(json_type, list):
        non_null = [t for t in json_type if t != "null"]
        return non_null[0] if non_null else None
    return json_type
```

Verified: `year_published, sample_size → integer`;
`practice_recommendation_level, training_level_required, study_type → string`
(and now correctly `searchable`). No union types remain in the emitted schema.
Nullability itself is enforced upstream by `SchemaVocabulary` coercion, not by
the DataStore schema.

---

## 3. Tagging quality — not indexing config — is the real ceiling on event relevance

### For clinicians

Even with a perfect setup, the system can only find "rupture" guidance if the AI
that read the PDF **labeled** that passage as being about rupture. Every tag is
applied once, at ingestion, by an AI reading the page. If it misses the label, or
labels a rupture passage as "none," that passage becomes invisible to the rupture
filter forever (until we re-ingest). So "select an event → get the right pages"
is only as good as the labeling done up front, and the default when the AI is
unsure is *the empty/"none" label* — which errs toward invisibility, not toward
over-surfacing.

### Technical

The RTA event trigger is deterministic *given correct tags* (`event → tag →
filter`), but the tags come from a single Gemini pass per chunk
(`ingestion/metadata_gen.py`). Two schema defaults bias toward silent recall loss:

- `session_event_tags` default is `["none"]`. A passage that discusses a rupture
  but is not tagged defaults to `none` and never matches
  `session_event_tags: ANY("rupture_repair")`.
- `therapeutic_modality` / `clinical_presentation` default to `[]`. An untagged
  passage matches no modality/presentation pre-filter.

Coercion (`SchemaVocabulary._coerce_array`) *drops* any Gemini value not in the
enum rather than mapping it — good for precision, but a near-miss token
("rupture" vs `rupture_repair`) is discarded, not salvaged:

```python
item_enum = self.enum_values(field)
cleaned = [v for v in value if v in item_enum]   # unknown tokens dropped
return cleaned if cleaned else default            # falls back to ["none"] / []
```

Mitigations (for the ingestion owner): the extraction prompt already injects the
enum legend and RTA/ASA guidance (`_enum_legend`, `_extraction_guidance`); keep
`temperature=0.0`; consider a spot-check/eval harness on a labeled sample before
committing the one-shot ingest, since re-tagging requires purge + re-ingest.
Discovery Engine does **not** validate tags (see §7), so extraction is the only
quality gate.

---

## 4. Coercion defaults and relaxed `required` can mislabel rather than reject

### For clinicians

When the AI can't confidently classify a page, it stores a generic label instead
of refusing. That keeps ingestion from crashing, but a generically-labeled page
won't come up under a specific filter — and in one case it stores a label
("blank") that isn't even on the official list, which can make later filtering
behave oddly.

### Technical

`ChunkMetadata` intentionally relaxes the schema's `required` (gives defaults) so
`_fallback_extraction()` never hard-fails when Gemini is down (documented, by
design). Combined with coercion defaults this produces two edge cases already
tracked in `DISCREPANCIES.md`:

- **`doc_type` `""` sentinel is not an enum member.** Unknown `doc_type` coerces
  to `""` (legacy, to avoid filter-expression errors), but `""` is absent from
  the `doc_type` enum. Filters like `doc_type != "front_matter"` behave, but any
  logic keying on the enum set must treat `""` as "unknown." **Open decision**
  (add an `other`/`front_matter` sentinel vs. keep `""`) — see
  `architecture_bootstrap.md`.
- **`domain` invalid → `other`, but the persona fallback token is
  `psychotherapy_general`.** Both route to the default persona, so behavior is
  correct, but the two "fallback" tokens differ. Minor; documented.

---

## 5. Front-matter is not filtered out at chunking time

### For clinicians

Title pages, tables of contents, and copyright pages carry no clinical guidance,
but nothing currently stops them from being chunked, tagged, and indexed — so
they can surface in results.

### Technical

`ChunkerConfig.skip_doc_types` and `front_matter_indicators` are loaded from
`config/chunk_config.yaml` but **never consumed** by `ContextAwareChunker`
(`CLAUDE.md` Known Issue #1 residual; `DISCREPANCIES.md` "Chunking config"). The
schema's intent (`doc_type: front_matter` chunks "excluded from search") is not
enforced at ingestion. Two options: wire front-matter filtering into the chunker,
or rely on a query-time `doc_type != "front_matter"` pre-filter — but the latter
depends on Gemini actually assigning `front_matter`, which the `""` sentinel (§4)
undercuts.

---

## 6. The two hard safety pre-filters must be server-side, not ranking hints

### For clinicians

Two rules are non-negotiable: after-session-only material must **never** appear
during a live session, and patient-facing handouts must **never** appear except
in the homework workflow. These have to be hard exclusions, not "rank it lower" —
a down-ranked unsafe document is still a reachable unsafe document.

### Technical

Per `metadata_schema.json` `notes.routing_safety`, every RTA query must AND-in:

```
corpus_scope != "asa_only" AND target_audience != "patient"
```

Both are `indexable` scalar strings, so they are enforceable server-side *before*
ranking — which is required for correctness. The searcher
(`retrieval/searcher.py`, still stubbed) **must** implement these as pre-filters
in `_build_filter_expression`, never as boosts. This is a safety defect if done
as ranking. (`homework_resource` is the single documented exception path for
`target_audience = "patient"`.)

---

## 7. Discovery Engine does not enforce the enums — coercion is the only gate

### For clinicians

Google's search engine stores whatever labels we give it; it does not check them
against our official list. So the only thing keeping labels clean is our own
ingestion code.

### Technical

DE ignores JSON-Schema `enum`/`minimum`/`maximum`/`pattern` (it uses the schema
for *field configuration*, not *validation*). Enum membership, array
normalization, and integer parsing are enforced solely by
`SchemaVocabulary.coerce()` at ingestion. Implication: keeping the enums in the
emitted schema is documentation only; a bad tag that slips past coercion will be
indexed as-is and is filterable/greppable as a spurious value. All validation
effort belongs in `schema_loader.py` + the extraction prompt, not the DataStore.

---

## 8. One-shot, immutable ingestion raises the stakes on every item above

### For clinicians

There is no "edit one page's tags" button. Any fix to tags or setup means wiping
the whole library and re-loading it. So it is worth getting the setup and a
labeling spot-check right *before* the single big load.

### Technical

`setup_vertex_search.py` registers the schema **once**; `batch_ingest.py` runs a
single `ImportDocuments` LRO; there is no per-document upsert
(`ingestion/indexer.py`). Schema/tag changes require `purge_datastore.py
--confirm` → clear GCS/DataStore → full re-ingest. Chunks imported *before*
schema registration silently drop unregistered fields (`CLAUDE.md`, GCP Resource
Order Dependency). This is exactly why §1 (correct annotation) and §3 (tagging
eval) must be validated up front — the cost of being wrong is a full re-ingest.

---

## 9. Field-count limits

### Technical (no clinician impact unless the schema grows)

Discovery Engine caps the number of configured fields. Google docs (*Configure
field settings*): *"You can configure up to 50 fields as indexable, searchable,
retrievable, or dynamic facetable."* The current emitted schema is **37 fields
total** (37 retrievable, 36 indexable, 31 searchable). Under the standard reading
(≤ 50 distinct fields per setting) this is comfortably within limits. If Google's
wording is instead an aggregate cap across settings, verify against the live API
before adding fields. Either way, adding many more metadata fields could hit the
cap and should be validated with a dry-run registration.

---

## 10. Optional optimization: system key fields (`title`, `uri`, `description`, `categories`)

### Technical

`schema_notes.md` §"System Key Requirements" and Google's docs note that
enterprise search favors root fields `title`/`uri`/`description`/`categories`
and supports `keyPropertyMapping` to designate them. We have a `title` field;
mapping it via `keyPropertyMapping: "title"` would improve snippet/display and
citation quality. This is **not** implemented in `_create_discoveryengine_schema()`
to keep the immutable schema's behavior predictable — it is left as a documented,
reversible-only-by-re-ingest enhancement (see `architecture_bootstrap.md`).

---

## Summary table

| # | Problem | Severity | Status |
|---|---|---|---|
| 1 | Array flags must be inside `items`; `schema_notes.md` says the opposite | **Critical** (silent RTA filter failure) | **Fixed** in `_create_discoveryengine_schema()`; verify pre-ingest |
| 2 | Nullable union `type` invalid for Discovery Engine | High (registration failure / lost searchable) | **Fixed** via `_concrete_type()` |
| 3 | Tagging quality is the real event-relevance ceiling | High | Mitigated (prompt guidance); needs eval before one-shot ingest |
| 4 | Coercion defaults / `doc_type=""` sentinel | Medium | Open decision (§4) |
| 5 | Front-matter not filtered in chunker | Medium | Open (wire chunker or query pre-filter) |
| 6 | Safety pre-filters must be server-side | **Critical** (safety) | Deferred — query path stubbed |
| 7 | Enums not enforced by Discovery Engine | Medium | By design; gate is coercion |
| 8 | One-shot immutable ingestion | Context | Raises stakes on 1–7 |
| 9 | Field-count cap (≤ 50) | Low | Within limits at 37 fields |
| 10 | `keyPropertyMapping` for `title` | Low (optimization) | Not implemented; documented |

## References

- Google Cloud — *Configure field settings*: `generative-ai-app-builder/docs/configure-field-settings`
- Google Cloud — *Provide or auto-detect a schema*: `generative-ai-app-builder/docs/provide-schema`
- Repo — `discovery_engine_comparison.md`, `schema_notes.md`, `config/metadata_schema.json`
- Repo — `scripts/setup_vertex_search.py::_create_discoveryengine_schema()`
- Repo — `architecture_bootstrap.md` (open items + verification steps)
