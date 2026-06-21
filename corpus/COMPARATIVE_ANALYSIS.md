# Comparative Analysis: Old Corpus vs. New RTA/ASA Corpora

**Documents reviewed:**
- `REVIEW_CORPUS.md` — audit of the prior corpus being replaced
- `CORPUS_NOTES_RTA.md` — curation guide for the new Real-Time Analysis corpus
- `CORPUS_NOTES_ASA.md` — curation guide for the new After-Session Analysis corpus

**Note on metadata schema:** The old corpus had no intelligent metadata schema. The `metadata_schema.json` in the current `rag_guidance` project is a general biomedical template (not a prior-corpus artifact) that has not yet been applied to any ingestion run. The schema comparison in Section 1.5 reflects the contrast between the old corpus's absence of structured metadata and the new schema proposed in the corpus notes documents.

---

## Section 1 — Changes Between Old and New Corpora

### 1.1 Architectural Split: Single Corpus → Dual Pipeline

The old system used one corpus per modality with no distinction between real-time and post-session retrieval. All documents — regardless of type — were fed into the same prefetch cache that drove live 30-second alert generation. The new design introduces two formally separated pipelines:

- **RTA (Real-Time Analysis)** — restricted to procedural, in-session-actionable content only. Governed by `CORPUS_NOTES_RTA.md`.
- **ASA (After-Session Analysis)** — inherits the full RTA corpus and adds document types appropriate only after the session has ended. Governed by `CORPUS_NOTES_ASA.md`.

The routing mechanism is a new `corpus_scope` metadata field with two values: `rta_and_asa` (shared) and `asa_only` (excluded from real-time retrieval). This is a hard filter applied at query time, not a soft ranking signal.

### 1.2 Document Type Curation

**RCT and meta-analysis handling (the central change):**

| Old behavior | New behavior |
|---|---|
| 31 CBT RCTs mixed into `cbt-corpus` alongside 3 manuals; no type filter possible | RCTs excluded entirely from RTA corpus; restricted to ASA corpus only |
| All 11 BA documents are studies with no manual present | BA manuals (Lejuez BATD, Martell) required before RTA inclusion; studies route to ASA |
| All 6 DBT documents are RCTs/meta-analyses; no Linehan manual | DBT corpus rebuilt around Linehan Skills Training Manual and individual therapy manual; existing studies move to ASA |
| All 10 IPT documents are RCTs/studies; no Weissman/Markowitz manual | IPT corpus rebuilt around Weissman/Markowitz/Klerman; studies route to ASA |
| RCT Discussion sections silently ingested with Methods/Results | RTA admits only RCT Discussion sections containing moderator/technique-level insight (Tier 3); full RCTs admitted to ASA Tier 1 |

**`safety-crisis` corpus:** Unchanged — already well-curated; all 9 documents are procedural instruments and clinical protocols appropriate for both pipelines.

**`ebt-corpus`:** Retained. The PE and CBT Social Phobia manuals continue as RTA Tier 1. The reference guide (bibliography) is a candidate for removal; the Deliberate Practice training text is evaluated under the new Tier 2 curation criteria.

**ThousandVoicesOfTrauma transcripts:** All 3,009 synthetic transcripts are PE/PTSD. They were a cross-modal contamination source in the old comprehensive path — PE techniques surfaced during CBT-depression sessions via shared `exhibited_behaviors` tags like "avoidance" and "self-blame." New guidance restricts these transcripts to PE-session queries only via `therapeutic_modality` and `corpus_scope` filtering. The 2 Beck annotated PDFs are retained as RTA Tier 1.

### 1.3 New Modality and Presentation Coverage

**Modalities absent from old corpus, added in new:**

| Modality | Pipeline | Source texts |
|---|---|---|
| EMDR | RTA Tier 1 | Shapiro 3rd ed.; Leeds protocols guide |
| Somatic (SE, SP) | RTA Tier 1 | Ogden, Minton & Pain; Fisher |
| IFS | RTA Tier 1 | Schwartz & Sweezy; Anderson et al. skills manual |
| Youth-specific (TF-CBT, DBT-A, OCD-child) | RTA Tier 1 | Rathus & Miller; Cohen/Mannarino/Deblinger; March & Mulle; Beck CBT children |
| Unified Protocol (UP) | RTA Tier 1 | Barlow et al. (already specified; needs discrete `UP` modality tag) |

**Clinical presentations added to the schema (`clinical_presentation` enum):**

`dissociative_disorders`, `health_anxiety`, `hoarding`, `bfrb`, `autism_spectrum`, `perinatal`

**Session event types added (`session_event_tags` enum):**

`shame_activation`, `somatic_activation`, `therapist_self_disclosure`, `avoidance_safety_behavior`, `minority_stress_disclosure`, `cultural_mismatch`, `premature_termination_signal`, `grief_loss_activation`

**Texts promoted from ASA-only to RTA Tier 2 (RECOMMENDED CHANGE in notes):**

LGBTQ+-affirmative practice (Pachankis/Safren; Austin/Craig) and culturally responsive practice texts (Hays; Lewis-Fernández CFI) — rationale: minority stress disclosures and cultural misattunements are in-session events requiring real-time response, not only post-session reflection.

### 1.4 ASA-Exclusive Content (New Corpus Category)

The ASA corpus adds entire document classes that did not exist in the old corpus in any form:

- RCTs with moderator and mediator analyses (Foa, Resick, Lynch, Barlow, Linehan)
- Meta-analyses and systematic reviews (Cuijpers depression series, Bisson Cochrane PTSD, Flückiger alliance, Wampold/Imel)
- Treatment matching and prescriptive therapy literature (Beutler, Norcross, Cloitre)
- Outcome monitoring instruments and clinical guides (ORS/SRS, PHQ-9, PCL-5, C-SSRS, etc.)
- Patient-facing homework and worksheets (tagged `corpus_scope: asa_only`, `target_audience: patient`)
- Case formulation and longitudinal formulation frameworks (Persons, Eells, Kuyken, Kernberg)
- Stepped care, level-of-care, and referral frameworks (SAMHSA LOCUS, Bower/Gilbody)
- Prognosis and course-of-illness literature (Zanarini McLean Study, Paris BPD, Foa PE predictors)
- Comorbidity and transdiagnostic management literature (Clark/Taylor, Brady PTSD/SUD, McMain DBT/SUD)
- Medication coordination literature — conceptual level only, not prescribing
- Clinician-translated neuroscience (van der Kolk, Porges/Dana)
- Group therapy and adjunctive treatment frameworks (Yalom, MacKenzie, Linehan skills group)
- Termination planning literature — currently absent as a named ASA function (RECOMMENDED CHANGE)

### 1.5 Metadata Schema: From None to Purpose-Built

**Old corpus:** No intelligent metadata schema. The corpus relied on two sources of structure: (1) manually created JSONL metadata files (e.g., `cbt_metadata.jsonl`) containing `document_type` values such as `randomized_controlled_trial`, `treatment_manual`, `clinical_study`, and `therapy_type` tags at the document level; and (2) dataset-provided sidecar metadata from ThousandVoicesOfTrauma (trauma type, exhibited behaviors, client demographics). No chunk-level tagging existed. Retrieval was purely semantic — the model received whatever documents were closest by embedding distance, with no mechanism to filter by document type, session event, or clinical presentation. The `document_type` field in the old JSONLs was never used as a retrieval filter.

**Current project schema (`config/metadata_schema.json`):** A general biomedical template from the `rag_guidance` scaffolding — not derived from the old corpus. It carries domains such as `cardiology`, `oncology`, `pharmacology`, `anatomy`, `biochemistry`; GRADE evidence levels (A/B/C/D); and an `entities` field defined as "drugs, conditions, genes, procedures." A single `psychiatry` enum value exists but subsumes all of psychotherapy into one undifferentiated bucket. This schema has not been applied to any ingestion run; it is the starting point that must be replaced.

**New schema (proposed in `CORPUS_NOTES_RTA.md` and `CORPUS_NOTES_ASA.md`):** A ground-up rebuild:

| Current project schema field | New treatment |
|---|---|
| `domain` — 27-value biomedical enum including `psychiatry` as one value | Replaced with 15-value psychotherapy-specific enum (`cognitive_behavioral`, `dialectical_behavior`, `trauma_focused`, `crisis_intervention`, etc.) |
| `evidence_level` — GRADE A/B/C/D | Replaced with `practice_recommendation_level` (6 values: `strongly_recommended`, `recommended`, `expert_consensus`, `theoretical_rationale`, `illustrative`, `not_applicable`); adds `use_with_caution` and `contraindicated` (RECOMMENDED CHANGE) |
| `entities` — drugs/genes/conditions | Superseded by `technique_tags` (named clinical techniques) |
| `doc_type` — 6 values: textbook, clinical_guideline, research_paper, review_article, case_report, front_matter | Expanded: adds `treatment_manual`, `session_transcript`, `case_formulation`, `supervision_material`, `clinical_worksheet`; and in ASA: `rct_paper`, `meta_analysis`, `outcome_instrument`, `homework_worksheet`, `psychoeducation_material`, `progress_note_template` |
| *(absent)* | `therapeutic_modality` (primary retrieval filter, array of controlled values) |
| *(absent)* | `clinical_presentation` (array) |
| *(absent)* | `session_event_tags` (primary real-time trigger, array) |
| *(absent)* | `session_phase` |
| *(absent)* | `target_audience` (hard exclusion for patient-facing material) |
| *(absent)* | `clinical_caution` (contraindication flags — patient safety field) |
| *(absent)* | `training_level_required` |
| *(absent)* | `risk_dimension_tags` (passive background risk monitoring) |

ASA-exclusive additions: `corpus_scope`, `analysis_function` (9 values), `evidence_base`, `patient_population`, `time_horizon`, `outcome_measure_tags`.

`prompt_config.yaml` must also be rebuilt — current personas are `cardiology`, `oncology`, `pharmacology`, `neurology`, `internal_medicine`, `anatomy`, `physiology`, `biochemistry`. None maps to the psychotherapy use case; all queries currently fall back to `default`.

---

## Section 2 — Pros

**1. Elimination of the core clinical risk in the old system.**
The most urgent documented problem — RCT chunks injected into every live 30-second alert — is structurally resolved by the `corpus_scope` hard filter. Efficacy statistics and CONSORT tables can no longer reach a clinician managing a live session. This was not fixable within the old architecture, which had no type-level filtering mechanism at query time.

**2. Evidence is matched to the clinical context that can use it.**
RCTs and meta-analyses are correctly routed to the ASA pipeline where a post-session clinician has time to read a synthesis and adjust the treatment plan. The old corpus had an all-or-nothing problem (include RCTs everywhere or lose them entirely); the new design resolves it with appropriate placement.

**3. Modality coverage gaps are filled.**
EMDR has Level A evidence from WHO, APA, and ISTSS and is widespread in practice. IFS is now APA-validated for depression and PTSD. Somatic approaches are extensively used in trauma work. Youth-specific therapies are a distinct clinical domain. None had procedural text in the old corpus — the modality tags for EMDR, IFS, SE, and youth presentations were functionally empty.

**4. The metadata schema enables precision retrieval for the first time.**
`session_event_tags` makes event-triggered retrieval actually work: when the session monitor detects a rupture, the searcher filters on `session_event_tags contains "rupture_confrontation"` rather than relying entirely on semantic similarity. `clinical_presentation` and `therapeutic_modality` allow modality-gated queries. None of this was possible with the old system's document-level-only `therapy_type` tags and purely semantic retrieval.

**5. Patient safety fields are introduced.**
`clinical_caution` captures explicit contraindications from source texts (e.g., "imaginal exposure contraindicated without dissociative screening"). `training_level_required` prevents specialist-certification-required guidance from being surfaced to a supervised trainee. Neither existed in any form in the old corpus.

**6. `target_audience` prevents patient-facing content from contaminating clinical retrieval.**
Patient workbooks and homework worksheets are now includable in the ASA corpus without risk of being served as clinical guidance, because `target_audience: patient` is a hard retrieval exclusion in all non-homework query paths.

**7. `analysis_function` enables structured multi-hop ASA retrieval.**
The ASA pipeline can issue a sequence of targeted passes: `session_autopsy` → `treatment_plan_revision` → `homework_resource`, with each pass using the output of the prior as context. The old system had no equivalent architecture.

**8. ThousandVoicesOfTrauma contamination is contained.**
Cross-modality citation risk (PE/PTSD transcripts surfacing during CBT-depression sessions via shared `exhibited_behaviors` terms) is addressed by explicit modality filtering. The value these transcripts have for PE sessions is preserved.

---

## Section 3 — Cons

**1. The corpus does not yet exist in its complete form.**
The new design specifies what should be in the corpus, but the required procedural anchor texts — Linehan's Skills Training Manual, Weissman/Markowitz IPT manual, Shapiro EMDR, Lejuez BATD, Martell BA, Schwartz IFS, Ogden Sensorimotor, Rathus/Miller DBT-A, TF-CBT, and numerous ASA texts — are not currently present. The old corpus, flawed as it was, was at least ingested and queryable.

**2. `corpus_scope` as a safety-critical filter is an operational risk.**
The entire benefit of the RTA/ASA split depends on the RTA searcher reliably enforcing `corpus_scope != "asa_only"` as a hard pre-filter on every query. If this filter is missing, misconfigured, or bypassed during a pipeline refactor, homework worksheets, patient-facing materials, and the RCT corpus silently leak back into real-time retrieval. The old problem resurfaces invisibly, with no alerting mechanism. This is a correctness requirement with no graceful degradation.

**3. Metadata extraction complexity increases substantially.**
The new schema asks Gemini to extract `session_event_tags`, `therapeutic_modality`, `clinical_presentation`, `clinical_caution`, `training_level_required`, `risk_dimension_tags`, `analysis_function`, `evidence_base`, and `patient_population` per chunk. Several require nuanced clinical reasoning (distinguishing `shame_activation` from `decompensation`, identifying `rct_moderator` evidence type). The current `_fallback_extraction()` path will produce silent quality degradation at scale. Prompt engineering and enum-constraint validation for each field requires significant iteration.

**4. ThousandVoicesOfTrauma becomes largely stranded.**
3,009 documents covering only PE/PTSD are now restricted to PE-session queries. For a system spanning CBT, DBT, IPT, BA, IFS, EMDR, and somatic modalities, this is a large corpus investment with a narrow return. Expanding transcript coverage to other modalities would require a new synthetic or annotated dataset, which is not in scope.

**5. The ASA pipeline adds substantial operational complexity.**
Multi-hop retrieval (sequential passes keyed on `analysis_function`) requires a more sophisticated query orchestration layer than the existing single-pass prefetch cache. This is net-new architectural work not present in the current codebase.

**6. Several RECOMMENDED CHANGE items are not yet committed to the schema.**
The `analysis_function` enum is missing `termination_planning`. The `time_horizon` enum is missing `open_ended`. `use_with_caution` and `contraindicated` are missing from `practice_recommendation_level`. The new session event tags (`shame_activation`, `somatic_activation`, etc.) are proposed but absent from the schema JSON. If ingestion begins before these are added, a second schema registration cycle and partial re-ingestion will be required.

**7. `prompt_config.yaml` personas are not rebuilt yet.**
The current file has cardiology, oncology, pharmacology, and other biomedical personas. Until replaced with psychotherapy personas, `PromptBuilder` falls back to `default` for every query, losing all domain-specific expert framing.

**8. `domain` vs. `therapeutic_modality` semantic overlap creates tagging inconsistency risk.**
The notes flag this and propose documenting the distinction (`domain` is document-level; `therapeutic_modality` is chunk-level and may differ). Until codified in both schema descriptions and the Gemini extraction prompt, Gemini will inconsistently assign these fields, degrading filter precision.

---

## Section 4 — Budget Estimation

### 4.1 Corpus Acquisition

| Category | Approx. count | Estimated cost |
|---|---|---|
| Missing RTA Tier 1 manuals (Linehan DBT, Weissman IPT, Lejuez BATD, Martell BA, Shapiro EMDR, Leeds EMDR, Schwartz IFS, Anderson IFS, Ogden Sensorimotor, Fisher, Rathus/Miller DBT-A, Cohen/Mannarino/Deblinger TF-CBT, March/Mulle OCD children, Beck CBT children, Hayes/Strosahl/Wilson ACT, Miller/Rollnick MI 3rd ed., Resick CPT, Klerman IPT, Barlow Unified Protocol, Jobes CAMS, Chow, Eubanks/Muran/Safran, Safran/Muran rupture, Greenberg EFT, Elliott EFT, Paivio EFT, Persons, McWilliams, Eells, Kuyken) | ~30 texts | $1,500–$3,000 |
| ASA Tier 1 additions (Beutler prescriptive, Norcross relationships that work, Lambert prevention of failure, outcome instrument clinical guides, Bryan/Rudd, Simon/Shuman, Greenberger/Padesky Mind Over Mood, Linehan diary cards, Resick CPT patient manual, Barlow UP patient workbook, Eells, Kernberg, Yalom, MacKenzie, Wampold/Imel, Cuijpers meta-analyses, Bisson Cochrane, Flückiger, Cloitre, Egan termination, Marx 1987, Quintana 1993, Norcross 2017 termination, Swift/Callahan, Castonguay/Beutler, Lutz trajectory) | ~25 texts + journal articles | $1,000–$2,500 |
| LGBTQ+ and cultural texts (Pachankis/Safren, Austin/Craig, Hays, Lewis-Fernández CFI, Comas-Díaz, Balsam, Bryant-Davis, Sue/Zane, Hays/Iwamasa, APA multicultural guidelines, Aggarwal CFI) | ~10 texts + free guidelines | $400–$800 |
| Outcome instrument manuals (PHQ-9, GAD-7, PCL-5, BDI-II, ORS/SRS, C-SSRS, AUDIT, MDQ, WHODAS — most freely available from publishers or federal sources) | ~10 instruments | $0–$200 |
| **Total acquisition** | | **$3,000–$6,500** |

### 4.2 GCP Infrastructure

| Item | Estimate |
|---|---|
| Vertex AI Search schema purge + re-registration (`purge_datastore.py` + `setup_vertex_search.py`) | Negligible (API call cost) |
| Gemini metadata extraction: ~512 tokens/chunk × ~50,000–80,000 chunks at Gemini Flash pricing (~$0.075/1M input tokens) | $2–$6 |
| Vertex AI Search indexing at ~$2.50/1,000 documents × 80K documents | ~$200 |
| Ongoing RTA query costs: 3 datastores × 6 retrievals per 25-second window per active session | $0.05–$0.15/session-hour |
| ASA pipeline queries: 3–5 multi-hop retrieval passes per session analyzed | $0.10–$0.30/session analyzed |
| GCS storage for corpus PDFs (~5–10 GB) | $0.10–$0.20/month |

### 4.3 Engineering Time

| Task | Estimate |
|---|---|
| Schema rebuild in `config/metadata_schema.json` + `setup_vertex_search.py` update | 4–8 hrs |
| Gemini extraction prompt redesign and validation (new fields, enum constraints, RTA vs. ASA prompt variants) | 16–24 hrs |
| `corpus_scope` filter enforcement in searcher + RTA/ASA pipeline split | 12–20 hrs |
| `prompt_config.yaml` psychotherapy persona rebuild | 4–8 hrs |
| ASA multi-hop retrieval orchestration (new architecture, no existing analog) | 24–40 hrs |
| Known Issues resolution as prerequisite (`ChunkerConfig.from_yaml()`, `CitationBuilder` import, `{n_passages}` template) | 8–12 hrs |
| Corpus ingestion run + retrieval quality validation | 4–8 hrs |
| **Total engineering** | **72–120 hrs** |

### 4.4 Summary

| Category | Low | High |
|---|---|---|
| Corpus acquisition | $3,000 | $6,500 |
| GCP infrastructure | $210 | $410 |
| Engineering (at $100–150/hr blended) | $7,200 | $18,000 |
| **Total** | **~$10,400** | **~$24,900** |

The dominant cost is engineering time, driven primarily by the ASA multi-hop pipeline and Gemini extraction prompt validation across the expanded schema. Corpus acquisition is a one-time fixed cost. GCP compute per re-ingestion is small relative to labor. Re-ingestion was required regardless of these changes due to the absence of any intelligent metadata schema in the original corpus — this work would have been necessary to unlock retrieval filtering under any schema design.
