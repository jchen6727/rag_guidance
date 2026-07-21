# config/ — Developer Guide (Internal-Facing)

**Audience:** technical auditors / architects (moderate depth).
**Scope:** the configuration + schema layer that governs ingestion vocabulary, chunking, prompting, and DataStore registration.
**Governed by:** `ORCHESTRATOR.md`. Vocabulary source of truth: `config/rta_v1.json`.
**Last reconciled:** 2026-07-20 (against `rta_v1.json`, `metadata_schema.json`, `schema_recommendations.md`, `summary.md`).

---

## Feedback log (newest first)

<!-- Developers: prepend feedback here, newest first, dated. Agents process top-down to the marker. -->

*(no developer feedback recorded yet)*

`<!-- ▲ unprocessed above this line ▲ -->`

---

## 1. What lives here

| File | Role | Authoritative for |
|---|---|---|
| `rta_v1.json` | **Design SoT** — RTA ChunkMetadata_v1, 23 fields | Vocabulary, enums, `directionality`+`applies_when` model |
| `metadata_schema.json` | **Currently-wired** schema — unified RTA+ASA, 37 fields | What the code actually loads today |
| `schema_loader.py` | `SchemaVocabulary` — derives enums/arrays/defaults/coercion from a schema | Single code-side vocabulary reader |
| `settings.py` | Env-driven config singleton; `metadata_schema_path` default = `metadata_schema.json` | Which schema the pipeline loads |
| `chunk_config.yaml` | `ChunkerConfig` params (token budget, similarity threshold, headers, front-matter) | Chunking behavior |
| `prompt_config.yaml` | Persona templates, RTA/ASA retrieval instruction blocks | PromptBuilder (query path, stubbed) |
| `schema_recommendations.md` | Analysis, open questions, rationale (annotates the SoT) | Design intent + §9 clinician questions |
| `summary.md` | Actionable implementation contract for agents | Invariants + phase definition-of-done |
| `CHANGELOG.md` / `CORPUS.md` / `ISSUES.md` | History / corpus notes / issue register | Provenance |

## 2. The central fact: two schemas, one of them wired

- `rta_v1.json` (title `ChunkMetadata_v1`) is the **design target** — 23 fields, RTA-only, with the `directionality`+`applies_when` relational contraindication model that replaced `practice_recommendation_level`.
- `metadata_schema.json` (title `ChunkMetadata`) is what **`schema_loader.py`, `metadata_gen.py`, and `setup_vertex_search.py` load** via `settings.metadata_schema_path`. 37 fields, includes ASA-only routing (`corpus_scope`, `analysis_function`, `evidence_base`, `time_horizon`) and the source-provenance block (`population_focus`, `setting`, `missingness`, …).

- `#DONE(schema-migration)[2026-07-20]` The RTA ingest path now loads `rta_v1.json`. `settings.metadata_schema_path` default → `config/rta_v1.json`; `METADATA_SCHEMA_PATH` in all four `.env*` files updated (they previously overrode the default); `metadata_gen._load_schema` bare default → `rta_v1.json`. `schema_loader.from_path` bare default is intentionally left at `metadata_schema.json` (used only by the preserved-ASA loader tests). CHANGELOG: `config/CHANGELOG.md` 2026-07-20.
- `#NOTE(asa-preserved)[2026-07-20]` `metadata_schema.json` is retained for future ASA work + history, not loaded by RTA. `models.py::ChunkMetadata` is now the 23 RTA fields but keeps `year_published: Optional[int]` so the ASA-schema coercion tests still pass.

## 3. Known defects in `rta_v1.json` (from `summary.md §2` / `schema_recommendations.md §7`)

All resolved 2026-07-20 (guarded by `tests/test_rta_schema.py`):

- `#DONE[2026-07-20]` File parses (23 fields). The trailing-comma bug in `summary.md §2.1` / `schema_recommendations.md §7.1` was already fixed before this pass — those subsections are `#STALE[2026-07-20]` but harmless.
- `#DONE(applies-when-vocab)[2026-07-20]` `applies_when` constrained to a closed union enum; `$defs.state_vocab` added (flat-inline materialization, since the loader doesn't resolve `$ref`/`oneOf`). Values **provisional** — `#TODO(state-vocab-values)[2026-07-20]` clinician Q2.
- `#DONE(directionality-default)[2026-07-20]` `directionality` default `"neutral"`.
- `#DONE(pairing-conditional)[2026-07-20]` root `if/then` enforces contraindicated/cautionary ⇒ `applies_when minItems 1`.
- `#DONE(stale-notes)[2026-07-20]` three obsolete notes deleted; `notes.vertex_ai_search` rewritten; four descriptions fixed; `Columbia`→`C-SSRS` normalized.
- `#NOTE[2026-07-20]` `domain` uses long names (`cognitive_behavioral_therapy`); `metadata_schema.json` uses short (`cognitive_behavioral`) — a genuine rename, hence the two schemas are not interchangeable (breaking).

## 4. How the vocabulary is consumed (why drift is dangerous)

`SchemaVocabulary` (`schema_loader.py`) is the single code-side reader. Both `metadata_gen.py` (coercion + prompt enum legend) and `setup_vertex_search.py` (DataStore field registration) consume it. This eliminates the *old* second source of truth (hard-coded enums) but does **not** protect against:

- The schema file itself being the wrong one (§2).
- Array item enum values not being validated at *write* time — `additionalProperties:false` blocks unknown keys but not out-of-vocab array members.
- Filterable arrays not being registered in the DataStore (`summary.md §4.4`): unregistered filterable array ⇒ filter **silently no-ops**. This is the most likely production defect.

## 5. Review points (kept current)

- `#DONE(schema-migration)[2026-07-20]` Code loads `rta_v1.json`; migration verified end-to-end (coercion → `ChunkMetadata` → `model_dump` → DataStore schema all round-trip 23 fields).
- `#DONE(applies-when-vocab)[2026-07-20]` `state_vocab` `$defs` added, `applies_when.items` constrained; re-registration handled by `setup_vertex_search` reading the active schema. `#TODO(state-vocab-values)[2026-07-20]` values pending Q2 (MIU-001).
- `#DONE(stale-notes)[2026-07-20]` notes + descriptions cleaned; guarded by tests.
- `#TODO(front-matter)[2026-07-20]` Owner: ingestion dev. Under `rta_v1.json` (no `front_matter` doc_type) the `skip_doc_types` filter is a no-op — front matter is unfiltered. Also `front_matter_indicators` was never wired into `ContextAwareChunker`. Redesign front-matter handling before a production ingest. Cross-ref `ingestion/dev_document.md`.

---

## Staleness note

- Verify §2 and §3 against `config/rta_v1.json` and `settings.py` at the start of any config work; both change under active development.
- The `summary.md §2.1` / `schema_recommendations.md §7.1` trailing-comma items are resolved — treat them as `#STALE`.
- Reconcile this file whenever `config/CHANGELOG.md` gains an entry newer than the date above.
