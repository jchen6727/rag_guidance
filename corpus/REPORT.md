# Stakeholder Decision Report
## TherAssist Corpus Rebuild — Critical Decisions Required

This document summarizes the decisions that require clinical or business judgment before implementation can proceed. Each item is categorized by difficulty of implementation and relative cost.

Difficulty ratings reflect combined engineering effort, clinical curation effort, and operational risk.
Cost ratings reflect direct spend (corpus acquisition + GCP compute + engineering hours).

---

## EASY — Low effort, low cost, clear benefit

**1. Purge and re-register the metadata schema**
The current schema is a biomedical template (cardiology, oncology domains; GRADE A–D evidence levels). It must be replaced with a psychotherapy-specific schema before any ingestion run. This is a one-time infrastructure step with well-defined scripts.
- *Decision:* Approve the schema replacement in `config/metadata_schema.json` as the first step before any corpus work.
- *Cost:* Negligible (API call cost).

**2. Rebuild `prompt_config.yaml` with psychotherapy personas**
The current config has cardiology, oncology, and pharmacology expert personas. Every query currently falls back to a generic `default` persona. Replacing this with psychotherapy domain personas (cognitive_behavioral, trauma_focused, psychodynamic, crisis_intervention) immediately improves all query quality.
- *Decision:* Approve persona rebuild. No corpus changes required.
- *Cost:* 4–8 engineering hours.

**3. Keep the `safety-crisis` corpus as-is**
The 9 documents (988 Lifeline, C-SSRS, SAFE-T, SAMHSA TIP50, Stanley-Brown Safety Planning) are the best-curated corpus in the stack. No changes needed; carry forward into both RTA and ASA pipelines.
- *Decision:* No action required. Retain as-is.

**4. Restrict ThousandVoicesOfTrauma to PE-session queries only**
All 3,009 synthetic transcripts are Prolonged Exposure / PTSD. They were surfacing during CBT-depression and DBT sessions via shared terms like "avoidance." Adding a `therapeutic_modality: PE` filter at query time stops the cross-modal contamination without deleting or re-ingesting the documents.
- *Decision:* Approve filter addition. No new documents needed.
- *Cost:* 2–4 engineering hours (searcher filter change).

---

## MEDIUM — Moderate effort or requires clinical input on scope

**5. Which therapy modalities to support at launch?**
The new corpus framework covers CBT, DBT, PE, CPT, ACT, IPT, BA, EFT, MI, and adds EMDR, IFS, somatic (SE/SP), and youth-specific variants (TF-CBT, DBT-A). Supporting all modalities requires acquiring ~30 additional treatment manuals. A narrower launch covering only the highest-volume modalities (CBT, DBT, PE, BA, IPT) reduces initial corpus cost by roughly half and simplifies the first ingestion run.
- *Decision needed:* Select modalities for Phase 1 launch. Defer others to Phase 2.
- *Cost impact:* Full scope ~$3,000–$4,500 in manuals; narrowed CBT/DBT/PE/BA/IPT scope ~$1,500–$2,000.

**6. Include LGBTQ+-affirmative and culturally responsive texts in RTA (real-time)?**
These texts currently appear only in the ASA corpus. The corpus notes recommend promoting them to RTA Tier 2 because minority stress disclosures and cultural misattunements are in-session events requiring real-time guidance. This requires sourcing ~10 additional texts.
- *Decision needed:* RTA inclusion now, or ASA-only to start?
- *Cost impact:* $400–$800 in texts; 4–8 hours additional ingestion work.

**7. Phased vs. full schema deployment**
The proposed schema adds 10+ new fields per chunk (`session_event_tags`, `therapeutic_modality`, `clinical_presentation`, `clinical_caution`, `training_level_required`, `risk_dimension_tags`, etc.). Several RECOMMENDED CHANGE items (new session event tags, `use_with_caution`/`contraindicated` recommendation levels, `termination_planning` analysis function) are not yet finalized in the schema JSON. A phased approach ships the core fields now and adds clinical safety and edge-case fields in a second ingestion run.
- *Decision needed:* Ship full schema in one run (requires finalizing all RECOMMENDED CHANGE items first), or phase fields across two ingestion runs?
- *Cost impact:* Two ingestion runs adds ~$200–$400 in GCP compute and 8–12 hours validation; single run requires 2–4 weeks of schema finalization upfront.

**8. What to do with the ThousandVoicesOfTrauma corpus long-term?**
The PE/PTSD restriction makes these 3,009 documents useful for PE sessions but inert for everything else. Options: (a) keep as-is, narrow utility; (b) supplement with synthetic or annotated transcripts for other modalities (significant cost and time); (c) retire the corpus when better transcript coverage becomes available.
- *Decision needed:* Retain for PE sessions, actively seek alternative transcript sources, or plan deprecation?
- *Cost impact:* Retention = no cost; expansion = significant research/data cost (not currently scoped).

---

## HARD — High engineering effort, clinical-legal judgment, or new architecture required

**9. Do you want a full After-Session Analysis (ASA) pipeline?**
The ASA pipeline is the most significant new component: multi-hop retrieval (3–5 sequential query passes per session), a separate document corpus with 25+ additional texts, new metadata fields (`analysis_function`, `evidence_base`, `patient_population`, `time_horizon`), and Gemini extraction prompts tuned for post-session analytical queries. The clinical value is high — it enables longitudinal case formulation, treatment plan revision, homework selection, and outcome monitoring integration. But this is a net-new architectural component with no equivalent in the current codebase.
- *Decision needed:* Is the ASA pipeline in scope for this build cycle? If so, should it be built concurrently with RTA or as a follow-on phase?
- *Cost impact:* ASA pipeline alone is ~$5,000–$9,000 in engineering. Deferring to Phase 2 cuts the current build scope by roughly 40%.

**10. Should RCTs and meta-analyses be included in the ASA corpus?**
The ASA design routes RCTs to the post-session context where clinicians can use research evidence for treatment planning. This is clinically appropriate and reflects standard-of-care supervision practice. However, surfacing specific RCT findings to clinicians as decision support raises questions about how results will be framed, whether moderator data (e.g., "PE has higher dropout in this PTSD subtype") is appropriate for a tool the therapist may cite back to patients, and whether including research evidence in a clinical support tool creates liability exposure.
- *Decision needed:* Approve RCT/meta-analysis inclusion in ASA with appropriate framing, or restrict ASA to procedural manuals and guidelines only?
- *Cost impact:* Excluding RCTs simplifies ASA corpus acquisition and Gemini prompt design; including them is the primary clinical value proposition of the ASA pipeline.

**11. Clinical safety field implementation (`clinical_caution`, `training_level_required`)**
`clinical_caution` flags contraindications extracted from source texts (e.g., "do not use imaginal exposure without dissociative screening"). `training_level_required` prevents specialist-certification-required techniques from being surfaced to supervised trainees. These fields require Gemini to extract negative and precautionary statements reliably — a different extraction task than identifying what a technique does. They also require a UI-level decision: how should the application surface a retrieved technique that carries a `clinical_caution` flag? Suppression? Warning badge? Separate display? This is a joint engineering + clinical UX decision.
- *Decision needed:* Approve these fields and define how the application should present caution-flagged content.
- *Cost impact:* 8–16 hours engineering for extraction and display logic; requires clinical review of caution presentation design.

---

## Summary Decision Matrix

| # | Decision | Difficulty | Cost |
|---|---|---|---|
| 1 | Approve schema purge and re-registration | EASY | Negligible |
| 2 | Rebuild `prompt_config.yaml` with psychotherapy personas | EASY | Low |
| 3 | Retain `safety-crisis` corpus as-is | EASY | None |
| 4 | Restrict ThousandVoicesOfTrauma to PE queries | EASY | Low |
| 5 | Choose modalities for Phase 1 launch | MEDIUM | Medium (scope-dependent) |
| 6 | LGBTQ+/cultural texts in RTA or ASA-only? | MEDIUM | Low–Medium |
| 7 | Phased vs. full schema deployment | MEDIUM | Medium |
| 8 | Long-term plan for ThousandVoicesOfTrauma | MEDIUM | Low–High (option-dependent) |
| 9 | Build ASA pipeline now or defer to Phase 2? | HARD | High |
| 10 | Include RCTs/meta-analyses in ASA? | HARD | Medium + legal review |
| 11 | Clinical safety fields and caution display design | HARD | Medium + clinical UX review |

---

## Suggested Sequencing

If building incrementally:

**Phase 1 (RTA only, highest-priority modalities):** Decisions 1, 2, 3, 4, 5, 7. Deliver a real-time system with procedural-only corpora, no RCT contamination, and functional metadata filtering. Estimated total: $5,000–$10,000.

**Phase 2 (Full modality coverage + cultural/LGBTQ+ texts):** Decisions 6, 8. Expand RTA to full modality set and add affirmative practice guidance. Estimated incremental: $2,000–$4,000.

**Phase 3 (ASA pipeline):** Decisions 9, 10, 11. Build after-session analysis as a distinct product feature with its own UI. Estimated incremental: $6,000–$12,000.
