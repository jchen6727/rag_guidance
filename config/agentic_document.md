# config/ — Agentic Instructions (Internal-Facing)

**Audience:** automated (agentic) developers. Full operational detail.
**Precondition:** you have already ingested `/ORCHESTRATOR.md` this session. If not, stop and read it.
**Source of truth:** `config/rta_v1.json` (design) / `config/metadata_schema.json` (wired). Reconcile both before editing.
**Last reconciled:** 2026-07-20.

---

## Handoff log (newest first)

<!-- Each agent appends a dated entry at the TOP describing what it changed, what it left open,
     and what the next agent should do first. Never rewrite prior entries. -->

### 2026-07-20 — RTA schema migration to rta_v1.json (COMPLETE)
- Repointed the RTA ingest path from `metadata_schema.json` (37 fields) to `rta_v1.json` (23 fields):
  `settings.metadata_schema_path` default + `METADATA_SCHEMA_PATH` in all four `.env*` files;
  `models.py::ChunkMetadata` rewritten to 23 fields; `metadata_gen._extraction_guidance()` + `_load_schema` default updated.
- Hardened `rta_v1.json`: `$defs.state_vocab` (provisional), `applies_when` constrained to the union enum,
  `directionality` default `neutral`, `domain` default `psychotherapy_general`, `if/then` pairing conditional,
  stale notes purged, four descriptions fixed, `Columbia`→`C-SSRS`.
- Added `tests/test_schema_valid.py` + `tests/test_rta_schema.py`; 57 schema/loader/metadata tests green.
- `#NOTE(asa-preserved)[2026-07-20]` `metadata_schema.json` retained for ASA/history; not loaded by RTA.
- **Next agent should:** run the first-ingest dry-run (`ingestion/agentic_document.md §2`) and address
  `#TODO(front-matter)[2026-07-20]` — front matter is no longer filtered (rta_v1 doc_type has no `front_matter`).
- Still blocked on clinician Q2 to *tighten* the provisional `state_vocab` values (mechanism already shipped).

### 2026-07-20 — orchestrator bootstrap
- Created the governance layer (`/ORCHESTRATOR.md`, `/MIU_TEMPLATE.md`) and this directory triad.
- Verified: `rta_v1.json` parses (23 fields); `metadata_schema.json` parses (37 fields); code loads the 37-field schema.
- **Next agent should:** resolve `#TODO(schema-migration)` (§2 decision) before any real ingest, and land the cheap `#TODO(stale-notes)` fix (§4) which currently pollutes the ingestion prompt.
- Left open: all §3 blocking items in `dev_document.md`; clinician Q2 unanswered.

`<!-- ▲ latest handoff above ▲ -->`

---

## 1. Operating rules for this directory

1. `rta_v1.json` is the vocabulary SoT. Do not change enums without a `config/CHANGELOG.md` entry and a version bump (`_v1` → `_v1_1` additive, `_v2` breaking).
2. Field **descriptions are prompt text** (`metadata_gen._build_extraction_prompt` embeds `properties` JSON + `notes`). Editing a description changes model behavior. Keep descriptions short and definitional; put disambiguation in a maintained ingestion-guidance file, not the schema.
3. Never hand-edit enum lists into `metadata_gen.py` — that reintroduces the drift `schema_loader.py` exists to kill. All vocabulary flows from the schema.
4. Any change to a **high-stakes field** (`ORCHESTRATOR §6`) requires an MIU and the validation gate.
5. After any schema edit that adds/renames an array field, you MUST re-register it in `scripts/setup_vertex_search.py` — unregistered filterable arrays fail silently.

## 2. Schema decision — RESOLVED 2026-07-20

`#DONE(schema-migration)[2026-07-20]` The RTA ingest path was migrated to `rta_v1.json` (Option B below), per the user directive to prioritize the real-time-analysis ingestion deadline. `config/metadata_schema.json` is preserved for future ASA work and as history. Recorded in `config/CHANGELOG.md` (2026-07-20).

- **Option A — ingest on `metadata_schema.json`** (throwaway pipeline test) — **NOT taken.**
- **Option B — migrate to `rta_v1.json`, then ingest (correct end-state)** — **TAKEN.**
  - `settings.metadata_schema_path` default → `config/rta_v1.json`; `METADATA_SCHEMA_PATH` updated in all four `.env*` files (they previously overrode the default).
  - `models.py::ChunkMetadata` = 23 RTA fields; serializes to `structData` via `model_dump()`.
  - `metadata_gen._extraction_guidance()` + `_load_schema` default updated; `SchemaVocabulary` unchanged (it is schema-agnostic).
  - `#NOTE(asa-preserved)[2026-07-20]` The provisional `state_vocab` values await clinician Q2, but the *mechanism* is shipped — no re-ingest is needed to tighten values later (additive enum change), though re-ingest is needed to populate `applies_when` on chunks tagged before a value change.

## 3. Task queue (dated; execute top-down)

- `#DONE(stale-notes)[2026-07-20]` Deleted `notes.routing_safety`, `notes.representation_and_implementation_fields`, `notes.recommended_change_items`; rewrote `notes.vertex_ai_search` to the real array-field list; fixed four descriptions (`patient_population`, `session_phase`, `clinical_measure_tags`, `session_event_tags`); normalized `Columbia`→`C-SSRS`. Guarded by `tests/test_rta_schema.py::TestNoStaleReferences`.
- `#DONE(directionality-default)[2026-07-20]` `directionality` default `"neutral"`.
- `#DONE(applies-when-vocab)[2026-07-20]` `$defs.state_vocab` added; `applies_when.items` constrained to the closed union enum (events ∪ presentations ∪ states) — materialized as a flat inline enum because `schema_loader`/`setup_vertex_search` do not resolve `$ref`/`oneOf`. Drift guarded by `test_rta_schema.py::TestAppliesWhenVocabulary::test_applies_when_equals_union`. **Values remain provisional** (`#TODO(state-vocab-values)[2026-07-20]` — clinician Q2; MIU: `MIU-001` example).
- `#DONE(pairing-conditional)[2026-07-20]` draft-07 `if/then` at schema root enforces contraindicated/cautionary ⇒ `applies_when` `minItems: 1`.
- `#TODO(state-vocab-values)[2026-07-20]` When clinicians answer Q2: edit `$defs.state_vocab` **and** the `applies_when` union enum (keep them equal — the drift test enforces this), bump the schema version note, re-register the filterable `applies_when` array, and re-ingest to populate. MIU required (high-stakes).
- `#TODO(front-matter)[2026-07-20]` `rta_v1.json` `doc_type` has no `front_matter`, so `chunk_config.yaml`'s `skip_doc_types: [front_matter]` filter is now a no-op. Decide front-matter handling before a production ingest (coordinate with `ingestion/`). Owner: ingestion dev.

## 4. Invariants to preserve (from `summary.md §0`)

- `directionality` and `applies_when` are one unit — never read/write/validate one without the other.
- Contraindications are never dropped by a relevance threshold.
- Ingestion vocabulary and detection vocabulary are the same enum with opposite semantics — never share a prompt between them.

## 5. Verification commands

```bash
# schema parses
python3 -c "import json;print(len(json.load(open('config/rta_v1.json'))['properties']),'fields')"
python3 -c "import json;print(len(json.load(open('config/metadata_schema.json'))['properties']),'fields')"

# which schema the code will load
PYTHONPATH=. python3 -c "from config.settings import settings; print(settings.metadata_schema_path)"

# vocabulary the loader exposes (sanity-check enums after any edit)
PYTHONPATH=. python3 -c "from config.schema_loader import SchemaVocabulary as V; v=V.from_path(); print(sorted(v.array_fields))"
```

## 6. Update-on-exit checklist (before you hand off)

- [ ] Append a dated entry to the Handoff log above.
- [ ] Flip any completed `#TODO → #DONE` here **and** in `dev_document.md`, with a `config/CHANGELOG.md` date.
- [ ] Update the plain-language *Points for review* in `clinical_document.md` if a clinician-visible item changed (translate — no code symbols).
- [ ] If you touched the SoT, walk the full propagation chain (`ORCHESTRATOR §4.2`).
- [ ] Re-date the `Last reconciled` headers you touched.

---

## Staleness note

- Re-verify §2 (schema wiring) and §3 (blocking items) against the live files each session — this is the fastest-moving area of the repo.
- The trailing-comma items in `summary.md §2.1` / `schema_recommendations.md §7.1` are resolved (`#STALE`).
- If `config/CHANGELOG.md` has an entry newer than this file's date, reconcile before feature work.
