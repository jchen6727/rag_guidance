# Corpus and Schema Recommendations
## Reviewer perspective: practicing psychotherapist

This document reviews `CORPUS_NOTES_RTA.md` and `CORPUS_NOTES_ASA.md` for clinical coverage gaps, schema design issues, and safety considerations. Recommendations are grouped by concern type and prioritized (P1 = correctness/safety risk; P2 = significant clinical gap; P3 = refinement).

---

## P1 — Safety and Correctness

### 1.1 Add a `contraindication_tags` or `clinical_caution` field to the schema

The current schema has no mechanism to distinguish a technique that is *recommended* from one that is *contraindicated for certain presentations*. This is a patient safety issue. Examples of contraindicated pairings that a RAG system could surface without this guard:

- Imaginal exposure (PE protocol) for clients with active dissociative disorders — contraindicated without stabilization work first
- Confrontational MI style for clients with psychosis or paranoid features
- Grief work using empty-chair technique (EFT) in active suicidal crisis
- Standard relaxation protocols for trauma clients with freeze/collapse responses (can trigger decompensation)
- Exposure hierarchy construction before adequate alliance is established for OCD

**Recommendation:** Add a `clinical_caution` free-text array field (Gemini-extracted) to capture explicit contraindications or precautions stated in the source chunk. The RTA retrieval system should surface caution flags when it retrieves technique recommendations, not just the recommendation itself.

### 1.2 Add a `training_level_required` field

Several modalities in the `therapeutic_modality` enum require advanced specialized training that is tracked through certifications (EMDR, ISTDP, IFS, Sensorimotor Psychotherapy, AEDP). The system as designed could surface EMDR-specific technique guidance to a trainee who has no EMDR certification and cause harm.

**Recommended enum:**
```
generalist          (any licensed therapist)
supervised_trainee  (appropriate with supervision)
post_licensure      (requires post-licensure clinical experience)
specialist_trained  (requires modality-specific certification or training program)
```

This field belongs in the RTA schema — it is more relevant at session-time than post-session.

### 1.3 Risk monitoring is not only an acute-event concern

Both the RTA and ASA notes treat risk as event-triggered: `session_event_tags: crisis_escalation` fires when suicidality emerges mid-session. This is correct but incomplete. In clinical practice, risk assessment is an ongoing background task for nearly every client — not only those in acute crisis.

**Recommendation:** Add a `risk_dimension_tags` field (array) for chunks that address chronic or baseline risk monitoring, not just acute escalation. Suggested values:

```
suicide_ideation_chronic      (passive SI, baseline monitoring)
self_harm_nonsuicidal         (NSSI patterns outside acute crisis)
homicide_risk                 (ongoing threat-to-others considerations)
substance_relapse_monitoring  (SUD relapse warning signs)
psychotic_decompensation      (prodromal monitoring)
eating_disorder_medical_risk  (AN, purging — physical risk tracking)
```

The RTA system should have a passive risk-tracking retrieval path that runs on every session, not only when `crisis_escalation` is detected.

---

## P2 — Significant Clinical Gaps

### 2.1 EMDR is missing from the RTA Tier 1 corpus

EMDR (Eye Movement Desensitization and Reprocessing) has Level 1 evidence for PTSD (WHO, APA, ISTSS guidelines), is practiced by a very large percentage of trauma therapists, and has a highly structured eight-phase protocol with session-moment-level procedural guidance. The `therapeutic_modality` enum already includes `EMDR`, but no EMDR texts appear in any tier of the RTA corpus.

**Recommended additions to RTA Tier 1:**
- Shapiro, *Eye Movement Desensitization and Reprocessing: Basic Principles, Protocols, and Procedures* (3rd ed., Guilford) — the primary clinical manual
- Shapiro & Forrest, *EMDR: The Breakthrough Therapy for Overcoming Anxiety, Stress, and Trauma* (therapist reference edition)
- Leeds, *A Guide to the Standard EMDR Therapy Protocols for Clinicians, Supervisors, and Consultants*

The corpus notes list PE, CPT, and EMDR in `therapeutic_modality` but only provide source texts for PE and CPT. This asymmetry will cause the RTA system to under-retrieve for EMDR-using therapists.

### 2.2 Somatic and body-based trauma approaches are absent from RTA

The `therapeutic_modality` list includes `SE` (Somatic Experiencing) and could support Sensorimotor Psychotherapy, yet no body-based trauma texts appear in either corpus tier. This is a significant gap: these approaches have substantial clinical uptake for trauma, complex PTSD, and attachment-based presentations.

**Recommended additions to RTA Tier 1:**
- Ogden, Minton & Pain, *Trauma and the Body: A Sensorimotor Approach to Psychotherapy* (clinician guide, Norton)
- Levine, *In an Unspoken Voice: How the Body Releases Trauma and Restores Goodness* (clinical application chapters)
- Fisher, *Healing the Fragmented Selves of Trauma Survivors* — parts-based somatic work

### 2.3 IFS (Internal Family Systems) is in the modality enum but has no corpus representation

IFS is now an APA-validated evidence-based practice for depression, PTSD, and relationship difficulties and is widely used. The `IFS` modality tag is in the enum, but no IFS texts appear in any tier. A therapist doing IFS-guided session work will get no modality-matched guidance.

**Recommended additions to RTA Tier 1:**
- Schwartz & Sweezy, *Internal Family Systems Therapy* (2nd ed., Guilford)
- Anderson, Sweezy & Schwartz (eds.), *Internal Family Systems Skills Training Manual* (PESI)

### 2.4 Adolescent and youth-specific therapy is significantly underrepresented

The `clinical_presentation` enum includes adolescent presentations (depression, anxiety, PTSD, BPD in adolescents), and `patient_population` in the ASA schema includes `adolescent` and `child`. But the RTA Tier 1 corpus lists only one youth-specific text (Barkley's *Defiant Children*, focused on ADHD/behavior). Real-time guidance for a therapist working with an adolescent with depression, self-harm, or family conflict will be inadequate.

**Recommended additions to RTA Tier 1:**
- Beck, *Cognitive Behavior Therapy with Children and Adolescents* (Guilford)
- Rathus & Miller, *DBT Skills Manual for Adolescents* (Guilford) — clinician edition
- Cohen, Mannarino & Deblinger, *Treating Trauma and Traumatic Grief in Children and Adolescents* (TF-CBT manual)
- March & Mulle, *OCD in Children and Adolescents: A Cognitive-Behavioral Treatment Manual*

### 2.5 LGBTQ+ affirmative practice appears only in ASA Tier 2 — it belongs in RTA Tier 2

A therapist working with an LGBTQ+ client needs affirmative practice guidance in real-time, not only post-session. Questions about how to respond to minority stress disclosures, internalized homophobia/transphobia, or coming-out crises are event-driven session moments.

**Recommendation:** Promote LGBTQ+-affirmative texts from ASA Tier 2 to RTA Tier 2, and add session-event-specific tagging (`session_event_tags: ["minority_stress_disclosure"]` — see new tag recommendations below).

**Suggested RTA additions:**
- Pachankis & Safren (eds.), *Handbook of Evidence-Based Mental Health Practice with Sexual and Gender Minorities* (Oxford)
- Austin & Craig (eds.), *Transgender and Gender Nonconforming Psychotherapy*

### 2.6 Culturally specific session-moment guidance is missing from RTA entirely

The ASA notes have a thoughtful section on cultural competency (Sue & Zane, Hays & Iwamasa, Comas-Díaz). But from a clinical standpoint, cultural misattunements happen in-session and need real-time guidance. A therapist who misreads a client's indirect communication style as resistance, or whose direct confrontational style violates the client's cultural norms, needs that correction at the moment of the event.

**Recommendation:** Add at least one culturally responsive psychotherapy text to RTA Tier 2:
- Hays, *Addressing Cultural Complexities in Counseling and Clinical Practice* (APA, 4th ed.)
- Sue, Zane, Hall & Berger (2009), "The case for cultural competency in psychotherapeutic interventions" (Annual Review of Psychology) — review article, session-technique level

Also recommend adding `cultural_mismatch` and `minority_stress_disclosure` to `session_event_tags` (see §3.2).

### 2.7 The `session_event_tags` taxonomy has significant gaps

The current 19-value taxonomy covers the events listed in the PMC reference but omits several clinically common and well-documented in-session events:

| Missing tag | Clinical rationale |
|---|---|
| `shame_activation` | Shame is the central affect in multiple presentations (BPD, trauma, SUD, eating disorders); multiple modalities (CFT, AEDP, EFT, ACT) have specific protocols for shame moments. Shame ≠ guilt ≠ rupture |
| `somatic_activation` | Patient reports or displays body-based distress (physical tension, dissociative numbing, freeze response). Trigger for body-based and trauma-informed interventions. Distinct from decompensation |
| `therapist_self_disclosure` | Therapist uses self-disclosure; has its own literature on indications, contraindications, and management. Not captured by any existing tag |
| `avoidance_safety_behavior` | Within-session safety behaviors (especially in ERP/OCD work and PE). Distinct from general `resistance_avoidance` in that it has a specific clinical protocol response |
| `minority_stress_disclosure` | Client discloses discrimination, microaggression, or structural oppression as content. Requires affirmative response distinct from general historical disclosure |
| `cultural_mismatch` | Therapist detects (or client signals) a cultural misattunement. Requires specific repair different from alliance rupture |
| `premature_termination_signal` | Client signals dropout intention without formal notice. Has its own clinical literature on retention interventions. Distinct from `termination_process` (the planned ending phase) |
| `grief_loss_activation` | Acute grief process emerging mid-session. Distinct from the clinical_presentation tag `grief_bereavement` at the chunk level |

### 2.8 Missing `dissociative_disorders` in `clinical_presentation`

The enum includes `complex_trauma` and `PTSD` but not dissociative disorders (DID, OSDD, depersonalization/derealization disorder). These are clinically distinct presentations with their own treatment literature and session-level event profiles. A client with DID switching parts mid-session is a critical real-time event not captured by the current taxonomy.

**Recommendation:** Add to `clinical_presentation`:
```
dissociative_disorders    (DID, OSDD, DPDR)
health_anxiety            (illness anxiety, somatic symptom disorder — distinct from somatic)
hoarding                  (OCD spectrum but requires distinct protocol)
bfrb                      (body-focused repetitive behaviors: trichotillomania, excoriation)
autism_spectrum           (ASD with mental health comorbidities)
perinatal                 (PPD, PPA, birth trauma — specialized presentation)
```

### 2.9 `SE` is missing from the `therapeutic_modality` enum

The notes list `SE` in the domain vocabulary description but it does not appear in the `therapeutic_modality` JSON array in either schema definition. Also missing:

```
SE                (Somatic Experiencing — Levine)
SP                (Sensorimotor Psychotherapy — Ogden)
EMDR-AIP          (EMDR's Adaptive Information Processing model explicitly)
UP                (Unified Protocol — transdiagnostic; distinct from individual modalities)
TFCBT             (TF-CBT — already listed as TF-CBT but ensure consistent casing)
```

---

## P3 — Schema Design Refinements

### 3.1 `session_phase` is missing a pre-therapy consultation stage

The current enum begins at `assessment_intake`. In practice, many clinicians see clients for a pre-therapy consultation or matching session before formal treatment begins. This phase has its own literature (motivational interviewing for engagement, expectancy setting, treatment matching). Suggested addition: `pre_intake_consultation`.

### 3.2 The `domain` and `therapeutic_modality` fields carry overlapping signal

`domain: trauma_focused` and `therapeutic_modality: [PE, CPT]` partially duplicate each other, which will create inconsistent Gemini tagging. The `domain` field appears to be for the primary modality family of the *source document*, while `therapeutic_modality` captures what the *chunk* addresses. This distinction should be documented explicitly in schema comments and extraction prompt instructions, or the redundancy should be collapsed.

**Recommendation:** Add a comment to `config/metadata_schema.json` clarifying: `domain` is a document-level property assigned from the source's primary orientation; `therapeutic_modality` is a chunk-level property extracted from the passage content and can differ from the document's domain.

### 3.3 `practice_recommendation_level` needs a negative polarity value

The current five levels (`strongly_recommended` through `not_applicable`) all describe degrees of positive support. Clinical literature also contains explicit *cautionary* and *contraindicated* guidance — e.g., "this technique should not be used in the first three sessions," "MI without CBT is insufficient for BPD," "avoid direct challenge of delusions." There is no way to represent this.

**Recommended additions:**
```
use_with_caution    (technique has evidence but requires specific preconditions)
contraindicated     (explicitly advised against in this context)
```

This pairs with the `clinical_caution` field recommended in §1.1.

### 3.4 The ASA `analysis_function` enum is missing `termination_planning`

The ASA notes cover relapse prevention under "prognosis_trajectory" and mention termination under session phases, but there is no dedicated `analysis_function` value for termination planning. In clinical practice, the termination phase generates a distinct post-session analysis task — reviewing the client's progress against treatment goals, managing termination-related emotions (dependency, abandonment), and writing the formal termination summary. This is distinct from `prognosis_trajectory` (which is about expected course of illness) and `treatment_plan_revision` (which assumes ongoing treatment).

**Recommendation:** Add `termination_planning` to the `analysis_function` enum with associated corpus additions:
- Egan, *Termination of Psychotherapy: The Crucial Last Chapter in Psychotherapy Treatment* (Routledge)
- Marx & Gelso (1987), "Termination of individual counseling in a university counseling center" — foundational research on planned termination
- Quintana (1993), "Toward an expanded and updated conceptualization of termination" — conceptual framework

### 3.5 The ASA `time_horizon` field doesn't accommodate open-ended treatment

Many clients are in open-ended psychotherapy (psychodynamic, relational, ongoing supportive). The current `time_horizon` values (`near_term`, `short_term`, `treatment_course`, `post_termination`) all implicitly assume time-limited treatment. For open-ended work, `treatment_course` is the closest fit but doesn't accurately represent a case that has been ongoing for two years with no defined endpoint.

**Recommendation:** Add `open_ended` to `time_horizon` for retrieval contexts where the clinician is not operating within a defined protocol arc.

### 3.6 The RTA Tier 3 guidance on meta-analyses is too restrictive

The notes say to include meta-analyses "only" when they synthesize technique-level findings, and to use only abstract and discussion sections. From a clinical standpoint, moderator tables from meta-analyses — showing for which patient characteristics a technique's effect size rises or falls — are directly useful to a mid-session clinician trying to calibrate their approach. The restriction on Results sections is too broad.

**Recommendation:** Revise to: "Include meta-analyses when they report moderator or mechanism findings. Exclude aggregate-only effect size summaries (e.g., g = 0.74 across 32 studies). In RCT partial-ingestion, include Results tables that report subgroup or moderator findings, not only the Discussion."

### 3.7 The `entities` field in `metadata_schema.json` is not mentioned in either CORPUS_NOTES document

The current schema has an `entities` field ("Named clinical/scientific entities: drugs, conditions, genes, procedures") that does not appear in either corpus note's field inventory. It is likely a carryover from the biomedical schema.

For psychotherapy, "named entities" would mean named techniques, named instruments, and named models rather than drugs or genes. The field should either be repurposed to capture `named_models_and_techniques` (e.g., "EMDR Phase 2," "DBT chain analysis," "Jobes CAMS protocol") or removed.

**Recommendation:** Either rename `entities` to `named_techniques` in `metadata_schema.json` to align with the psychotherapy context, or remove it and allow `technique_tags` to absorb the same function.

### 3.8 Cultural formulation tools are absent from both corpora

The DSM-5 Cultural Formulation Interview (CFI) and its supplementary modules are validated, freely available structured tools that guide therapists through cultural formulation in both intake and ongoing treatment. These are not mentioned in either corpus notes document despite the broader emphasis on cultural competence.

**Recommendation (RTA Tier 2):**
- Lewis-Fernández et al., *DSM-5 Handbook on the Cultural Formulation Interview* (APA)
- Aggarwal et al. (2016), "Using the Cultural Formulation Interview to build culturally sensitive services" — implementation guide

---

## Summary Prioritization

| # | Recommendation | Priority | Affected file(s) |
|---|---|---|---|
| 1.1 | Add `clinical_caution` field | P1 | Schema, CORPUS_NOTES_RTA |
| 1.2 | Add `training_level_required` field | P1 | Schema, CORPUS_NOTES_RTA |
| 1.3 | Add chronic risk monitoring path | P1 | CORPUS_NOTES_RTA, CORPUS_NOTES_ASA |
| 2.1 | Add EMDR to RTA Tier 1 | P2 | CORPUS_NOTES_RTA |
| 2.2 | Add somatic/body-based trauma texts to RTA Tier 1 | P2 | CORPUS_NOTES_RTA |
| 2.3 | Add IFS texts to RTA Tier 1 | P2 | CORPUS_NOTES_RTA |
| 2.4 | Add youth-specific therapy texts to RTA Tier 1 | P2 | CORPUS_NOTES_RTA |
| 2.5 | Promote LGBTQ+-affirmative texts to RTA Tier 2 | P2 | CORPUS_NOTES_RTA, CORPUS_NOTES_ASA |
| 2.6 | Add culturally responsive texts to RTA Tier 2 | P2 | CORPUS_NOTES_RTA |
| 2.7 | Extend `session_event_tags` (8 new values) | P2 | Schema, CORPUS_NOTES_RTA |
| 2.8 | Add `dissociative_disorders` and other presentations | P2 | Schema, CORPUS_NOTES_RTA |
| 2.9 | Add `SE`, `SP`, `UP` to `therapeutic_modality` | P2 | Schema |
| 3.1 | Add `pre_intake_consultation` to `session_phase` | P3 | Schema |
| 3.2 | Clarify `domain` vs. `therapeutic_modality` semantics | P3 | Schema comments |
| 3.3 | Add `use_with_caution` / `contraindicated` to `practice_recommendation_level` | P3 | Schema |
| 3.4 | Add `termination_planning` to ASA `analysis_function` | P3 | CORPUS_NOTES_ASA |
| 3.5 | Add `open_ended` to ASA `time_horizon` | P3 | CORPUS_NOTES_ASA |
| 3.6 | Relax Tier 3 meta-analysis restriction on Results sections | P3 | CORPUS_NOTES_RTA |
| 3.7 | Repurpose or remove `entities` field | P3 | Schema, CORPUS_NOTES_RTA |
| 3.8 | Add DSM-5 Cultural Formulation Interview materials | P3 | CORPUS_NOTES_RTA, CORPUS_NOTES_ASA |
