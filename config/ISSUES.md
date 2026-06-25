# Config Issues — Open for Human Review

Items below require a decision or manual action before DataStore registration or corpus ingestion. Each item is tagged with urgency:

- **[BLOCKER]** — must be resolved before any DataStore registration or ingestion run
- **[PRE-INGEST]** — must be resolved before the first ingestion of new corpus documents
- **[PRE-INGEST-ASA]** — must be resolved before ASA corpus ingestion specifically
- **[DESIGN]** — architectural decision; does not block registration but affects pipeline behavior
- **[CORPUS]** — corpus acquisition required for the feature to function; schema is ready
- **[CODE]** — code change required to implement a schema or config feature

---

## I-01 [BLOCKER] DataStore purge required before schema registration

The schema change is not backwards-compatible with any previously registered DataStore. Fields removed (`entities`, `evidence_level`), fields renamed/replaced (`domain`, `doc_type`, `practice_recommendation_level`), and fields added require a fresh DataStore.

**Action:** Run `PYTHONPATH=. python scripts/purge_datastore.py --confirm` then `PYTHONPATH=. python scripts/setup_vertex_search.py` before any ingestion. Do not attempt incremental import over an existing DataStore registered against the old schema.

**Risk:** All previously indexed data is permanently deleted. Ensure the source PDFs in `corpus/` are complete before purging.

---

## I-02 [BLOCKER] Array fields require explicit Vertex AI Search registration

The following array fields must be registered as filterable attributes (type `key` or `text`) in `scripts/setup_vertex_search.py` to be usable as retrieval filters. Without explicit registration, Vertex AI Search stores them as unindexed data only:

- `therapeutic_modality`
- `clinical_presentation`
- `session_event_tags`
- `analysis_function`
- `patient_population`
- `risk_dimension_tags`
- `outcome_measure_tags`
- `clinical_caution`
- `technique_tags`

**Action:** Audit `setup_vertex_search.py` schema registration logic before running it. Confirm each array field is registered with filterable=true. This is a correctness requirement for RTA event-based retrieval — if `session_event_tags` is not filterable, the primary retrieval trigger for the RTA pipeline does not function.

---

## I-03 [BLOCKER] `ingestion/metadata_gen.py` must be updated before any ingestion

Two removed fields and all new fields affect the Gemini extraction prompt and `_fallback_extraction()`:

1. **Remove `entities` and `evidence_level`** from `_fallback_extraction()` return values. These fields are no longer in the schema; populating them will fail `additionalProperties: false` validation.

2. **Add new fields** to the extraction prompt: `therapeutic_modality`, `clinical_presentation`, `session_event_tags`, `session_phase`, `target_audience`, `practice_recommendation_level`, `technique_tags`, `clinical_caution`, `training_level_required`, `risk_dimension_tags`, `corpus_scope`, `analysis_function`, `evidence_base`, `patient_population`, `time_horizon`, `outcome_measure_tags`.

3. **RTA vs ASA extraction mode:** ASA documents require Gemini to reason about epistemological type (`evidence_base`), population (`patient_population`), analysis routing (`analysis_function`), and temporal scope (`time_horizon`). This benefits from including the document's abstract or first few pages alongside the chunk as context. Consider a mode parameter in the extraction call.

4. **Controlled vocabulary in prompt:** Provide enum lists directly in the Gemini extraction prompt for `session_event_tags`, `therapeutic_modality`, `clinical_presentation`, `analysis_function`, and `patient_population` to constrain hallucination.

5. **`outcome_measure_tags` normalization:** Gemini will produce variants ("Patient Health Questionnaire-9", "PHQ9", "PHQ 9"). Add normalization to canonical abbreviations in `_fallback_extraction()`.

---

## I-04 [CODE] `PromptBuilder` must handle split retrieval instruction templates

`prompt_config.yaml` now has `retrieval_instruction_rta` and `retrieval_instruction_asa` instead of a single `retrieval_instruction`. `PromptBuilder` must:

1. Accept a `pipeline_mode` parameter ("rta" or "asa").
2. Select the appropriate template block by `pipeline_mode`.
3. Inject `{n_passages}`, `{session_event}`, `{therapeutic_modality}` in addition to existing variables.

**Fallback behavior:** If `pipeline_mode` is not supplied, default to `retrieval_instruction_rta` to preserve existing behavior.

---

## I-05 [CODE] `corpus_scope` pre-filter must be a hard constraint in the RTA searcher

The `corpus_scope` field separates RTA from ASA retrieval. The RTA searcher must apply `corpus_scope != "asa_only"` as a mandatory pre-filter on every query — not as a soft ranking signal. Similarly, `target_audience == "patient"` must be a hard pre-filter exclusion on all queries outside `analysis_function == "homework_resource"`.

These are patient safety constraints (homework worksheets surfaced mid-session are inappropriate and may confuse the clinician) and must not be implemented as ranking adjustments that can be overridden by relevance score.

**Action:** Implement in `retrieval/searcher.py` as pre-filters, not post-hoc ranking adjustments.

---

## I-06 [DESIGN] Single DataStore vs. separate DataStores for RTA and ASA

The current schema assumes a single shared DataStore with `corpus_scope` as the routing field. The corpus notes support both architectures:

- **Single DataStore (current design):** One registration, one ingestion pipeline, `corpus_scope` pre-filter on every RTA query. Simpler operationally; risk that a misconfigured searcher leaks `asa_only` documents into RTA retrieval.
- **Separate DataStores:** Explicit routing by DataStore ID; `corpus_scope` field is redundant in the ASA-only store. Adds operational complexity (two registration runs, two ingestion targets) but provides stronger architectural separation.

**Decision required before provisioning** `setup_vertex_search.py`. If separate DataStores are chosen, remove `corpus_scope` as a retrieval filter from the RTA searcher configuration and instead route by DataStore ID. Update `corpus_scope` in the schema to be a documentation-only field in the ASA DataStore.

---

## I-07 [DESIGN] `domain` enum sync between `prompt_config.yaml` and `metadata_schema.json`

The `domain` enum in `metadata_schema.json` and the persona keys in `prompt_config.yaml` must remain in sync. A mismatch causes PromptBuilder to silently fall back to `default`. This is currently enforced by convention only.

**Recommended action:** Add a unit test that loads both files and asserts that every value in the `domain` enum has a corresponding persona key (or documents the explicit fallback). This prevents persona coverage gaps from going undetected as new enum values are added.

---

## I-08 [PRE-INGEST] RECOMMENDED CHANGE items included in schema — corpus acquisition pending

The following items were included in the schema based on RECOMMENDED CHANGE blocks in `CORPUS_NOTES_RTA.md` and `CORPUS_NOTES_ASA.md`. The schema fields are ready, but no corpus documents covering these areas have been acquired yet. The fields will have empty/default values for all currently ingested documents until source texts are added.

**Therapeutic modality additions (SE, SP, UP):**
- SE (Somatic Experiencing): Levine; no source texts in corpus. Relevant to `somatic_activation` session event.
- SP (Sensorimotor Psychotherapy): Ogden; no source texts. See CORPUS_NOTES_RTA.md Tier 1 RECOMMENDED CHANGE.
- UP (Unified Protocol): Barlow transdiagnostic; no source texts tagged `UP` specifically.
- Recommended acquisitions: Ogden et al., *Trauma and the Body*; Levine, SE protocol texts; Fisher, *Healing the Fragmented Selves*; Barlow et al., *Unified Protocol* (if not already tagged).

**Clinical presentation additions (dissociative_disorders, health_anxiety, hoarding, bfrb, autism_spectrum, perinatal):**
- No corpus texts specifically targeting these presentations. Retrieval for these tags will return empty for now.

**Session event additions (shame_activation, somatic_activation, minority_stress_disclosure, cultural_mismatch, therapist_self_disclosure, avoidance_safety_behavior, premature_termination_signal, grief_loss_activation):**
- Most require corpus texts currently absent. See I-09 for LGBTQ+/cultural materials specifically.

**Termination planning (`analysis_function: termination_planning`):**
- Corpus notes recommend acquiring: Egan, *Termination of Psychotherapy*; Marx & Gelso (1987); Quintana (1993); Norcross et al. (2017). No texts currently in corpus.

**`pre_intake_consultation` in `session_phase`:**
- No MI-for-engagement or treatment-matching consultation texts currently tagged for this phase.

---

## I-09 [CORPUS] LGBTQ+ and cultural competency materials — corpus scope decision

`CORPUS_NOTES_RTA.md` recommends that LGBTQ+-affirmative and culturally responsive practice texts be promoted from ASA-only to RTA Tier 2. The rationale: minority stress disclosures and cultural misattunements are in-session events requiring real-time guidance, not only post-session reflection.

**Items referenced:**
- Pachankis & Safren (eds.), *Handbook of Evidence-Based Mental Health Practice with Sexual and Gender Minorities*
- Austin & Craig (eds.), *Transgender and Gender Nonconforming Psychotherapy*
- Hays, *Addressing Cultural Complexities in Counseling and Clinical Practice* (4th ed.)
- Lewis-Fernández et al., *DSM-5 Handbook on the Cultural Formulation Interview*

**Decision required:** Tag these `corpus_scope: rta_and_asa` (per RTA recommendation) or `corpus_scope: asa_only` (current default for cultural/diversity texts in the ASA corpus notes). Also tag `session_event_tags: ["minority_stress_disclosure"]` and `session_event_tags: ["cultural_mismatch"]` to enable RTA event-based retrieval.

---

## I-10 [PRE-INGEST-ASA] `practice_recommendation_level` needs `empirically_derived` handled in extraction

The `empirically_derived` value is intended for RCT-sourced chunks in the ASA corpus that report data-supported findings not yet synthesized into a clinical guideline. Gemini extraction must be prompted to distinguish this from `strongly_recommended` (which implies guideline status). Document the distinction in the extraction prompt: "`empirically_derived` = finding from an RCT or meta-analysis that has not yet been incorporated into an APA/NICE/ISTSS guideline."

---

## I-11 [CODE] Risk monitoring background retrieval pass not yet implemented

`risk_dimension_tags` is designed to drive a passive background retrieval pass on every session — not only when `crisis_escalation` fires. This requires a separate low-priority retrieval path in the RTA pipeline that runs alongside the event-triggered path on every session.

This is documented in the schema and in `CORPUS_NOTES_RTA.md` but has no corresponding implementation. The risk is that the system currently has no mechanism for surfacing chronic suicide ideation monitoring guidance unless an acute crisis event is detected.

**Action:** Design a secondary retrieval path in `retrieval/searcher.py` keyed on `risk_dimension_tags` that runs passively on every session query at lower priority than the main event-triggered path.

---

## I-12 [DESIGN] ASA Gemini extraction prompt is distinct from RTA extraction prompt

The ASA extraction prompt must additionally elicit `evidence_base`, `patient_population`, `analysis_function`, and `time_horizon` — fields requiring Gemini to reason about the epistemological type of the source document. This is distinct from RTA chunk extraction and benefits from including the document's abstract or title page alongside the chunk.

**Options:**
1. Single extraction call with both RTA and ASA field sets (simpler pipeline; wastes tokens for RTA-only documents).
2. Two extraction calls gated on `corpus_scope` (more precise; adds complexity to `metadata_gen.py`).

**Recommended:** Gate on `corpus_scope` at ingest time: if a document is designated `asa_only`, use the ASA extraction prompt. If `rta_and_asa`, run both or use the combined prompt. Document the decision in `ingestion/metadata_gen.py`.

---

## I-13 [DESIGN] `clinical_caution` field requires explicit retrieval surfacing

`clinical_caution` contains contraindications and precautions extracted from chunks. The value of this field is zero if the retrieval system ranks or filters it away — a high-caution chunk retrieved alongside a technique recommendation must surface its caution text to the therapist.

**Required behavior:** The response generator must inspect `clinical_caution` values in retrieved chunks and include them in the response when non-empty, regardless of whether the retrieved chunk was the top-ranked passage. This is a safety requirement, not a ranking preference.

**Action:** Design the `generation/response_gen.py` or `generation/prompt_builder.py` to inject `clinical_caution` content from retrieved `SearchResult.metadata` into the prompt, separate from the passage text.

---

## I-14 [PRE-INGEST] `training_level_required` values for existing corpus documents

The three current corpus documents (Boswell & Constantino *Deliberate Practice in CBT*, Foa et al. *PE for PTSD*, *CBT for Social Phobia*) have not been assigned `training_level_required` values. Gemini will attempt extraction at ingest time, but these values should be reviewed manually:

- Boswell & Constantino: likely `supervised_trainee` to `post_licensure`
- PE for PTSD (Foa et al.): `specialist_trained` (PE certification standard applies)
- CBT for Social Phobia: `post_licensure`

Review extracted values after ingestion and correct via delete-then-reimport if Gemini assigns incorrect levels.

---

## I-15 [DESIGN] `outcome_measure_tags` enum vs. free text

The current schema enumerates specific instrument abbreviations in `outcome_measure_tags`. The enum approach enforces canonical naming but requires schema updates when new instruments are added. The alternative (free text array with normalization in `_fallback_extraction()`) is more flexible but risks drift.

**Current decision:** Use the enum (forces schema update discipline). The normalization logic in `_fallback_extraction()` handles the most common Gemini variant forms. If a novel instrument appears, add it to the enum and re-register the schema.

**Instruments not currently in the enum that may appear in corpus:** YSR/CBCL (youth), PSS (Perceived Stress Scale), DERS (Difficulties in Emotion Regulation), RRS (Ruminative Response Scale), PTCI (Posttraumatic Cognitions Inventory). Add as needed.
