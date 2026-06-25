# Config Changelog

## 2026-06-25 — CBT/DBT/IPT scope pruning

Pruned `metadata_schema.json` and `prompt_config.yaml` to reflect the scope of competence of a psychotherapist trained in CBT, DBT, and/or IPT. The guiding principle: every domain, modality tag, and persona must represent something a CBT/DBT/IPT-trained clinician is both qualified to deliver and ethically permitted to claim competence in. Modalities requiring separate certification or belonging to a different therapeutic tradition are removed from the schema enums and from the persona list. Where a removed modality's techniques appear in passing within a kept persona (e.g. psychodynamic formulation concepts within a case formulation persona), the persona is reworded to distinguish *understanding* from *delivery*.

### metadata_schema.json

**`domain` enum — removed 4 values:**

| Removed value | Rationale |
|---|---|
| `acceptance_commitment` | ACT, CFT, and FAP are distinct training tracks requiring specific competency development beyond CBT. A CBT/DBT/IPT therapist may be familiar with ACT concepts but is not qualified to deliver ACT as a modality. |
| `psychodynamic` | PDT, relational, and object-relations approaches are a separate professional training track (psychoanalytic institutes, post-graduate PDT programs). Outside CBT/DBT/IPT ethical bounds. |
| `emotion_focused` | EFT and AEDP require specific training (York University EFT certification, AEDP Institute). Neither is part of CBT/DBT/IPT competency development. |
| `systemic_family` | Structural, strategic, narrative, and Gottman couples therapy are family/couples specialty training tracks distinct from individual CBT/DBT/IPT. |

**`therapeutic_modality` enum — removed 19 values:**

| Removed value | Rationale |
|---|---|
| `ACT` | Distinct modality; ACBS training required |
| `CFT` | Compassion Focused Therapy; Paul Gilbert's dedicated training program required |
| `FAP` | Functional Analytic Psychotherapy; distinct behavioral approach with its own training |
| `EMDR` | EMDR International Association (EMDRIA) certification required; not within CBT/DBT/IPT scope |
| `TF-CBT` | Trauma-Focused CBT for children aged 3–17; requires child specialty training and TF-CBT certification beyond standard adult CBT |
| `NET` | Narrative Exposure Therapy; primarily for refugee/mass trauma populations; requires specific training program |
| `PDT` | Psychodynamic therapy; separate training track |
| `relational` | Relational psychoanalysis; separate training track |
| `object_relations` | Object relations therapy; psychoanalytic training required |
| `EFT` | Emotion-Focused Therapy; York/ICEEFT certification required |
| `AEDP` | Accelerated Experiential Dynamic Psychotherapy; AEDP Institute training required |
| `IFS` | Internal Family Systems; IFS Institute Level 1/2/3 training required |
| `ISTDP` | Intensive Short-Term Dynamic Psychotherapy; Allan Abbass intensive training required |
| `Gottman` | Gottman Method couples therapy; Gottman Institute Level 1/2/3 certification required |
| `narrative` | Narrative therapy; systemic/narrative training track (Dulwich Centre, etc.) |
| `SE` | Somatic Experiencing; Peter Levine's multi-year practitioner training required |
| `SP` | Sensorimotor Psychotherapy; Sensorimotor Psychotherapy Institute certification required |
| `MBSR` | Mindfulness-Based Stress Reduction; requires dedicated MBSR teacher training (200+ hrs), not a psychotherapy competency |
| `MBRP` | Mindfulness-Based Relapse Prevention; addiction specialty program outside CBT/DBT/IPT scope |

**Descriptions updated:** `subdomain` (removed EMDR example), `technique_tags` (removed EMDR and EFT-specific technique examples), `session_event_tags` (updated shame_activation and somatic_activation to reference CBT/DBT/IPT protocols explicitly), `training_level_required` (updated examples), `time_horizon` (updated open_ended description), `notes.recommended_change_items` (noted SE/SP removal).

---

### prompt_config.yaml

**Personas removed — 4:**

| Removed persona | Rationale |
|---|---|
| `acceptance_commitment` | ACT/CFT/FAP outside CBT/DBT/IPT competency scope |
| `psychodynamic` | PDT/relational/object_relations outside CBT/DBT/IPT scope |
| `emotion_focused` | EFT/AEDP outside CBT/DBT/IPT scope |
| `systemic_family` | Structural/Gottman/narrative family therapy outside CBT/DBT/IPT scope |

**Personas updated — 4:**

`default` — Removed references to ACT and psychodynamic approaches. Added explicit out-of-scope redirect instruction: the system will not offer guidance on modalities outside the CBT/DBT/IPT families and will redirect to a modality specialist when those arise.

`trauma_focused` — Removed EMDR (EMDRIA certification required), TF-CBT (child specialty), and NET (refugee/mass trauma specialty). Retained PE and CPT as the two first-line, CBT-based PTSD protocols. Added explicit disclaimer that PE/CPT require formal protocol training beyond general CBT and should not be treated as generic CBT.

`mindfulness_based` — Removed MBSR (wellness/medical program, mindfulness teacher training) and MBRP (addiction specialty). Retained MBCT and mindfulness-as-skill within DBT and CBT. Added explicit redirect to MBSR instructors for MBSR enquiries. Added distinction between MBCT, DBT mindfulness, and CBT attentional retraining functions.

`psychopathology_clinical` — Removed McWilliams as a primary formulation reference (psychoanalytic tradition). Retained Persons, Kuyken-Padesky-Dudley, and Eells as the CBT/integrative formulation tradition. Added explicit language distinguishing *understanding* character structure and developmental history (used to inform CBT/DBT/IPT formulations) from *delivering* psychodynamic treatment.

---

## 2026-06-24 — Psychotherapy domain migration

### metadata_schema.json

**Breaking change.** Complete schema replacement. Requires `scripts/purge_datastore.py --confirm` + `scripts/setup_vertex_search.py` + full re-ingestion before any new corpus ingest.

**Fields removed:**
- `entities` — general biomedical named-entity field ("drugs, conditions, genes, procedures"). Superseded by `technique_tags` (named clinical techniques, psychotherapy-specific). Update `ingestion/metadata_gen.py` `_fallback_extraction()` to not populate this field.
- `evidence_level` — GRADE A/B/C/D scale, designed for medical intervention grading. Replaced by `practice_recommendation_level` which covers the psychotherapy evidence spectrum including polarity values.

**Fields replaced:**
- `domain` — old enum was the general biomedical specialty list (cardiology, oncology, pharmacology, etc.). New enum is psychotherapy-specific: `cognitive_behavioral`, `dialectical_behavior`, `acceptance_commitment`, `trauma_focused`, `psychodynamic`, `interpersonal`, `emotion_focused`, `motivational_interviewing`, `mindfulness_based`, `systemic_family`, `crisis_intervention`, `therapeutic_alliance`, `clinical_supervision`, `psychopathology_clinical`, `psychotherapy_general`, `other`.
- `doc_type` — old enum (textbook, clinical_guideline, research_paper, review_article, case_report, front_matter) extended and replaced with psychotherapy-specific types: `treatment_manual`, `session_transcript`, `case_formulation`, `supervision_material`, `clinical_worksheet`, `textbook`, `clinical_guideline`, `review_article`, `case_report`, `rct_paper`, `meta_analysis`, `outcome_instrument`, `homework_worksheet`, `psychoeducation_material`, `progress_note_template`, `front_matter`.
- `evidence_level` → `practice_recommendation_level` — values: `strongly_recommended`, `recommended`, `expert_consensus`, `theoretical_rationale`, `empirically_derived`, `illustrative`, `use_with_caution`, `contraindicated`, `not_applicable`, `null`. Added `empirically_derived` (RCT-sourced findings not yet in a formal guideline), `use_with_caution`, and `contraindicated` to represent negative polarity recommendations.

**Fields added (new to RTA base):**
- `therapeutic_modality` (array) — chunk-level modality tags; primary filter for modality-specific RTA queries. Enum: CBT, CBT-I, BA, REBT, Schema, DBT, ACT, CFT, FAP, CPT, PE, EMDR, TF-CBT, NET, IPT, IPSRT, PDT, relational, object_relations, EFT, AEDP, MI, MBCT, MBSR, MBRP, IFS, ISTDP, Gottman, narrative, supportive, integrative, SE, SP, UP.
- `clinical_presentation` (array) — diagnostic presentations or clinical themes. Enum includes depression, bipolar, anxiety_general, panic_disorder, social_anxiety, specific_phobia, GAD, PTSD, complex_trauma, OCD, hoarding, bfrb, BPD, ADHD, SUD, eating_disorder, grief_bereavement, chronic_pain, somatic, health_anxiety, psychosis, narcissistic, antisocial, avoidant, dependent, dissociative_disorders, relationship_family, medical_stress, impulse_control, insomnia, autism_spectrum, perinatal, other.
- `session_event_tags` (array) — in-session event types; primary real-time retrieval trigger. Enum covers rupture subtypes, transference, countertransference, doorknob/historical disclosures, crisis, decompensation, flight into health, resistance, intellectualization, boundary testing, alliance building, psychoeducation, exposure, homework review, termination, shame activation, somatic activation, therapist self-disclosure, avoidance safety behavior, minority stress disclosure, cultural mismatch, premature termination signal, grief loss activation, none.
- `session_phase` (string) — treatment arc stage: pre_intake_consultation, assessment_intake, early_treatment, mid_treatment, late_treatment, termination, crisis, any.
- `target_audience` (string) — therapist, trainee, supervisor, patient, general. `patient` is a hard retrieval exclusion from all paths except `analysis_function=homework_resource`.
- `technique_tags` (array) — named clinical techniques; Gemini-extracted proper technique names. Replaces `entities`.
- `clinical_caution` (array) — explicit contraindications or precautions stated in the chunk. Safety field: surfaced alongside technique recommendations, not suppressed.
- `training_level_required` (string) — minimum clinician training level: generalist, supervised_trainee, post_licensure, specialist_trained.
- `risk_dimension_tags` (array) — ongoing risk monitoring dimensions (chronic SI, NSSI, homicide risk, substance relapse, psychotic decompensation, eating disorder medical risk). Drives passive background risk-tracking retrieval on every session, independent of `crisis_escalation` in `session_event_tags`.

**Fields added (ASA extension):**
- `corpus_scope` (string) — `rta_and_asa` (default) or `asa_only`. Hard retrieval routing field. RTA searcher applies `corpus_scope != asa_only` as a mandatory pre-filter.
- `analysis_function` (array) — post-session analysis functions: session_autopsy, case_formulation_update, treatment_plan_revision, homework_resource, outcome_monitoring, risk_documentation, referral_coordination, prognosis_trajectory, supervision_preparation, termination_planning.
- `evidence_base` (string) — epistemological type of the evidence: rct_primary, rct_moderator, meta_analytic, qualitative_research, case_series, single_case, expert_clinical, theoretical, instrument_normative, not_applicable.
- `patient_population` (array) — population for whom evidence applies. Used for treatment matching in ASA.
- `time_horizon` (string) — temporal scope: single_session, near_term, short_term, treatment_course, post_termination, open_ended, any.
- `outcome_measure_tags` (array) — canonical instrument abbreviations (PHQ-9, GAD-7, PCL-5, etc.) referenced in the chunk.

---

### prompt_config.yaml

**Breaking change.** All biomedical personas replaced. `retrieval_instruction` split into two pipeline-mode templates. New template variables added.

**Template variables added:**
- `{n_passages}` — now documented. Was present in `retrieval_instruction` but absent from the variable legend (fixes Known Issue #2 from CLAUDE.md).
- `{pipeline_mode}` — selects between `retrieval_instruction_rta` and `retrieval_instruction_asa`.
- `{session_event}` — detected session event label (RTA only; empty string if not applicable).
- `{therapeutic_modality}` — therapist's current primary modality.

**Retrieval instruction blocks:**
- `retrieval_instruction` (single shared block) → split into `retrieval_instruction_rta` and `retrieval_instruction_asa`. RTA version emphasizes immediate actionability, explicit caution surfacing, and in-session latency constraints. ASA version permits synthesis across passages and multi-hop analysis.

**Personas replaced:**
- Removed: `default` (biomedical), `cardiology`, `oncology`, `pharmacology`, `neurology`, `internal_medicine`, `anatomy`, `physiology`, `biochemistry`.
- Added: `default` (psychotherapy_general), `cognitive_behavioral`, `dialectical_behavior`, `acceptance_commitment`, `trauma_focused`, `psychodynamic`, `interpersonal`, `emotion_focused`, `motivational_interviewing`, `mindfulness_based`, `systemic_family`, `crisis_intervention`, `therapeutic_alliance`, `clinical_supervision`, `psychopathology_clinical`.
- Domain keys match the `domain` enum in `metadata_schema.json`. PromptBuilder falls back to `default` on any miss.

---

### Files created

- `config/CHANGELOG.md` — this file.
- `config/ISSUES.md` — conflicts and open decisions requiring human review before DataStore registration or ingestion.
