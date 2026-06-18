This corpus body is designed to incorporate into a RAG assistance/analysis tool that monitors a clinician-patient therapy session and provides real time feedback and suggestions. This tool will span across common psychotherapeutic modalities (e.g. CBT, CBT-I, ERP, DBT, CPT, PE, ACT, IPT, PDT, ...) and across common clinical presentations (e.g. Depression/Bipolar, Anxiety/Panic/Phobias, Trauma/PTSD, BPD, OCD, Grief & Bereavement, Relationship & Family Conflicts, Chronic Pain, Medical Stress, SUD/SUDs, Impulse control, ...)

Beyond these treatment and presentation tags, the analysis should handle various events that can occur during a psychotherapy session (e.g. therapeutic rupture, transference enactment, unanticipated/doorknob disclosures, "new" historical disclousre, sudden clinical escalation/crisis, decompensation/micro-dissociation, sudden flight into health, boundary testing, sudden resistance / intellectualization), (see https://pmc.ncbi.nlm.nih.gov/articles/PMC12401482/)

---

# Corpus Curation Guide

## Governing Principle

The RAG system answers a single operational question in near real-time: **"Given what is happening right now in this therapy session, what does the clinical literature say a skilled therapist should do or consider?"** Every curation decision flows from this constraint. A document earns its place not by being authoritative or prestigious, but by providing **actionable, in-session procedural guidance** that can be retrieved, chunked at 512 tokens, and acted upon within the timeframe of a clinical exchange.

---

## Documents to Include ("Good Corpus")

### Tier 1 — Core (Highest retrieval value)

**Evidence-based treatment manuals (therapist editions)**
These are the primary source of procedural knowledge. They describe exactly what a therapist does, when, and why — at session-by-session and sometimes moment-by-moment resolution. Therapist editions are preferred over patient workbooks because they contain clinical rationale, troubleshooting guidance, and common obstacles.

Examples:
- Foa et al., *Prolonged Exposure Therapy for PTSD* (therapist guide, Oxford) — already in corpus
- Resick et al., *Cognitive Processing Therapy for PTSD* (Guilford)
- Linehan, *DBT Skills Training Manual* (Guilford) — clinician's edition
- Clark & Wells or Hofmann & Otto, *Cognitive Behavioral Therapy for Social Anxiety Disorder*
- Hayes, Strosahl & Wilson, *Acceptance and Commitment Therapy* (practitioner's guide)
- Barlow et al., *Unified Protocol for Transdiagnostic Treatment of Emotional Disorders* (therapist guide)
- Klerman et al., *Interpersonal Psychotherapy of Depression* (IPT manual)
- Barkley, *Defiant Children: A Clinician's Manual* (for pediatric/ADHD presentations)
- Jobes, *Managing Suicidal Risk: A Collaborative Approach* (CAMS)
- Miller & Rollnick, *Motivational Interviewing* (3rd ed., Guilford)

**Deliberate practice and therapist-competency texts**
Books explicitly structured around developing clinical skill — often include annotated session vignettes, supervisor commentary, and criteria for recognizing skill gaps. These index cleanly to session events.

Examples:
- Boswell & Constantino, *Deliberate Practice in Cognitive Behavioral Therapy* (APA) — already in corpus
- Chow, *Better Results: Using Deliberate Practice to Improve Therapeutic Effectiveness*
- Eubanks, Muran & Safran, *Alliance-Focused Training*

**Annotated session transcripts and clinical case books**
Verbatim or near-verbatim session excerpts with expert clinical commentary are uniquely valuable: they provide both the raw speech pattern and the supervisor-level interpretation. The ratio of transcript to commentary is a quality signal — pure transcripts without commentary are less useful than annotated ones.

Examples:
- Yalom, *The Gift of Therapy* (process-focused vignettes)
- McWilliams, *Psychoanalytic Case Formulation* (case reasoning)
- Binder, *Key Competencies in Brief Dynamic Psychotherapy*
- Safran & Muran, *Negotiating the Therapeutic Alliance* (rupture/repair transcripts)
- Greenberg & Goldman (eds.), *Case Studies in Emotion-Focused Therapy*
- Linehan, *Cognitive-Behavioral Treatment of Borderline Personality Disorder* — Chapter-level case material
- Any APA *Psychotherapy in 6 Sessions* video companion texts (contain annotated transcripts)

**Alliance rupture and repair-focused texts**
The system must recognize and respond to rupture events (withdrawal, confrontation) in real-time. This is a specialized area with its own clinical literature.

Examples:
- Safran & Muran, *A Relational Approach to Psychotherapy* (older but foundational)
- Eubanks, Muran & Safran (2018 meta-analysis chapter in *APA Handbook of Psychotherapy*)
- Norcross & Wampold, *Psychotherapy Relationships That Work* (APA, 3rd ed.) — especially alliance, rupture, and repair chapters

**Crisis intervention and clinical escalation guides**
The system must flag sudden escalation and retrieve actionable protocol steps (safety planning, lethality assessment, hospitalization criteria) within seconds.

Examples:
- Roberts (ed.), *Crisis Intervention Handbook* (Oxford)
- Stanley & Brown, *Safety Planning Intervention* (SPI) training materials
- Jobes, *Managing Suicidal Risk* (CAMS framework)
- Rudd et al., *Brief Cognitive Behavioral Therapy for Suicide Prevention*

**Emotion-focused and process-experiential texts**
EFT and process-experiential approaches contain detailed in-session marker-task maps (e.g., "when you observe X marker, use Y task") that are directly retrievable.

Examples:
- Greenberg, *Emotion-Focused Therapy* (APA)
- Elliott, Watson, Goldman & Greenberg, *Learning Emotion-Focused Therapy* (APA)
- Paivio & Pascual-Leone, *Emotion-Focused Therapy for Complex Trauma*

**Case formulation and clinical reasoning texts**
These provide the cognitive scaffolding for understanding *why* a patient is doing what they are doing — essential for contextualizing in-session events against the broader case.

Examples:
- Persons, *The Case Formulation Approach to Cognitive-Behavior Therapy* (Guilford)
- McWilliams, *Psychoanalytic Diagnosis* (2nd ed.) — character structure and defenses
- Eells (ed.), *Handbook of Psychotherapy Case Formulation* (Guilford)
- Kuyken, Padesky & Dudley, *Collaborative Case Conceptualization* (Guilford)

### Tier 2 — Supplementary (Moderate retrieval value)

**Clinical practice guidelines (psychotherapy-relevant sections only)**
APA Clinical Practice Guidelines, NICE guidelines (UK), and SAMHSA Treatment Improvement Protocols (TIPs) contain evidence-based recommendations at the session-component level. The procedural sections are useful; introductory epidemiology and cost-effectiveness sections are not.

- APA Clinical Practice Guideline for PTSD (2017)
- APA Guidelines for Psychological Practice with Transgender and Gender Nonconforming People
- NICE CG91 (Depression with Chronic Physical Health Problem)
- SAMHSA TIP 57 (Trauma-Informed Care in Behavioral Health Services)

**Psychopathology texts with explicit treatment implications**
Texts that describe clinical presentations in a way that directly informs treatment response — not pure diagnosis references. The criterion is whether a chunk from this text would help a therapist respond to something happening in session.

Examples:
- Clarkin, Fonagy & Gabbard (eds.), *Psychodynamic Psychotherapy for Personality Disorders*
- Linehan, *Cognitive-Behavioral Treatment of Borderline Personality Disorder* (the 1993 theory sections)
- Herman, *Trauma and Recovery* — conceptual framework for complex PTSD presentations

**Transference, countertransference, and relational process**
Explicitly relevant to the transference-enactment and countertransference session-event tags.

Examples:
- Ogden, *The Analyst's Ear and the Critic's Eye* — countertransference listening
- Aron, *A Meeting of Minds* — relational psychoanalysis process
- Hayes, Gelso & Hummel (2011), "Managing countertransference" (APA review chapter)

**Clinical supervision manuals**
Supervision texts contain session-by-session commentary on what went right, what went wrong, and how to redirect — directly analogous to the tool's function.

Examples:
- Falender & Shafranske, *Clinical Supervision: A Competency-Based Approach* (APA)
- Watkins & Milne (eds.), *Wiley International Handbook of Clinical Supervision*

### Tier 3 — Selective inclusion (Narrow retrieval value; curate carefully)

**Meta-analyses and systematic reviews** — Include *only* those that synthesize technique-level findings (e.g., "which specific DBT skills components most predict BPD outcomes") rather than aggregate effect sizes. Use the abstract and discussion sections; skip Methods and Results tables. Tag `doc_type: review_article` and exclude from certain retrieval filters.

**High-quality qualitative process research** — Studies using tape-assisted recall, sequential process coding (e.g., SASB, CCRT), or intensive single-case designs that directly describe session-level events. These are rare but valuable.

---

## Documents to Exclude ("Bad Corpus")

### Category 1 — Randomized Controlled Trials (primary efficacy data)

**Why excluded:** RCTs answer "Does Treatment A outperform Treatment B?" They provide aggregate outcome statistics (effect sizes, response rates, NNT) but contain no guidance on *how* to conduct the treatment or respond to in-session events. A chunk from an RCT retrieved mid-session would say "the HAMD-17 score decreased by 6.2 points (95% CI: 4.1–8.3)" — useless to a clinician managing a patient's crisis disclosure right now.

Structural markers that identify an RCT to exclude:
- CONSORT flow diagram
- Sections titled "Randomization," "Blinding," "Power calculation," "ITT analysis"
- Primary outcome measured in weeks/months post-treatment
- No technique-level procedural content

**Partial exception:** The *Discussion* section of an RCT that explains *which protocol components predicted outcomes* can be useful. If selectively ingesting RCTs, exclude everything through Results and ingest Discussion only — and only when it contains mechanism or technique-level insight.

### Category 2 — Psychiatric pharmacology textbooks

**Why excluded:** Psychopharmacology (drug mechanisms, receptor pharmacology, dosing tables, drug-drug interactions, prescribing guidelines) is entirely outside the therapeutic frame. The therapist cannot and should not alter medication mid-session. Pharmacology content that leaks into retrieval creates two active harms: it clutters the retrieved passages with irrelevant content, and it risks the system surfacing medication-adjacent suggestions that are out of scope for a non-prescriber.

Exclude specifically:
- Stahl's *Essential Psychopharmacology* and its Prescriber's Guide
- Schatzberg & Nemeroff, *The American Psychiatric Association Publishing Textbook of Psychopharmacology*
- Any PK/PD reference, drug monograph collection, or pharmacotherapy algorithm

**Narrow exception:** A brief psychoeducation-level summary of a medication class *as it appears in a therapy manual* (e.g., "patients are often prescribed SSRIs alongside CBT for OCD; the therapist should understand that...") is acceptable if it is contained within an otherwise good-corpus document. Do not ingest standalone pharmacology references.

### Category 3 — Epidemiology, prevalence studies, and burden-of-disease reports

**Why excluded:** "12-month prevalence of MDD is 7.2% in US adults" has no actionable value in session. These documents populate the corpus with statistically dense, procedurally empty chunks that waste retrieval bandwidth and dilute signal.

Includes: NIMH statistics pages, WHO global mental health reports, GBD (Global Burden of Disease) mental health chapters, SAMHSA annual survey data.

### Category 4 — Neuroscience and neuroimaging research

**Why excluded:** fMRI studies of amygdala reactivity in PTSD, neural correlates of rumination, default-mode network connectivity in depression — none of this translates to session-moment guidance. The level of abstraction (neural circuit → behavioral phenotype → in-session event) is too large for the current system to bridge.

**Narrow exception:** Clinician-facing neuroscience education *when it is explicitly embedded in a treatment manual* as psychoeducation content (e.g., the "hand model of the brain" as described in a trauma manual) is acceptable because it appears in an otherwise high-value document and is already at the appropriate level of abstraction.

### Category 5 — General psychiatric textbooks (non-psychotherapy sections)

**Why excluded:** Comprehensive psychiatry references (Kaplan & Sadock, Stahl's case files, the *DSM-5 Handbook of Differential Diagnosis*) contain diagnostic criteria, biological etiologies, medical comorbidities, and pharmacotherapy — all outside scope. Psychotherapy-relevant sections within these texts (if any) are typically brief, superficial, and redundant with better sources.

**Note on DSM-5:** The raw DSM-5 diagnostic criteria text is a borderline case. It is not useful for in-session guidance (a therapist does not retrieve diagnostic criteria mid-session), but clinically contextualized descriptions of presentations (differential diagnosis reasoning, cultural considerations) *in a therapy manual that cites DSM* are fine.

### Category 6 — Psychometric and assessment instrument manuals

**Why excluded:** PHQ-9 scoring guides, MMPI-3 administration manuals, Rorschach scoring systems, structured diagnostic interview manuals (SCID, M.I.N.I.) — these support assessment, not session process. A therapist monitoring the session in real-time is not administering tests; they are conducting therapy.

**Exception:** Outcome monitoring instruments that are explicitly integrated into session process (e.g., the ORS/SRS used in Partners for Change Outcome Management System, the YOQ in youth treatment) may be included when their use is described within a treatment manual as part of session structure.

### Category 7 — Administrative, regulatory, and ethics documents

**Why excluded:** HIPAA compliance guides, billing and coding references, licensing board ethics codes — these belong in an HR/compliance system, not a clinical guidance corpus.

**Exception:** Ethics content that specifically addresses within-session clinical decision-making — e.g., "duty to warn" decision frameworks, documentation obligations after a suicide risk assessment — may be useful in a crisis-event context. Include selectively and tag `session_event_tags: ["crisis_escalation"]`.

### Category 8 — Consumer/patient-facing psychoeducation

**Why excluded:** Self-help books, patient workbooks, and lay-audience mental health guides are written *for* patients, not *about* how to conduct therapy. They describe the patient experience, not the therapist's decision process. Including them would confuse the retrieval system about its target audience.

The distinction from the patient side of treatment manuals: a Linehan DBT Skills Workbook (patient edition) is excluded; the corresponding DBT Skills Training Manual (therapist edition) is included.

---

## Summary Decision Matrix

| Document type | Include? | Notes |
|---|---|---|
| Evidence-based treatment manual (therapist edition) | **Yes** | Tier 1 core |
| Session transcript with clinical annotation | **Yes** | Tier 1 core |
| Deliberate practice / therapist training text | **Yes** | Tier 1 core |
| Alliance, rupture/repair focused text | **Yes** | Tier 1 core |
| Crisis intervention protocol | **Yes** | Tier 1 core |
| Clinical practice guideline (psychotherapy sections) | **Yes** | Tier 2; exclude epidemiology intro |
| Psychopathology text with treatment implications | **Yes** | Tier 2; case-by-case |
| Clinical supervision manual | **Yes** | Tier 2 |
| Meta-analysis / systematic review | **Selective** | Tier 3; technique-level findings only |
| Patient workbook / self-help | **No** | Wrong audience |
| Randomized controlled trial | **No** | No in-session guidance |
| Psychiatric pharmacology textbook | **No** | Out of therapeutic scope |
| Epidemiology / prevalence report | **No** | No actionable content |
| Neuroimaging / neuroscience study | **No** | Abstraction gap too large |
| General psychiatric textbook | **No** | Superseded by focused sources |
| Psychometric / assessment manual | **No** | Assessment ≠ therapy process |
| Administrative / regulatory document | **No** | Wrong system |

---

# Recommended Metadata Schema for Psychotherapy Corpus Ingestion

The current `config/metadata_schema.json` was designed for a general biomedical corpus (cardiology, oncology, pharmacology). The psychotherapy use case has a fundamentally different retrieval profile: queries are event-driven (triggered by something happening in session), audience-specific (the clinician, not the patient), and modality-filtered (a DBT-trained therapist needs DBT guidance, not generic CBT). The schema must be rebuilt around these retrieval axes.

## Fields to Retain (Unchanged)

| Field | Rationale |
|---|---|
| `doc_id` | Required; content hash for deduplication |
| `source_file` | Required; provenance |
| `title` | Document/chapter title; useful for ranking and display |
| `chapter` | Section heading; treatment manuals have numbered sessions ("Session 4: In Vivo Exposure") that are the primary navigation unit |
| `page_start`, `page_end` | Required; citation path |
| `chunk_index` | Required; pipeline invariant |
| `keywords` | Gemini-extracted terms; retain as free-text signal |
| `year_published` | Psychotherapy evidence evolves; older editions of manuals may conflict with newer protocol revisions |

## Fields to Modify

**`domain`** — Replace the current general-biomedical enum with a psychotherapy-specific controlled vocabulary:

```
psychotherapy_general
cognitive_behavioral          (CBT and its first-order derivatives: BA, REBT, Schema Therapy)
dialectical_behavior          (DBT and its adaptations)
acceptance_commitment         (ACT, FAP, CFT)
trauma_focused                (PE, CPT, EMDR, TF-CBT, NET)
psychodynamic                 (PDT, relational, object relations, self psychology)
interpersonal                 (IPT, IPSRT)
emotion_focused               (EFT, AEDP, process-experiential)
motivational_interviewing     (MI, MINT)
mindfulness_based             (MBCT, MBSR, MBRP)
systemic_family               (structural, strategic, narrative, Gottman)
crisis_intervention           (CAMS, SPI, CBT-SP, ACT for suicide)
therapeutic_alliance          (rupture/repair process, common factors)
clinical_supervision          (supervisory process and training)
psychopathology_clinical      (diagnostic conceptualization with treatment implications)
other
```

**`doc_type`** — Expand to include psychotherapy-specific document classes:

```
treatment_manual              (protocol-specific therapist guides: PE, CPT, DBT, ACT manuals)
session_transcript            (verbatim or near-verbatim session material, annotated or raw)
case_formulation              (case conceptualization documents)
supervision_material          (supervision session content, training case discussions)
clinical_worksheet            (structured in-session tools: chain analysis, thought records, exposure hierarchies)
textbook                      (retain)
clinical_guideline            (retain: APA, NICE, SAMHSA guidelines)
review_article                (retain: meta-analyses, systematic reviews)
case_report                   (retain: single-case clinical reports)
front_matter                  (retain: excluded from search)
```

**`evidence_level`** — The GRADE framework (A/B/C/D) is designed for medical intervention recommendations and maps poorly onto psychotherapy guidance, where most high-quality evidence is from well-designed RCTs rated "B" but practitioner manuals contain no formal rating at all. Replace with:

```
practice_recommendation_level:
  strongly_recommended        (APA/NICE Grade A equivalent; RCT-supported)
  recommended                 (evidence-based but with caveats)
  expert_consensus            (clinical consensus, clinical practice guideline without full RCT base)
  theoretical_rationale       (theoretically grounded but limited empirical support)
  illustrative                (case example, vignette, or transcript; not a recommendation)
  not_applicable
```

## New Fields to Add

**`therapeutic_modality`** (array of strings, controlled vocabulary)
The therapy modality or modalities the chunk directly addresses. This is the primary filter for modality-specific queries — a therapist practicing PE does not want DBT skills content surfaced.

```
CBT, CBT-I, BA, REBT, Schema, DBT, ACT, CFT, FAP, CPT, PE, EMDR, TF-CBT, NET,
IPT, IPSRT, PDT, relational, object_relations, EFT, AEDP, MI, MBCT, MBSR, MBRP,
IFS, ISTDP, Gottman, narrative, supportive, integrative
```

This is an array because some texts (e.g., Barlow's Unified Protocol) explicitly cut across modalities.

**`clinical_presentation`** (array of strings, controlled vocabulary)
Diagnostic presentations or clinical themes the chunk addresses. Aligns with the CORPUS_NOTES taxonomy.

```
depression, bipolar, anxiety_general, panic_disorder, social_anxiety, specific_phobia,
GAD, PTSD, complex_trauma, OCD, BPD, ADHD, SUD, eating_disorder, grief_bereavement,
chronic_pain, somatic, psychosis, narcissistic, antisocial, avoidant, dependent,
relationship_family, medical_stress, impulse_control, insomnia, other
```

**`session_event_tags`** (array of strings, controlled vocabulary)
The in-session event types that this chunk directly addresses. This is the retrieval trigger for the real-time system — when the session monitor detects a rupture, it filters retrieval on `session_event_tags contains "rupture"`. Align with the CORPUS_NOTES event taxonomy (see the PMC reference).

```
rupture_withdrawal           (patient becomes silent, disengaged, compliant-without-investment)
rupture_confrontation        (patient directly challenges or criticizes therapist)
rupture_repair               (steps for repairing after either rupture subtype)
transference_enactment       (patient relating to therapist as if a significant other)
countertransference          (therapist's emotional reaction requiring management)
doorknob_disclosure          (significant disclosure at session end)
historical_disclosure        (new trauma or event disclosure mid-session)
crisis_escalation            (suicidality, self-harm, homicidality emerging mid-session)
decompensation               (acute dysregulation, dissociation, panic in session)
flight_into_health           (premature symptom report, resistance through wellness)
resistance_avoidance         (behavioral and verbal avoidance of therapeutic work)
intellectualization          (cognitive distancing from affective material)
boundary_testing             (violations of frame: gifts, contact requests, session extension)
alliance_building            (explicit alliance-repair and strengthening interventions)
psychoeducation              (delivery of psychoeducation in session)
exposure_in_session          (imaginal or in-vivo exposure work occurring in session)
homework_review              (review of between-session work)
termination_process          (ending phase, goodbye, relapse prevention)
none                         (chunk is reference/background; not event-specific)
```

**`session_phase`** (string, controlled vocabulary)
Where in the arc of treatment this chunk applies. Useful for retrieval when the session monitor knows the patient's treatment stage.

```
assessment_intake
early_treatment              (sessions 1–4 for most manuals)
mid_treatment                (active intervention phase)
late_treatment               (consolidation, generalization)
termination
crisis                       (phase-agnostic acute response)
any                          (applies throughout treatment)
```

**`target_audience`** (string, controlled vocabulary)
Who the source document was written for. Critical for preventing patient-facing workbook content from being surfaced as clinical guidance.

```
therapist                    (clinician manual, supervision text, professional reference)
trainee                      (deliberate practice, training-focused material)
supervisor                   (supervision manuals, training program design)
patient                      (patient workbook, self-help; generally excluded — see curation guide)
general                      (lay audience)
```

**`technique_tags`** (array of strings, Gemini-extracted free text)
Named clinical techniques referenced in the chunk. Distinct from `keywords` in that these should be proper technique names rather than topic terms. 0–10 items recommended.

Examples: `"Socratic questioning"`, `"behavioral activation"`, `"imaginal exposure"`, `"chain analysis"`, `"TIPP skills"`, `"cognitive restructuring"`, `"EMDR bilateral stimulation"`, `"two-chair dialogue"`, `"motivational interviewing OARS"`

## Recommended Full Schema (Proposed Replacement)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "ChunkMetadata",
  "description": "Per-chunk metadata for psychotherapy RAG corpus ingestion into Vertex AI Search.",
  "type": "object",
  "required": ["doc_id", "source_file", "domain", "doc_type", "page_start", "page_end", "chunk_index"],
  "properties": {
    "doc_id":        { "type": "string", "description": "SHA-256 of source PDF bytes.", "pattern": "^[a-f0-9]{64}$" },
    "source_file":   { "type": "string", "description": "Basename of source PDF." },
    "title":         { "type": "string", "default": "" },
    "chapter":       { "type": "string", "description": "Nearest section/session heading above chunk.", "default": "" },
    "page_start":    { "type": "integer", "minimum": 1 },
    "page_end":      { "type": "integer", "minimum": 1 },
    "chunk_index":   { "type": "integer", "minimum": 0 },
    "year_published":{ "type": ["integer","null"], "minimum": 1900, "maximum": 2100, "default": null },

    "domain": {
      "type": "string",
      "enum": [
        "cognitive_behavioral","dialectical_behavior","acceptance_commitment",
        "trauma_focused","psychodynamic","interpersonal","emotion_focused",
        "motivational_interviewing","mindfulness_based","systemic_family",
        "crisis_intervention","therapeutic_alliance","clinical_supervision",
        "psychopathology_clinical","psychotherapy_general","other"
      ]
    },
    "subdomain": { "type": "string", "description": "Narrower topic within domain (e.g. 'schema therapy', 'EMDR phase 2'). Free text.", "default": "" },

    "doc_type": {
      "type": "string",
      "enum": [
        "treatment_manual","session_transcript","case_formulation",
        "supervision_material","clinical_worksheet","textbook",
        "clinical_guideline","review_article","case_report","front_matter"
      ]
    },

    "therapeutic_modality": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "CBT","CBT-I","BA","REBT","Schema","DBT","ACT","CFT","FAP",
          "CPT","PE","EMDR","TF-CBT","NET","IPT","IPSRT","PDT",
          "relational","object_relations","EFT","AEDP","MI","MBCT",
          "MBSR","MBRP","IFS","ISTDP","Gottman","narrative","supportive","integrative"
        ]
      },
      "description": "Therapy modalities the chunk directly addresses. Primary retrieval filter.",
      "default": []
    },

    "clinical_presentation": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "depression","bipolar","anxiety_general","panic_disorder","social_anxiety",
          "specific_phobia","GAD","PTSD","complex_trauma","OCD","BPD","ADHD",
          "SUD","eating_disorder","grief_bereavement","chronic_pain","somatic",
          "psychosis","narcissistic","antisocial","avoidant","dependent",
          "relationship_family","medical_stress","impulse_control","insomnia","other"
        ]
      },
      "description": "Clinical presentations or diagnostic themes the chunk addresses.",
      "default": []
    },

    "session_event_tags": {
      "type": "array",
      "items": {
        "type": "string",
        "enum": [
          "rupture_withdrawal","rupture_confrontation","rupture_repair",
          "transference_enactment","countertransference","doorknob_disclosure",
          "historical_disclosure","crisis_escalation","decompensation",
          "flight_into_health","resistance_avoidance","intellectualization",
          "boundary_testing","alliance_building","psychoeducation",
          "exposure_in_session","homework_review","termination_process","none"
        ]
      },
      "description": "In-session event types this chunk directly addresses. Primary real-time retrieval trigger.",
      "default": ["none"]
    },

    "session_phase": {
      "type": "string",
      "enum": ["assessment_intake","early_treatment","mid_treatment","late_treatment","termination","crisis","any"],
      "default": "any"
    },

    "target_audience": {
      "type": "string",
      "enum": ["therapist","trainee","supervisor","patient","general"],
      "description": "Intended audience of the source document. Chunks with target_audience=patient are excluded from clinical retrieval.",
      "default": "therapist"
    },

    "practice_recommendation_level": {
      "type": ["string","null"],
      "enum": ["strongly_recommended","recommended","expert_consensus","theoretical_rationale","illustrative","not_applicable",null],
      "description": "Strength of practice recommendation. Replaces general GRADE evidence_level for psychotherapy context.",
      "default": null
    },

    "technique_tags": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Named clinical techniques (e.g. 'chain analysis', 'imaginal exposure'). Gemini-extracted, free text. 0–10 items.",
      "default": []
    },

    "keywords": {
      "type": "array",
      "items": { "type": "string" },
      "description": "Key topic terms extracted by Gemini. 3–10 terms.",
      "default": []
    }
  },
  "additionalProperties": false
}
```

## Implementation Notes for Schema Migration

1. **Vertex AI Search re-registration is required.** The current schema is registered in the DataStore. Adopting this schema requires running `scripts/purge_datastore.py --confirm` followed by `scripts/setup_vertex_search.py` with the updated `config/metadata_schema.json`, then full re-ingestion.

2. **Array fields are not filterable by default in Vertex AI Search.** `therapeutic_modality`, `clinical_presentation`, `session_event_tags`, and `technique_tags` must be explicitly registered as filterable attributes (type `key` or `text`) in the DataStore schema if they are to be used in retrieval filters. Confirm this in `setup_vertex_search.py` before schema registration.

3. **Gemini extraction prompt must be updated.** The metadata generation prompt in `ingestion/metadata_gen.py` currently extracts against the old schema's field set. Update it to elicit the new fields — especially `session_event_tags`, `therapeutic_modality`, and `clinical_presentation`, which require the model to reason about session-level events and clinical taxonomy. Provide the enum lists directly in the prompt to constrain hallucination.

4. **`prompt_config.yaml` personas need a psychotherapy persona.** The current config has cardiology, oncology, pharmacology, neurology, internal_medicine, anatomy, physiology, and biochemistry — none of which map to the psychotherapy use case. Add a `psychotherapy` persona (and likely sub-personas by modality domain: `cognitive_behavioral`, `psychodynamic`, `trauma_focused`) to route queries appropriately.

5. **`domain` enum in `prompt_config.yaml` and `metadata_schema.json` must be kept in sync.** PromptBuilder selects persona by `domain` key — mismatches silently fall back to `default`.

6. **The `target_audience=patient` filter should be a hard retrieval exclusion**, not a soft ranking signal. Implement this as a pre-filter in the searcher rather than relying on the ranker to deprioritize it.


