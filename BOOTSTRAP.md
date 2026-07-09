# Agent Bootstrap — RAG Guidance Pipeline

This document is the entry point for any new agent session. Read it first, in full, before reading any other file. It is kept current as the project evolves.

---

## Project in one paragraph

A Python RAG system that provides clinical guidance to psychotherapists trained in **CBT, DBT, and IPT** — and only those three therapy families. It has two operational modes: **RTA** (real-time analysis, in-session) and **ASA** (after-session analysis). A session transcript is ingested, relevant clinical literature is retrieved from a Vertex AI Search DataStore, and Gemini generates grounded guidance with inline citations. **The ingest path is implemented** (`ingestion/*.py` except the dead `watcher.py`, plus `models.py`, `config/settings.py`, `scripts/`, most `tests/`). **The query path is still stub-only** (`raise NotImplementedError`): `generation/`, `retrieval/`, and `rta_prompt/`. Scaffolding, docstrings, type signatures, and config files are complete and authoritative throughout.

---

## What has been done so far (recent sessions)

1. **Config domain migration** (`2026-06-24`) — `config/metadata_schema.json` and `config/prompt_config.yaml` were rewritten from a generic biomedical baseline to a psychotherapy-specific schema covering both the RTA and ASA pipelines. See `config/CHANGELOG.md` §2026-06-24.

2. **CBT/DBT/IPT scope pruning** (`2026-06-25`) — All domains, modalities, and personas outside the competence of a CBT/DBT/IPT-trained clinician were removed. See `config/CHANGELOG.md` §2026-06-25 for the full removal table and rationale.

---

## Mandatory reading order (before any implementation work)

Read these files in this order. Do not skip any.

| # | File | Why |
|---|---|---|
| 1 | `CLAUDE.md` | Project rules, known issues list, command reference. The known issues list is authoritative — do not re-derive them. |
| 2 | `config/CHANGELOG.md` | What changed in the config files and why. Prevents re-introducing removed fields or modalities. |
| 3 | `config/metadata_schema.json` | Current authoritative schema. All ingestion, retrieval filter expressions, and Gemini extraction prompts must conform to this. |
| 4 | `config/prompt_config.yaml` | Persona definitions and retrieval instruction templates. Contains the CBT/DBT/IPT scope constraint in each persona's system prompt. |
| 5 | `config/ISSUES.md` | 23 open issues (I-01–I-23). Several are blockers before DataStore registration or ingestion. Check this before implementing anything that touches GCP or the DataStore. |
| 6 | `rta_prompt/models.py` | All pipeline I/O types: `PatientContext`, `RTAResponse`, `ASAResponse`, `DetectedEvent`, `SessionTranscript`, `ASAHopResult`. These drive every implementation decision downstream. |
| 7 | `models.py` | Core shared types: `Chunk`, `ChunkMetadata`, `SearchResult`, `Citation`, `GeneratedResponse`. `ChunkMetadata` is the Pydantic model that must stay in sync with `config/metadata_schema.json`. |

---

## Key architectural facts (know before writing any code)

**Two pipelines share one corpus.**
- RTA: `rta_prompt/rta/pipeline.py` → `RTAPipeline.run(transcript)` — called per turn; must return within the latency of a live clinical exchange.
- ASA: `rta_prompt/asa/pipeline.py` → `ASAPipeline.run(transcript, patient_history)` — called once after session close; multi-hop; no latency budget.

**`corpus_scope` is a hard routing field, not a ranking signal.**
RTA searcher applies `NOT corpus_scope = "asa_only"` as a mandatory pre-filter on every query. `target_audience = "patient"` is a hard exclusion on all paths except `analysis_function = "homework_resource"` in ASA. These are patient safety constraints — implement them as pre-filters in `_build_static_filter()` / `_build_asa_filter()`, never as ranking adjustments.

**Schema and implementation are out of sync.**
`ingestion/metadata_gen.py` still has the old biomedical constants (`_VALID_DOMAINS`, `_VALID_DOC_TYPES`, `_VALID_EVIDENCE_LEVELS`) and populates the removed `entities` field in `_fallback_extraction()`. These must be corrected before ingestion. See the "files to modify" section below.

**Pipeline persona domain keys are wrong.**
`rta_prompt/rta/pipeline.py:_RTA_PERSONA_DOMAIN = "psychotherapy_rta"` and `rta_prompt/asa/pipeline.py:_ASA_PERSONA_DOMAIN = "psychotherapy_asa"` — neither value exists in `config/prompt_config.yaml`. The correct key depends on the patient context's primary modality (e.g. `"cognitive_behavioral"`, `"dialectical_behavior"`). `PromptBuilder` falls back to `"default"` on a miss, so the pipeline currently always uses the generic persona. Fix this by deriving the domain key from `PatientContext.therapeutic_modality[0]` at pipeline init (or pass `domain` explicitly from the caller).

**`PromptBuilder` must handle the new split retrieval instruction.**
The config now has `retrieval_instruction_rta` and `retrieval_instruction_asa` (not a single `retrieval_instruction`). `PromptBuilder.build()` must accept `pipeline_mode: str` ("rta" or "asa") and select the correct block. Template variables `{n_passages}`, `{session_event}`, and `{therapeutic_modality}` are new and must be injected. See `config/prompt_config.yaml` header for the full variable list.

---

## Next session: scope-of-competence enforcement

**The central task for the next implementation session** is ensuring that the system never provides guidance on modalities, techniques, or treatment approaches outside the ethical bounds of a CBT/DBT/IPT-trained clinician, and that it redirects to a specialist when appropriate.

This is not only about persona wording (already done in `config/prompt_config.yaml`). It must be enforced in code at multiple layers:

### Layer 1 — `PatientContext` validation (`rta_prompt/models.py`)

`PatientContext.therapeutic_modality` is a plain `list[str]` with no validation. Add a `__post_init__` validator that:
1. Checks each value against the `therapeutic_modality` enum in `config/metadata_schema.json` (load at import time).
2. Logs a warning and removes any value not in the enum.
3. Specifically guards against the 19 removed modalities (EMDR, ACT, EFT, PDT, IFS, etc.) — if one appears, log a prominent warning: "Modality X is outside the CBT/DBT/IPT scope of this system. Removing from filter. Seek specialist consultation."

### Layer 2 — `EventDetector._build_llm_prompt()` (`rta_prompt/rta/event_detector.py`)

The LLM event detection prompt must include an explicit scope constraint:

> "You are assisting a psychotherapist trained in CBT, DBT, and IPT. Do not suggest interventions from outside these modalities (e.g. EMDR, ACT, EFT, psychodynamic interpretation, somatic approaches). If you detect that the session material requires a modality outside this scope, set the detected event tag to 'none' and note in your reasoning that specialist consultation is indicated."

This prevents the event detector from hallucinating tags that would route retrieval to out-of-scope content — even if such tags existed in a future schema.

### Layer 3 — `PromptBuilder.build()` (`generation/prompt_builder.py`)

When `_select_persona()` is called with a domain that matches to `"default"` (i.e. the domain was not found), the build method should prepend a note to the system prompt:

> "Note: the requested domain was not found in the configured persona set. Falling back to the general CBT/DBT/IPT supervisor. If this session involves a modality outside CBT, DBT, or IPT, redirect the clinician to consult a specialist trained in that modality."

This makes the fallback transparent to the generated response rather than silent.

### Layer 4 — Retrieved passage scope guard (`retrieval/searcher.py` or a new `ScopeGuard`)

Consider adding a `ScopeGuard.filter(results: list[SearchResult]) -> list[SearchResult]` that removes any retrieved passage whose `therapeutic_modality` metadata contains out-of-scope values. This is a defensive measure in case the DataStore is ever re-ingested with documents from excluded modalities. The guard should log which passages were filtered and why.

### Layer 5 — Out-of-scope redirect message

Define a canonical out-of-scope redirect string in a constants file (e.g. `rta_prompt/constants.py`):

```python
OUT_OF_SCOPE_REDIRECT = (
    "The clinical material in this session involves approaches outside the scope of "
    "CBT, DBT, and IPT (the modalities covered by this guidance system). For guidance "
    "on {modality}, please consult a clinician with specific training in that modality. "
    "This system will continue to provide CBT/DBT/IPT-relevant guidance for any "
    "aspects of the session that fall within that scope."
)
```

Surface this string in `RTAResponse.guidance_text` or `ASAResponse` when the session modality or retrieved passages fall outside scope, rather than returning an empty response or generating speculative content.

---

## Files to modify (implementation priority order)

### P0 — Must fix before any ingestion run

**`ingestion/metadata_gen.py`**
- Replace `_VALID_DOMAINS` set (currently biomedical) with the 12-value psychotherapy domain enum from `config/metadata_schema.json`. Load the schema at module level and derive the sets programmatically so they stay in sync automatically.
- Replace `_VALID_DOC_TYPES` with the 16-value psychotherapy doc_type enum.
- Remove `_VALID_EVIDENCE_LEVELS` (GRADE A/B/C/D). Replace with `_VALID_PRACTICE_RECOMMENDATION_LEVELS` from the new schema.
- In `_validate_and_coerce()`: remove the coercion block for `entities` (field no longer exists). Add coercion blocks for the new array fields: `therapeutic_modality`, `clinical_presentation`, `session_event_tags`, `analysis_function`, `patient_population`, `risk_dimension_tags`, `outcome_measure_tags` — each must default to `[]` if missing or non-list.
- In `_fallback_extraction()`: remove `entities` from the return value. Add defaults for all new required fields.
- In `_build_extraction_prompt()`: update to include the new field list, provide enum lists inline for constrained fields. For ASA documents (`corpus_scope = "asa_only"`), extend the prompt to elicit `evidence_base`, `patient_population`, `analysis_function`, and `time_horizon`. See `config/ISSUES.md §I-03` for the full requirements.

**`scripts/setup_vertex_search.py`**
- Register all array fields as filterable attributes (`key` or `text` type). See `config/ISSUES.md §I-02` for the full list. This is a DataStore registration correctness requirement — without it the RTA event filter does not function.

### P1 — Must implement before any pipeline run

**`generation/prompt_builder.py`**
- Implement `_load_config()`, `_select_persona()`, `_format_retrieved_chunks()`, `list_available_domains()`.
- Implement `build()` with the new signature: accept `pipeline_mode: str` parameter; select `retrieval_instruction_rta` or `retrieval_instruction_asa` from config; inject all template variables including `{n_passages}`, `{session_event}`, `{therapeutic_modality}`.
- Add scope-of-competence fallback note when persona falls back to `default` (see Layer 3 above).

**`rta_prompt/rta/pipeline.py`**
- Fix `_RTA_PERSONA_DOMAIN` constant — derive from `PatientContext.therapeutic_modality[0]` (mapping to schema `domain` values), not a hardcoded `"psychotherapy_rta"` string.
- Implement all stub methods per their docstrings.

**`rta_prompt/asa/pipeline.py`**
- Fix `_ASA_PERSONA_DOMAIN` — same problem as RTA pipeline.
- Implement all stub methods per their docstrings.

**`rta_prompt/rta/searcher.py`**
- Implement `_build_static_filter()` — must include `NOT corpus_scope = "asa_only"` and `NOT target_audience = "patient"` as mandatory guards.
- Implement `_build_event_filter()`, `_build_training_level_filter()`, `search()`, `search_risk()`.

**`rta_prompt/asa/searcher.py`**
- Implement `_build_asa_filter()` — corpus_scope restriction lifted; target_audience=patient allowed only for `homework_resource`.
- Implement `search_by_function()`, `search_outcome_instruments()`, helper methods.

**`retrieval/searcher.py`**
- `SearchFilter` dataclass has only old schema fields (`domain`, `subdomain`, `doc_type`, `year_published_min/max`, `custom_expression`). The RTA/ASA searchers bypass this via `custom_expression` — that is the correct approach; do not add all new fields to `SearchFilter`. Document this explicitly.
- Implement `search()`, `_build_filter_expression()`, `_parse_result()`, `_parse_metadata()`, `_get_client()`.

**`rta_prompt/rta/event_detector.py`**
- Implement `detect()`, `detect_risk_signals()`, `_run_heuristic_pass()`, `_run_llm_pass()`, `_build_llm_prompt()`, `_get_client()`.
- In `_build_llm_prompt()`: include the CBT/DBT/IPT scope constraint (Layer 2 above).

### P2 — Before test implementation

**`rta_prompt/models.py`**
- Add `__post_init__` to `PatientContext` for scope-of-competence validation (Layer 1 above).

**`models.py` (`ChunkMetadata`)**
- Current Pydantic model must be verified to match `config/metadata_schema.json` field for field. Likely out of sync — it may still have `entities` and `evidence_level` fields. Update to add all new fields with correct types and defaults.

---

## Files to read but not modify

| File | What it tells you |
|---|---|
| `corpus/CORPUS_NOTES_RTA.md` | Ground truth for what belongs in the RTA corpus and why. If adding new corpus documents, this is the inclusion/exclusion criterion. |
| `corpus/CORPUS_NOTES_ASA.md` | Ground truth for ASA corpus additions. Also contains the full ASA schema spec that was merged into `config/metadata_schema.json`. |
| `corpus/RTA_ASA_SCHEMA.md` | Consolidated JSON excerpts of both schemas. Useful for cross-referencing — the authoritative version is `config/metadata_schema.json`. |
| `config/settings.py` | `Settings` singleton. All GCP config, model IDs, and env var names. Call `settings.validate_all()` at startup. |
| `structure.md` | High-level project layout notes (may be stale — `CLAUDE.md` takes precedence). |
| `caveats.md` | Known Vertex AI Search behavioral limitations (e.g. enterprise edition required for semantic search, filter expression syntax quirks). Read before implementing `retrieval/searcher.py`. |
| `issues.md` (root-level) | Original pre-migration issues list. Mostly superseded by `config/ISSUES.md` but may contain infra-level notes not duplicated there. |

---

## Controlled vocabulary quick reference

The following enum values are the ground truth from `config/metadata_schema.json`. Hardcoding any enum value in implementation code is fragile — load from the schema file at module init instead.

**`domain`** (12 values):
`cognitive_behavioral`, `dialectical_behavior`, `trauma_focused`, `interpersonal`, `motivational_interviewing`, `mindfulness_based`, `crisis_intervention`, `therapeutic_alliance`, `clinical_supervision`, `psychopathology_clinical`, `psychotherapy_general`, `other`

**`therapeutic_modality`** (15 values, CBT/DBT/IPT scope only):
`CBT`, `CBT-I`, `BA`, `REBT`, `Schema`, `DBT`, `CPT`, `PE`, `IPT`, `IPSRT`, `MI`, `MBCT`, `UP`, `supportive`, `integrative`

**Out-of-scope modalities** (removed; must not appear in any filter, extraction prompt, or generated output):
`ACT`, `CFT`, `FAP`, `EMDR`, `TF-CBT`, `NET`, `PDT`, `relational`, `object_relations`, `EFT`, `AEDP`, `IFS`, `ISTDP`, `Gottman`, `narrative`, `SE`, `SP`, `MBSR`, `MBRP`

**`corpus_scope`**: `rta_and_asa` (default), `asa_only`

**`session_phase`**: `pre_intake_consultation`, `assessment_intake`, `early_treatment`, `mid_treatment`, `late_treatment`, `termination`, `crisis`, `any`

**`analysis_function`** (10 values): `session_autopsy`, `case_formulation_update`, `treatment_plan_revision`, `homework_resource`, `outcome_monitoring`, `risk_documentation`, `referral_coordination`, `prognosis_trajectory`, `supervision_preparation`, `termination_planning`

---

## Test infrastructure notes

- Run all tests with `PYTHONPATH=. pytest tests/`
- `tests/conftest.py` exists but may be minimal — consolidate any `make_chunk()` or fixture helpers here before writing new tests.
- `tests/fixtures/` does not exist yet — create it and populate with sample PDFs before implementing extractor tests (see `CLAUDE.md` Known Issue #5).
- No `pyproject.toml` — all imports are absolute from project root.
