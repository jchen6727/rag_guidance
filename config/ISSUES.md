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

**Current intentional gaps:** `psychotherapy_general` and `other` do not have dedicated persona keys — both fall back to `default` by design. `default` is the general psychotherapy supervisor persona and is appropriate for both.

**Recommended action:** Add a unit test that loads both files and asserts every `domain` enum value either has a matching persona key or is explicitly listed as a known `default` fallback. This prevents unintentional coverage gaps from going undetected as new enum values are added.

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

---

## I-16 [CODE] `population_focus` vs. `patient_population` disambiguation in extraction prompt

`population_focus` describes who the source was developed, adapted, or piloted for. `patient_population` describes who the chunk's evidence or recommendation applies to. These will often share values but are conceptually distinct: a standard adult CBT manual may have `population_focus=["adult_general"]` and `patient_population=["adult_general"]`, while a culturally adapted version developed in partnership with a BIPOC community clinic would have `population_focus=["bipoc"]` even if the base protocol's stated applicability (`patient_population`) is broader.

Without explicit disambiguation in the Gemini extraction prompt, the model will conflate these fields. The prompt must include: "population_focus = who participated in developing or validating this source; patient_population = who the evidence in this passage applies to."

---

## I-17 [CODE] `missingness` inference requires explicit Gemini prompt guidance

`missingness` captures what the source does not report — demographic data, fidelity monitoring, adverse events, population-specific subgroup analyses. Inferring absence is inherently harder than extracting presence, and without explicit instruction Gemini will leave this field empty.

**Action:** Add a dedicated instruction block to the extraction prompt: "Report what is notably absent from this source. Examples: 'no demographic breakdown of study sample', 'no fidelity monitoring reported', 'efficacy data for adolescents not reported', 'no adverse event data', 'cultural adaptation process not described'." Without this, `missingness` will default to `[]` for all documents and lose its value as a representation-gap signal.

---

## I-18 [DESIGN] `adaptation_status=culturally_adapted` and `corpus_scope` routing interaction

The `adaptation_status` field description notes that `culturally_adapted` and `resource_constrained` sources may warrant `corpus_scope=rta_and_asa` even when the base protocol defaults to `asa_only`. This override is not automatically enforced — it requires a curation rule or code decision.

**Options:**
1. At ingest time, if `adaptation_status in ["culturally_adapted", "resource_constrained"]`, override `corpus_scope` to `rta_and_asa` regardless of `doc_type` default.
2. Flag for human curation review rather than automatic override.
3. Leave the description as advisory only; curators set `corpus_scope` manually.

**Decision required before ingesting adapted materials.** If option 1 is chosen, implement in `ingestion/metadata_gen.py` as a post-extraction override after Gemini assignment.

---

## I-19 [BLOCKER] New array fields require Vertex AI Search filterable registration

The following array fields added in the 2026-06-25 schema update must be registered as filterable attributes in `scripts/setup_vertex_search.py` before DataStore registration. Without registration these fields are stored but cannot be used as retrieval filters:

- `population_focus`
- `setting`
- `presentation_coverage`
- `intended_use_context`
- `source_language`

`missingness` is informational only and does not require filterable registration.

**Action:** Audit `setup_vertex_search.py` and add these five fields alongside the existing array fields from I-02. The full filterable array field list is now: therapeutic_modality, clinical_presentation, session_event_tags, analysis_function, patient_population, risk_dimension_tags, outcome_measure_tags, clinical_caution, technique_tags, population_focus, setting, presentation_coverage, intended_use_context, source_language.

---

## I-20 [CODE] `presentation_coverage` and `session_event_tags` must be disambiguated in extraction prompt

`presentation_coverage` is a source-level property describing what the document addresses (e.g. `discrimination_stress`, `migration_acculturation`). `session_event_tags` is a chunk-level property describing in-session events a specific passage addresses (e.g. `minority_stress_disclosure`, `cultural_mismatch`).

The values overlap conceptually: a source covering `discrimination_stress` in `presentation_coverage` will likely have chunks tagged `minority_stress_disclosure` in `session_event_tags`. Without explicit disambiguation, Gemini may assign chunk-level event tags based on the document's overall coverage, or omit `presentation_coverage` because the same content is already captured in `session_event_tags`.

**Action:** Add to the extraction prompt: "presentation_coverage = what cultural or contextual dimensions does the overall source document address; session_event_tags = what specific in-session event does this individual chunk directly address." Both fields should be populated independently.

---

## I-21 [CODE] `study_type` vs. `evidence_base` disambiguation in extraction prompt

`study_type` is a document-level field set once from the source's primary study design. `evidence_base` is chunk-level and can vary within a document: a chunk from an RCT paper may be `evidence_base=rct_primary` while a chunk in the same paper summarizing prior literature might be `evidence_base=meta_analytic`.

Without disambiguation, Gemini may copy `study_type` into `evidence_base` for every chunk (collapsing meaningful variation) or set `study_type` differently per chunk (incorrect; it is fixed at the document level).

**Action:** Extraction prompt must state: "study_type is fixed at the document level — it does not change between chunks. evidence_base describes the epistemological character of the specific passage being extracted."

---

## I-22 [BLOCKER] New fields require re-extraction for existing corpus documents

The three existing corpus documents (Boswell & Constantino *Deliberate Practice in CBT*, Foa et al. *PE for PTSD*, CBT for Social Phobia) have not been tagged with any of the nine representation or implementation fields added in the 2026-06-25 schema update. `CorpusScanner.scan()` skips documents already recorded in the manifest via `is_processed()`.

**Action:** Either run `batch_ingest.py --force` for each existing file to trigger re-extraction, or set the new fields manually via curator review and delete-then-reimport. Re-extraction also requires the DataStore purge and re-registration mandated by I-01 for any schema change, so this can be combined with the next full re-ingest cycle.

Approximate expected values for manual curation:
- Boswell & Constantino: `study_type=clinical_manual`, `population_focus=["adult_general"]`, `setting=["academic_medical_center"]`, `intended_use_context=["supervision", "self_study"]`
- Foa et al. PE for PTSD: `study_type=clinical_manual`, `population_focus=["adult_general", "veteran_military"]`, `setting=["academic_medical_center"]`, `intended_use_context=["in_session_support"]`
- CBT for Social Phobia: `study_type=clinical_manual`, `population_focus=["adult_general"]`, `setting=["academic_medical_center"]`, `intended_use_context=["in_session_support"]`

---

## I-23 [DESIGN] `evidence_level` from proposed_changes_metadata_schema.md — scope clarification needed

`proposed_changes_metadata_schema.md` listed "evidence level" as an implementation field alongside study type and sample size. This was interpreted as already covered by two existing fields: `practice_recommendation_level` (recommendation strength and polarity: strongly_recommended through contraindicated) and the new `study_type` (study design type). A GRADE A/B/C/D field was explicitly removed in the 2026-06-24 migration as not appropriate for the psychotherapy evidence context.

**If a distinct field was intended** — for example, a formal APA Division 12 evidence category (Well-Established, Probably Efficacious, Possibly Efficacious) or a NICE grade — add it to the schema and log a new entry here. The current schema does not prevent this addition; it would be added to the enum alongside `practice_recommendation_level` or as a separate field.

**No action required unless the original intent was a field not covered by `practice_recommendation_level` or `study_type`.**
