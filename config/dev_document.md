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

**Consequence:** an ingest today tags against the 37-field schema. Fields that `rta_v1.json` intentionally dropped are still elicited and indexed. This is the primary migration debt. See `config/agentic_document.md` for the decision path.

- **#NOTE(schema-wired)** `settings.py:143` → `metadata_schema_path` default `config/metadata_schema.json`. `schema_loader.py:82` hardcodes the same default. `metadata_gen.py:348` hardcodes it too.
- **#TODO(schema-migration)** Repoint the code to `rta_v1.json` *after* its blocking items (§3) close, or consciously ship the first ingest on `metadata_schema.json` and defer. Cross-ref `ORCHESTRATOR §7`.

## 3. Known defects in `rta_v1.json` (from `summary.md §2` / `schema_recommendations.md §7`)

Re-verified against the current file on 2026-07-20:

- **#DONE 2026-07-19** File parses. The trailing-comma bug described in `summary.md §2.1` (and `schema_recommendations.md §7.1`) is already fixed — those subsections are now `#STALE` but harmless. `python3 -c "import json,sys; json.load(open('config/rta_v1.json'))"` exits clean; last field is `clinical_measure_tags`, there is no `missingness` field.
- **#TODO(applies-when-vocab)** `applies_when` is `{"type": "string"}` unconstrained (`rta_v1.json:151`). No `$defs.state_vocab`. **Highest-severity gap** — silent retrieval misses on the contraindication path. Blocked on clinician Q2.
- **#TODO(directionality-default)** `directionality` (line 142) has no `default` and is not in `required` — may be silently absent. Add `"default": "neutral"` or require it.
- **#TODO(pairing-conditional)** No draft-07 `if/then` enforcing `directionality ∈ {contraindicated,cautionary} ⇒ applies_when minItems 1`.
- **#TODO(stale-notes)** `notes.routing_safety`, `notes.representation_and_implementation_fields`, `notes.recommended_change_items` reference removed fields; `notes.vertex_ai_search` lists 7 nonexistent fields; four field descriptions have dangling references (`patient_population`→`evidence_base`; `session_phase`→`pre_intake_consultation` not in enum; `clinical_measure_tags`→`analysis_function`; `session_event_tags` truncated at "Motivational"). These descriptions are **read into the ingestion prompt** — stale text is a live model instruction.
- **#TODO** Normalize `C-SSRS`/`Columbia` (same instrument, two enum values) in `clinical_measure_tags`.
- **#NOTE** `domain` enum uses long names (`cognitive_behavioral_therapy`), `metadata_schema.json` uses short (`cognitive_behavioral`) — a rename, hence breaking across the two.

## 4. How the vocabulary is consumed (why drift is dangerous)

`SchemaVocabulary` (`schema_loader.py`) is the single code-side reader. Both `metadata_gen.py` (coercion + prompt enum legend) and `setup_vertex_search.py` (DataStore field registration) consume it. This eliminates the *old* second source of truth (hard-coded enums) but does **not** protect against:

- The schema file itself being the wrong one (§2).
- Array item enum values not being validated at *write* time — `additionalProperties:false` blocks unknown keys but not out-of-vocab array members.
- Filterable arrays not being registered in the DataStore (`summary.md §4.4`): unregistered filterable array ⇒ filter **silently no-ops**. This is the most likely production defect.

## 5. Review points (kept current)

- **#TODO(schema-migration)** Owner: architect. Done = code loads the intended schema and first ingest tags against it. MIU: none yet.
- **#TODO(applies-when-vocab)** Owner: schema + clinician. Done = `state_vocab` `$defs` added, `applies_when.items` constrained, DataStore re-registered. MIU: `MIU-001` (example) blocked on Q2.
- **#TODO(stale-notes)** Owner: agent. Done = three notes deleted, four descriptions fixed, `notes.vertex_ai_search` rewritten to the real field set. Low risk, high value (they leak into prompts).
- **#PARTIAL** `chunk_config.yaml` `skip_doc_types`/`front_matter_indicators` are loaded but only `skip_doc_types` is consumed (in `batch_ingest.py:114`); front-matter *indicators* are not wired into the chunker. Cross-ref `ingestion/dev_document.md`.

---

## Staleness note

- Verify §2 and §3 against `config/rta_v1.json` and `settings.py` at the start of any config work; both change under active development.
- The `summary.md §2.1` / `schema_recommendations.md §7.1` trailing-comma items are resolved — treat them as `#STALE`.
- Reconcile this file whenever `config/CHANGELOG.md` gains an entry newer than the date above.
