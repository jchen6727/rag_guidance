# After-Session Analysis (ASA) Corpus Notes

This corpus body is designed for the **after-session analysis** pipeline: a slower, compute-budget-generous process that runs after a therapy session has concluded. It serves two distinct analytical functions:

1. **Session Autopsy** — retrospective reconstruction of what happened in the session, naming the clinical events that occurred, evaluating the therapist's response quality, and surfacing missed opportunities or areas requiring supervisory attention.

2. **Longitudinal Management** — synthesizing the session's events against the broader treatment arc to update the case formulation, generate treatment plan adjustments, suggest homework assignments, flag referral considerations, and provide prognosis-informed recommendations.

This pipeline is architecturally related to the real-time analysis (RTA) system described in `CORPUS_NOTES_RTA.md`, but operates under different constraints: it is not time-bounded by a live clinical exchange, it may issue multi-hop retrieval calls, it may synthesize across dozens of passages, and it may draw on document types that are too slow or too abstract to be useful in-session.

**The full RTA corpus is also available to the ASA system.** This document describes what is *added* to that base — documents that are inappropriate for real-time retrieval but are valuable for the reflective, post-session mode. When there is no specific reason to separate corpora at the DataStore level, tag documents with `corpus_scope` (see Schema section) to route queries appropriately.

---

# Corpus Curation Guide

## Governing Principle

The ASA system answers two question families, not one:

- **Autopsy**: *"What clinically significant events occurred in this session, what do they mean, and how well were they handled?"*
- **Longitudinal**: *"Given where this patient now stands in their treatment, what does the best available evidence and clinical literature recommend for next steps?"*

The second question is the key departure from the RTA corpus: **evidence from controlled research is now directly actionable** because the clinician has time to read a synthesis, weigh treatment options, and adjust the treatment plan before the next session. A meta-analysis showing that a particular augmentation strategy improves outcomes for treatment-resistant cases of the patient's presentation type is genuinely useful here. So is a patient-facing thought record the clinician can review, adapt, and assign as homework.

Curation should prioritize: **depth of evidence, breadth of clinical scope, and utility for between-session clinical decision-making.**

---

## Documents to Include ("Good ASA Corpus")

### Tier 1 — Core (Highest analytical value)

**All RTA Tier 1 and Tier 2 documents**
The procedural treatment manuals, session transcripts, deliberate practice texts, rupture/repair literature, and clinical practice guidelines from the RTA corpus are equally valuable for session autopsy. The ASA system retrieves them to name what happened ("the therapist failed to address a confrontation rupture at minute 34") and to evaluate the response against best-practice benchmarks. Include the full RTA corpus in the ASA DataStore.

**RCTs and multi-site clinical trials (psychotherapy and combined treatment arms)**
This is the primary expansion beyond the RTA corpus. After a session, the clinician can benefit from knowing: "For patients with this patient's comorbidity profile, what does the randomized evidence say about augmenting CBT with an additional modality?" or "Is there RCT support for switching from PE to CPT for PTSD non-responders?"

Include RCTs where:
- At least one treatment arm is a psychotherapy (not drug-only)
- The paper reports session-level or component-level moderators, not only aggregate outcomes
- The patient population matches the target presentations in `CORPUS_NOTES_RTA.md`
- The Discussion/Implications sections contain clinically actionable findings

Prioritize RCTs with **moderator and mediator analyses** — these answer "for whom and through what mechanism" rather than just "does it work," which is the relevant question for an individual patient.

Examples:
- Foa et al. (1999, 2005), PE vs. SIT vs. combined — PTSD
- Resick et al. (2002, 2008), CPT vs. PE for PTSD — differential response by presentation
- Lynch et al. (2007), DBT for older adults with treatment-resistant depression — population moderator data
- Barlow et al. (2017), Unified Protocol RCT — transdiagnostic moderators
- Linehan et al. (2006), DBT vs. CTBE for BPD — component analysis

**Meta-analyses and systematic reviews (all levels of clinical focus)**
Where the RTA corpus admits only technique-level reviews, the ASA corpus admits the full range: aggregate effect size reviews, moderator meta-analyses, network meta-analyses comparing multiple treatments, and systematic reviews of adverse events or dropout predictors.

Especially valuable:
- Cuijpers et al. (ongoing series) — meta-analyses of psychological treatments for depression
- Bisson et al. (Cochrane) — psychological therapies for PTSD
- Ost (2008 and updates) — efficacy of ACT
- Weisz et al. — youth psychotherapy meta-analyses
- Flückiger et al. (2018) — therapeutic alliance meta-analysis (also in RTA)
- Norcross & Lambert — common factors systematic reviews
- Wampold & Imel, *The Great Psychotherapy Debate* (2nd ed.) — contextual model evidence

**Treatment matching and prescriptive therapy literature**
Research and clinical frameworks specifically addressing which patients respond to which treatments — directly relevant to longitudinal plan adjustment.

Examples:
- Beutler et al., *Prescriptive Psychotherapy* — systematic treatment selection model
- Swift & Callahan, *A Delay Discounting Rationale for Two-Phase Treatment of Depression*
- Castonguay & Beutler (eds.), *Principles of Therapeutic Change That Work* (APA)
- Norcross (ed.), *Psychotherapy Relationships That Work* (3rd ed.) — tailoring to patient characteristics
- Cloitre et al. (2010, 2011) — Phase-based vs. direct trauma processing for complex PTSD (treatment sequencing)

**Outcome monitoring and progress feedback systems**
After-session analysis is the natural moment to integrate outcome monitoring data (PHQ-9, GAD-7, ORS/SRS, PCL-5, BDI, DASS, MDQ, etc.) with session content. Include both the clinical literature on outcome monitoring and the administration/interpretation guides for instruments.

Examples:
- Lambert, *Prevention of Treatment Failure* (APA) — ORS/SRS, PCOMS
- Miller, Duncan & Hubble, *Heart and Soul of Change* — feedback-informed treatment
- Lutz et al. — early treatment response and trajectory modeling
- Instrument manuals: ORS/SRS (Partners for Change), PCL-5 (PTSD Checklist), PHQ-9 clinical guide, CAMS (Columbia-Suicide Severity Rating Scale), C-SSRS administration guide
- Whitebird et al. — routine outcome monitoring implementation guides

**Between-session homework and patient-facing intervention materials**
The ASA system is the appropriate place to retrieve, review, and tailor homework for the upcoming session. Patient-facing worksheets, thought records, exposure hierarchies, behavioral activation schedules, and diary card templates are now relevant — but only in the clinical context of a therapist selecting and customizing them, not as direct patient-accessible content.

Examples:
- Greenberger & Padesky, *Mind Over Mood* (2nd ed.) — worksheets the therapist reviews and assigns
- Linehan DBT diary cards and chain analysis worksheets
- Foa et al. PE patient workbook (for therapist review of homework structure)
- Resick et al. CPT patient manual — impact statements, stuck point logs, worksheets
- Barlow et al. Unified Protocol patient workbook — for homework assignment planning
- Any modality-specific homework templates in the existing Tier 1 treatment manuals' appendices

Tag all patient-facing materials `target_audience: patient` and `corpus_scope: asa_only` so they are excluded from real-time retrieval but available post-session.

**Case conceptualization and longitudinal formulation frameworks**
The session autopsy must update the working case formulation. Include texts that provide structured frameworks for integrating new session data into the ongoing formulation.

Examples:
- Persons, *The Case Formulation Approach to Cognitive-Behavior Therapy* (Guilford)
- Eells (ed.), *Handbook of Psychotherapy Case Formulation* (Guilford, 3rd ed.)
- McWilliams, *Psychoanalytic Case Formulation*
- Kuyken, Padesky & Dudley, *Collaborative Case Conceptualization*
- Kernberg et al., *Psychodynamic Therapy for Personality Pathology* (formulation-focused)

**Risk management documentation and clinical decision frameworks**
After a session in which suicidality, self-harm, homicidality, or severe decompensation occurred, the ASA system should retrieve structured frameworks for risk documentation, safety planning updates, duty-to-warn analysis, and level-of-care escalation criteria.

Examples:
- Jobes, *Managing Suicidal Risk* (CAMS framework) — also in RTA, doubly relevant here
- Bryan & Rudd, *Brief Cognitive-Behavioral Therapy for Suicide Prevention* — risk tiering
- Stanley & Brown — Safety Planning Intervention documentation guide
- APA Practice Guidelines for Assessment and Treatment of Patients with Suicidal Behaviors
- SAMHSA TIP 50 — Addressing Suicidal Thoughts and Behaviors in Substance Abuse Treatment
- Simon & Shuman (eds.), *Clinical Manual of Psychiatry and Law* — documentation standards

# RECOMMENDED CHANGE
**Termination planning — currently absent from Tier 1 as a named function**
Termination is a major clinical event with its own post-session analysis demands: reviewing progress against treatment goals, managing termination-related affect (dependency, abandonment, grief), and producing a formal termination summary. This is distinct from `prognosis_trajectory` (expected illness course) and `treatment_plan_revision` (ongoing treatment). The ASA system lacks both a dedicated corpus section and a named `analysis_function` value for it (see schema recommendations below).

Recommended additions to Tier 1:
- Egan, *Termination of Psychotherapy: The Crucial Last Chapter in Psychotherapy Treatment* (Routledge)
- Marx & Gelso (1987), "Termination of individual counseling in a university counseling center" — foundational research on planned termination
- Quintana (1993), "Toward an expanded and updated conceptualization of termination" — conceptual framework
- Norcross, Zimmerman, Greenberg & Swift (2017), "Do all therapists do that when saying goodbye?" — empirical study on termination practices
# END RECOMMENDED CHANGE

### Tier 2 — Supplementary (Moderate analytical value)

**Stepped care, level-of-care, and referral frameworks**
After a session, the clinician may need to consider whether the patient requires higher-intensity services (PHP, IOP, inpatient), adjunctive services (group therapy, peer support), or specialist referral (neuropsychological assessment, medication evaluation, pain management). Include frameworks for these decisions.

Examples:
- SAMHSA LOCUS (Level of Care Utilization System) clinical guide
- Bower & Gilbody — stepped care model literature
- APA Guidelines on referral to higher levels of care (disorder-specific)
- Kessler & Stafford, *Collaborative Medicine Case Studies* — primary care integration models
- Roy-Byrne et al. — collaborative care for anxiety and depression

**Prognosis and longitudinal course-of-illness literature**
Understanding the expected trajectory of a patient's presentation informs treatment planning and realistic goal-setting. Include empirical data on treatment response predictors, dropout predictors, relapse rates, and long-term outcome moderators.

Examples:
- Whisman et al. — predictors of CBT response for depression
- Kessler et al. — longitudinal course of anxiety disorders
- Paris, *Prognosis of Borderline Personality Disorder* — long-term outcome data for BPD
- Zanarini et al. (McLean Study of Adult Development) — prospective BPD outcome data
- Foa et al. — predictors of PE dropout and non-response
- Driessen & Hollon — predictors of treatment response in depression

**Comorbidity and transdiagnostic management literature**
Patients rarely present with a single diagnosis. After a session, the clinician may need to reason about how co-occurring presentations interact, complicate the primary treatment, or require sequenced or integrated intervention.

Examples:
- Clark & Taylor — transdiagnostic cognitive model
- Orsillo & Roemer, *Acceptance-Based Behavioral Therapies* — transdiagnostic emotion dysregulation
- Barlow et al., *Clinical Handbook of Psychological Disorders* (5th ed.) — comorbidity chapters
- Brady et al. — PTSD and SUD co-occurrence treatment
- Otto & Smits (eds.) — anxiety and mood comorbidity
- McMain et al. — DBT for BPD with comorbid SUD

**Cultural, diversity, and contextual factors in treatment planning**
Longitudinal management must account for cultural context, identity factors, socioeconomic stressors, and structural barriers to care that shape both how therapy should be conducted and what referrals are realistic.

Examples:
- Sue & Zane — culturally responsive psychotherapy
- Hays & Iwamasa (eds.), *Culturally Responsive Cognitive-Behavioral Therapy* (APA)
- Comas-Díaz, *Multicultural Care: A Clinician's Guide to Cultural Competence*
- APA Guidelines on Multicultural Education, Training, Research, Practice, and Organizational Change
- Balsam et al. — LGBTQ-affirmative psychotherapy frameworks
- Bryant-Davis — trauma treatment with Black clients

# RECOMMENDED CHANGE
**Cultural Formulation Interview materials — currently absent**
The DSM-5 Cultural Formulation Interview (CFI) and its supplementary modules are validated, freely available structured tools for conducting cultural formulation in intake and ongoing treatment. These are directly relevant to post-session case formulation updates when the session surfaced cultural factors.

Recommended additions:
- Lewis-Fernández et al., *DSM-5 Handbook on the Cultural Formulation Interview* (APA)
- Aggarwal et al. (2016), "Using the Cultural Formulation Interview to build culturally sensitive services" — implementation guide for clinicians

Tag: `analysis_function: ["case_formulation_update"]`, `corpus_scope: asa_only`

**Note on LGBTQ+ materials:** These texts are currently ASA-only. The same materials should also be present in the RTA corpus at Tier 2, since cultural misattunements and minority stress disclosures are in-session events requiring real-time guidance.
# END RECOMMENDED CHANGE

**Medication coordination and prescriber communication**
When a patient is receiving concurrent pharmacotherapy, the ASA system may need to flag potential drug-therapy interactions, help the therapist formulate a communication to the prescribing psychiatrist, or provide context for the patient's medication-related concerns raised in session. This is not prescribing guidance — it is coordination-of-care knowledge.

Include: brief overviews of pharmacotherapy commonly co-prescribed with psychotherapy (SSRIs, SNRIs, mood stabilizers, atypical antipsychotics at a conceptual level), and frameworks for therapist-prescriber communication.

Examples:
- Beitman & Saveanu, *Integrating Psychotherapy and Pharmacotherapy*
- Hollon & DeRubeis, *Combination treatments for depression* (conceptual and research overview)
- APA/American Psychiatric Association joint guidance on integrated care
- Specific chapters in modality manuals addressing medication context (e.g., PE manual's section on concurrent medication)

**Translational neuroscience (clinician-facing level only)**
Unlike the RTA corpus, the ASA system can support a brief synthesis of relevant neuroscience when it directly informs a clinical recommendation. The criterion is whether the science has been translated into clinical implications by the source document itself.

Examples:
- van der Kolk, *The Body Keeps the Score* — trauma neuroscience at clinical application level
- LeDoux & Pine — translated fear-circuit science for clinical understanding
- Porges, *The Polyvagal Theory in Therapy* (Deb Dana's clinical adaptation) — translated autonomic science
- Specific chapters in APA handbooks where mechanism-level findings are translated to technique selection

Exclude: primary neuroimaging studies, fMRI protocols, EEG research, animal models.

**Group therapy and adjunctive treatment formats**
The ASA system may recommend adding group therapy, skills groups, or other adjunctive modalities. Include texts describing when and how to make these recommendations.

Examples:
- Yalom & Leszcz, *The Theory and Practice of Group Psychotherapy* (5th ed.)
- MacKenzie, *Introduction to Time-Limited Group Psychotherapy*
- Linehan DBT skills training group manual
- McRoberts et al. — individual vs. group therapy comparative literature

### Tier 3 — Selective Inclusion (Narrow analytical value; curate carefully)

**Qualitative research on therapy process and patient experience**
High-quality qualitative studies on how patients experience therapy, what they find helpful or harmful, and how they describe their recovery can inform the longitudinal perspective — especially for patients who have not responded or have dropped out.

Criteria for inclusion: peer-reviewed, uses recognized qualitative methodology (IPA, grounded theory, thematic analysis), explicitly focused on psychotherapy process rather than general mental health experience.

**Psychometric instrument full manuals**
Assessment instrument manuals are now relevant when the therapist needs to interpret a patient's formal assessment results, track change over time, or select an appropriate between-session monitoring tool. Include complete administration and scoring guides for commonly used instruments.

Examples: PHQ-9, GAD-7, PCL-5, BDI-II, DASS-21, ORS/SRS, AUDIT/DAST, CAGE, MDQ, HCL-32, C-SSRS, Columbia Protocol, WHODAS 2.0.

Exclude: full neuropsychological batteries, projective instrument manuals (Rorschach, TAT), structured diagnostic interview manuals (SCID, M.I.N.I.) — these are assessment tools requiring specialist training, not outcome monitoring.

**Relapse prevention and maintenance treatment literature**
Relevant primarily for patients approaching termination or showing signs of early relapse.

Examples:
- Marlatt & Gordon, *Relapse Prevention* (2nd ed.)
- Segal, Williams & Teasdale, *Mindfulness-Based Cognitive Therapy for Depression* (relapse prevention framework)
- Fava et al. — continuation and maintenance phase literature
- Well-being therapy approaches — Fava

---

## Documents to Exclude from the ASA Corpus

### Category 1 — Pure Pharmacology and Prescribing References

The same rationale as in the RTA corpus, with slightly different framing: the after-session clinician can consider medication augmentation *in general terms*, but should not be surfacing dosing tables, titration schedules, receptor pharmacology, or drug-drug interaction databases — these are for prescribers, and surfacing them creates both liability and retrieval noise.

Exclude specifically:
- Stahl's *Essential Psychopharmacology* and the *Prescriber's Guide*
- Schatzberg & Nemeroff, *Textbook of Psychopharmacology*
- Any pharmacokinetic/pharmacodynamic reference or drug monograph collection
- Specific dosing guidelines and prescribing algorithms

**What is acceptable**: brief narrative overviews of drug classes as contextual background within psychotherapy-focused texts (e.g., "SSRIs are commonly co-prescribed with PE; therapists should understand that..."). The source document must be a psychotherapy text, not a pharmacology text.

### Category 2 — Basic Science and Preclinical Research

Animal models, in-vitro studies, molecular biology of psychiatric disorders, genetic association studies, and biomarker research. These are too many translational steps removed from clinical decision-making even in the reflective post-session mode.

**Exception**: review articles that explicitly bridge from basic science to clinical application, written for clinician audiences (e.g., a review in *Journal of Clinical Psychology* summarizing what genetic research implies for treatment selection). The target audience must be clinician, not researcher.

### Category 3 — Epidemiology and Burden-of-Disease Data (Standalone)

Prevalence statistics, incidence rates, disability-adjusted life years, and health economics data remain unhelpful even after session. The clinician is managing a specific patient, not a population.

**Exception**: epidemiological findings that are embedded within a treatment-recommendation context — e.g., "given that 60% of patients with chronic PTSD develop comorbid MDD, structured screening for depression is recommended at 8-week reassessment." The recommendation must be the primary content; the statistic is supporting evidence.

### Category 4 — Administrative, Legal, and Regulatory Documents

HIPAA compliance guides, billing and coding references, licensing board ethics codes, malpractice case summaries, insurance prior authorization protocols. These belong in a compliance system, not a clinical guidance corpus.

**Exception**: clinical-decision-relevant ethics content (duty to warn analysis, informed consent standards for specific clinical situations, documentation obligations following suicidality) is acceptable and already flagged for inclusion under risk management above.

### Category 5 — Self-Help Books Without Clinical Framework

Consumer-facing mental health books that do not contain the clinical decision-making structure needed for the therapist perspective. These describe the patient experience rather than the clinician's reasoning.

**Exception**: patient-facing workbooks that are the companion piece to a specific treatment manual (PE patient workbook, CPT patient manual, DBT self-help skills workbook) are included in Tier 1 as homework resources, tagged `target_audience: patient`. The distinguishing criterion is whether the book is part of an evidence-based treatment package that a trained clinician supervises.

### Category 6 — General Psychiatric Textbooks (Non-Psychotherapy Sections)

Same exclusion as RTA. Kaplan & Sadock, *Comprehensive Textbook of Psychiatry*, and similar reference texts contain extensive pharmacotherapy, biological treatments, and diagnostic nosology that crowded the RTA corpus. Psychotherapy sections in these texts are typically brief and superseded by dedicated sources already in the corpus.

---

## Summary Decision Matrix

| Document type | RTA corpus | ASA corpus | Notes |
|---|---|---|---|
| Evidence-based treatment manual (therapist edition) | Yes | Yes | Core to both |
| Session transcript with clinical annotation | Yes | Yes | Session autopsy anchor |
| Deliberate practice / therapist training text | Yes | Yes | Both autopsy and planning |
| Rupture/repair and alliance literature | Yes | Yes | Both modes |
| Crisis intervention protocol | Yes | Yes | Risk documentation |
| Clinical practice guidelines (psychotherapy sections) | Yes | Yes | |
| RCTs with modality and moderator data | No | **Yes** | Key ASA addition |
| Meta-analyses / systematic reviews (aggregate) | Selective | **Yes** | Full inclusion in ASA |
| Treatment matching / prescriptive therapy | No | **Yes** | Longitudinal planning |
| Outcome monitoring instruments and literature | No | **Yes** | Between-session tracking |
| Patient-facing homework and worksheets | No | **Yes** | Homework assignment only |
| Prognosis / course-of-illness research | No | **Yes** | Long-term planning |
| Comorbidity management literature | Selective | **Yes** | Treatment sequencing |
| Level-of-care and referral frameworks | No | **Yes** | Escalation guidance |
| Medication coordination (conceptual level) | No | **Yes** | Prescriber communication |
| Cultural competency and diversity texts | No | **Yes** | Longitudinal framing |
| Group therapy and adjunctive formats | No | **Yes** | Adjunctive recommendations |
| Translational neuroscience (clinician-facing) | No | Selective | Must be clinician-translated |
| Qualitative process research | No | Selective | High quality only |
| Psychometric instrument manuals | No | Selective | Outcome monitoring only |
| Relapse prevention texts | Selective | **Yes** | Late-treatment and maintenance |
| Psychiatric pharmacology textbooks | No | No | Out of therapeutic scope |
| Basic science / preclinical research | No | No | Too many translational steps |
| Epidemiology / burden-of-disease (standalone) | No | No | Population ≠ individual patient |
| Neuroimaging / fMRI studies | No | No | Abstraction gap |
| General psychiatric textbooks | No | No | Superseded by focused sources |
| Administrative / regulatory documents | No | No | Wrong system |
| Consumer self-help (without clinical frame) | No | No | Wrong audience |

---

# Recommended Metadata Schema for ASA Corpus Ingestion

## Relationship to the RTA Schema

The ASA schema **extends** the RTA schema — all fields recommended in `CORPUS_NOTES_RTA.md` are retained, with the following modifications and additions. If both corpora share a single Vertex AI Search DataStore, the union of both schemas applies to all documents, and retrieval queries use `corpus_scope` as a hard filter to separate real-time from post-session retrieval.

If the corpora are maintained as separate DataStores, apply the full combined schema to the ASA DataStore and the RTA-only schema to the RTA DataStore.

## Fields to Retain from the RTA Schema (Unchanged)

All required fields: `doc_id`, `source_file`, `title`, `chapter`, `page_start`, `page_end`, `chunk_index`, `year_published`

All controlled-vocabulary fields: `domain`, `subdomain`, `doc_type` (see additions below), `therapeutic_modality`, `clinical_presentation`, `session_event_tags`, `session_phase`, `target_audience`, `technique_tags`, `keywords`

`practice_recommendation_level` — retain and extend with an additional value: `empirically_derived` for RCT-sourced findings that reach the ASA corpus but would not have been admitted to the RTA corpus.

## New Fields for ASA

**`corpus_scope`** (string, controlled vocabulary) — **the most important new field**
Routes documents to the correct retrieval pipeline. Documents tagged `rta_and_asa` are retrieved by both systems; `asa_only` documents are excluded from real-time retrieval.

```
rta_and_asa          (default for all RTA Tier 1/2 documents)
asa_only             (RCTs, meta-analyses, homework, assessment instruments, prognosis literature)
```

This field is the hard filter applied at query time. The searcher in the ASA pipeline lifts the `asa_only` exclusion; the RTA searcher keeps it in force. No other schema change is needed to support dual-corpus operation.

**`analysis_function`** (array of strings, controlled vocabulary)
Which post-session analysis function(s) this chunk primarily serves. ASA queries are routed by function (session autopsy vs. longitudinal planning) before modality and presentation filters are applied.

```
session_autopsy          (retrospective event identification and response evaluation)
case_formulation_update  (integrating session data into the evolving case conceptualization)
treatment_plan_revision  (adjusting modality, pacing, goals, or sequence)
homework_resource        (therapist-side retrieval of between-session materials to assign)
outcome_monitoring       (interpreting outcome scores or tracking trajectory)
risk_documentation       (post-session safety plan review, duty-to-warn reasoning, level-of-care)
referral_coordination    (adjunctive service recommendations, prescriber communication)
prognosis_trajectory     (expected course-of-illness, relapse risk, maintenance planning)
supervision_preparation  (framing the session for supervisor review)
```

# RECOMMENDED CHANGE
The `analysis_function` enum is missing a value for termination planning. The termination phase generates a distinct post-session analysis task that is not covered by `prognosis_trajectory` (expected illness course) or `treatment_plan_revision` (assumes ongoing treatment): reviewing client progress against stated goals, managing termination-related affect, and producing a formal termination summary.

```
termination_planning     (reviewing treatment progress, managing ending-phase affect, producing
                          termination summary, planning for maintenance and relapse prevention)
```
# END RECOMMENDED CHANGE

**`evidence_base`** (string, controlled vocabulary)
Characterizes the type of evidence the chunk represents. Distinct from `practice_recommendation_level` (which rates strength of recommendation) — this field rates the epistemological type of the source.

```
rct_primary              (chunk from an RCT paper)
rct_moderator            (chunk reporting moderator/mediator analysis from an RCT)
meta_analytic            (chunk from a meta-analysis or systematic review)
qualitative_research     (chunk from a qualitative study)
case_series              (multiple case reports analyzed together)
single_case              (single case report or intensive single-case study)
expert_clinical          (clinical expert opinion, consensus statement)
theoretical              (theoretical model, not empirically tested)
instrument_normative     (assessment instrument norms, administration data)
not_applicable           (procedural content: manuals, transcripts, worksheets)
```

**`patient_population`** (array of strings, controlled vocabulary)
The population for whom the evidence or recommendation applies. Critical for treatment matching — an RCT conducted entirely in veteran populations with military PTSD should not be retrieved as equally relevant to a community sample with childhood PTSD.

```
adult_general
adult_older              (age 60+)
adolescent               (age 12–17)
child                    (age 6–11)
veteran_military
first_responder
perinatal
lgbtq
bipoc                    (broad racial/ethnic minority designation; specify in subdomain)
low_income
chronic_medical_illness
severe_mental_illness    (SMI: psychosis, treatment-resistant mood)
forensic
cross_cultural           (non-Western or non-North-American sample)
not_specified
```

**`time_horizon`** (string, controlled vocabulary)
The temporal scope of the chunk's clinical relevance — useful for routing the longitudinal management queries.

```
single_session           (relevant to what happens within one session)
near_term                (next 1–4 sessions; adjustments to immediate treatment conduct)
short_term               (1–3 months; goal revision, modality augmentation decisions)
treatment_course         (full treatment arc; sequencing, format, phasing decisions)
post_termination         (maintenance, relapse prevention, booster sessions)
any
```

# RECOMMENDED CHANGE
The `time_horizon` enum implicitly assumes time-limited treatment. Many clients are in open-ended therapy (psychodynamic, relational, long-term supportive) where `treatment_course` does not accurately describe a case that has been ongoing for two or three years with no defined endpoint.

```
open_ended               (no defined treatment arc or termination target; applies to long-term
                          dynamic, relational, or supportive therapy contexts)
```
# END RECOMMENDED CHANGE

**`outcome_measure_tags`** (array of strings, controlled vocabulary)
For chunks containing data from or about specific outcome instruments. Allows the outcome monitoring analysis function to retrieve interpretation guidance for the specific instrument in use.

```
PHQ-9, GAD-7, PCL-5, BDI-II, DASS-21, HAM-D, MADRS, BAI, SPIN,
ORS, SRS, PCOMS, C-SSRS, Columbia, AUDIT, DAST, MDQ, HCL-32,
WHODAS, SF-36, WHOQOL, OQ-45, CORE-OM, IES-R, DES, EDE-Q, other
```

## Extended `doc_type` Values (Additions to RTA Enum)

Add the following to the `doc_type` controlled vocabulary:

```
rct_paper                (randomized controlled trial report)
meta_analysis            (systematic review or meta-analysis)
outcome_instrument       (psychometric instrument manual or scoring guide)
homework_worksheet       (patient-facing structured exercise for between-session use)
psychoeducation_material (patient-facing educational content within a treatment package)
progress_note_template   (clinical documentation guide or note template)
```

## Full ASA-Extended Schema (Additions Only; Union with RTA Schema)

```json
{
  "corpus_scope": {
    "type": "string",
    "enum": ["rta_and_asa", "asa_only"],
    "description": "Hard retrieval filter. asa_only chunks are excluded from real-time retrieval.",
    "default": "rta_and_asa"
  },
  "analysis_function": {
    "type": "array",
    "items": {
      "type": "string",
      "enum": [
        "session_autopsy", "case_formulation_update", "treatment_plan_revision",
        "homework_resource", "outcome_monitoring", "risk_documentation",
        "referral_coordination", "prognosis_trajectory", "supervision_preparation"
      ]
    },
    "description": "Post-session analysis function(s) this chunk serves. Primary ASA retrieval routing field.",
    "default": []
  },
  "evidence_base": {
    "type": "string",
    "enum": [
      "rct_primary", "rct_moderator", "meta_analytic", "qualitative_research",
      "case_series", "single_case", "expert_clinical", "theoretical",
      "instrument_normative", "not_applicable"
    ],
    "description": "Epistemological type of the evidence in the chunk.",
    "default": "not_applicable"
  },
  "patient_population": {
    "type": "array",
    "items": {
      "type": "string",
      "enum": [
        "adult_general", "adult_older", "adolescent", "child",
        "veteran_military", "first_responder", "perinatal", "lgbtq",
        "bipoc", "low_income", "chronic_medical_illness",
        "severe_mental_illness", "forensic", "cross_cultural", "not_specified"
      ]
    },
    "description": "Population for whom this chunk's evidence or recommendation applies. Used for treatment matching.",
    "default": ["not_specified"]
  },
  "time_horizon": {
    "type": "string",
    "enum": [
      "single_session", "near_term", "short_term", "treatment_course", "post_termination", "any"
    ],
    "description": "Temporal scope of the chunk's clinical relevance for longitudinal management queries.",
    "default": "any"
  },
  "outcome_measure_tags": {
    "type": "array",
    "items": { "type": "string" },
    "description": "Outcome instruments referenced or normed in the chunk. Enables routing to specific instrument guidance.",
    "default": []
  }
}
```

## Implementation Notes

1. **`corpus_scope` is the single most important new field for system safety.** If both corpora share a DataStore, the RTA searcher must apply `corpus_scope != "asa_only"` as a mandatory pre-filter on every query. This is a correctness requirement, not a ranking signal — a homework worksheet retrieved mid-session is not merely unhelpful, it breaks the real-time latency contract and may confuse the clinician.

2. **`analysis_function` enables multi-hop ASA retrieval.** The ASA pipeline can issue a sequence of targeted retrievals: first `analysis_function = session_autopsy` to name the session's events, then `analysis_function = treatment_plan_revision` with the identified clinical state as query context, then `analysis_function = homework_resource` to retrieve tailored between-session assignments. Structure the pipeline around these functions as query types.

3. **`evidence_base` and `patient_population` are the joint moderator for RCT retrieval.** When the ASA system is answering a treatment-matching question, it should filter `evidence_base IN [rct_primary, rct_moderator, meta_analytic]` and rank by `patient_population` overlap with the current patient's profile. This prevents an adult veteran PTSD RCT from being weighted equally with a civilian adolescent sample for a 16-year-old patient.

4. **`outcome_measure_tags` should use the exact instrument acronym as the controlled value.** Gemini extraction will produce variants ("Patient Health Questionnaire-9", "PHQ9", "PHQ 9") — normalize to the canonical abbreviation in the `_fallback_extraction()` path.

5. **Homework and patient-facing materials require a two-step retrieval gate.** First retrieve by `analysis_function = homework_resource` AND `clinical_presentation` match AND `therapeutic_modality` match. Then apply a secondary filter: `target_audience = patient`. Never surface `target_audience = patient` documents in any RTA query path or any ASA query path where `analysis_function` is not `homework_resource`.

6. **The `practice_recommendation_level` field needs `empirically_derived` added to its enum** before ASA schema registration. RCT-sourced chunks cannot accurately be tagged as `strongly_recommended` (a guideline designation) or `expert_consensus` (a non-empirical designation) — `empirically_derived` captures findings that are data-supported but not yet synthesized into a clinical practice recommendation.

7. **ASA Gemini extraction prompts require separate prompt design from RTA.** The RTA extraction prompt asks Gemini to identify session events and clinical techniques in a chunk. The ASA extraction prompt must additionally elicit `evidence_base`, `patient_population`, `analysis_function`, and `time_horizon`. These require Gemini to reason about the epistemological type of the source (is this from an RCT? What population?), which benefits from including the document's abstract or first few pages as context alongside the chunk.

# RECOMMENDED CHANGE
8. **Risk monitoring in the ASA pipeline should not rely solely on `risk_documentation` as an `analysis_function`.** That value covers acute post-session risk documentation (safety plan updates, duty-to-warn reasoning). It does not cover the clinician's ongoing background task of tracking chronic suicide ideation, NSSI patterns, or relapse risk trajectories across sessions. The ASA system should run a second retrieval pass keyed on `risk_dimension_tags` (proposed in CORPUS_NOTES_RTA.md) for every session — not only those flagged with acute risk events — to surface trajectory-monitoring guidance as a lower-priority output alongside the primary session analysis.

9. **The `practice_recommendation_level` enum (inherited from RTA) needs negative polarity values in the ASA context as well.** Post-session analysis synthesizes RCT and meta-analytic evidence, which includes explicit "do not use" findings (e.g., "EMDR without prior stabilization worsened outcomes in this complex PTSD subgroup"). The existing enum has no way to represent this. Add `use_with_caution` and `contraindicated` consistent with the RTA recommendation.
# END RECOMMENDED CHANGE
