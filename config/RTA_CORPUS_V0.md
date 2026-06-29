# Initial Rough (v0) of proposed Real Time Analysis (RTA) Corpus

Author: James Chen (Backend AI/LLM Architect)

## RE: Lack of Clinical SME in Generating this Document (Most Important!)

Except for Vikki's recommendations, our tiers, modality organization, searches were conducted agnostic to:

1. what occurs during a clinical session, including what is appropriate reasoning pre session vs. in session vs. after session.

2. the ability of these texts to span the breadth and depth of CBT, DBT and IPT care.

3. the availability of these texts to clinician-academics.

Because of this, we anticipate the majority, or all of this list will be changed as we clarify with your team both what the context should contain, when it should be retrieved, etc. We are reliant on your team to add/remove documents.

Instead, this list is simply used as an example organization and tier structure that we will be using to help determine our approach to corpus ingestion (see notes)

## RE: The Tier Structure.

We are utilizing a tiered structure to handle corpus, this allows our backend team to allocate the necessary time and budget to any document, with Tier 1 and Tier 2 documents being considered as documents necessary for a functioning RAG assistant, with differing anticiated budgets for tier 1 (70%) and tier 2 (20-30%). Tier 3 documents will be considered as additional documents for corpus ingestion if time is available.

### Tier 1 documents:

* Encompass the "Core Knowledge"/"Foundational Framework" of any large metadata domain (currently, we are using the modalities of CBT, DBT and IPT)
* Spans interventional techniques and presentations *across* any metadata domain.
* I.E. a comprehensive guide to CBT/DBT/IPT. Something you would recommend to a prospective clinician "buy/read this first".

Mechanistically, we differentiate these because we anticipate that ingestion of these will generate many metadata tags (discrete relevant sections), so we will spend >70% of our budget ensuring these are tagged and indexed correctly due to the value/breadth/complexity of the document.

Likely we would have only very few ( foundational ) tier 1 documents, possibly 1 or 2 texts per large metadata domain.

### Tier 2 documents:

* Encompass necessary "Supplemental Knowledge" for any large metadata domain.
* May have interventional techniques related to a specific sub-group of presentations.
* I.E. CBT for Anxiety. 
Something that you would recommend to a prospective clinician looking at a particular vignette to "buy/read this"

We anticipate less tag generation due to the specificity of the text, and will likely spend 20-30% of our budget on these documents. 

We can budget in more tier 2 documents, possibly around 3 to 5 that cover sub-groups within a large metadata domain, since their metadata and ingestion will be more straightforward due to reduced scope of the document

Of note, Tier 2 documents do not mean that the information contained within is of "lesser importance" than Tier 1, just that their reduced scope means that we anticipate the ingestion method will be easier due to the reduced scope.

### Tier 3 documents:

* Encompass highly specialized knowledge within a large metadata domain that may be outside the knowledge scope of a practitioner.
* May provide answers to a very specific set of individual problems.

We may briefly review these documents and their ingestion, but may move to the after session analysis or drop entirely.

## RE: Culturally Responsive Care

I am treating Vikki as SME for corpus/schema for this section of the corpus. She has recommended two books --

1. CA-CBT for Black Populations: A Manual for Mental Health Practitioners (CAMH, 2024)

2. Cultural Adaptations of Evidence-Based Interventions for Latinx Populations (National Hispanic and Latino MHTTC, 2022)

And has additional schema notes for these. Since she is spearheading this in both theory and schema implementation, they will be essentially Tier 1 documents.

---

# TIER 1 Recommendations

## Therapeutic Modalities
### All Modality Reference
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---| 
| 1 | APA Handbook of Psychiatry | Tier 1 | Chapters across modalities, presentations and interventional events | ~$400

### CBT + sub-domains (PE, DBT, ACT)
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Boswell & Constantino, *Deliberate Practice in CBT* (APA)| Tier 1 | Therapist skill refinement; annotated technique gaps; deliberate practice protocols |  ✓ IN  |
| 2 | Linehan, *DBT Skills Training Manual* (2nd ed., Guilford) — Clinician's Edition | Tier 1 | Core DBT skills procedures: chain analysis, diary card review, distress tolerance, emotion regulation | ~$80–100 |
| 3 | Hayes, Strosahl & Wilson, *Acceptance and Commitment Therapy* — Practitioner's Guide | Tier 1 | Core ACT procedures; defusion, values work, committed action in session | ~$70–90 |
| 4 | *Thousand Voices of Trauma* - Annotated Texts | Tier 1 | CBT? Session Transcripts |  ✓ IN  |

### IPT
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Weissman, Markowitz & Klerman, *Comprehensive Guide to Interpersonal Psychotherapy* | Tier 1 | Full IPT reference; session structure, problem area work, termination procedures | ~$70–90 |

## Cross Modality Techniques

### Crisis Intervention / Safety
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Roberts (ed.), *Crisis Intervention Handbook* (Oxford) | Tier 1 | Step-by-step crisis response protocols; acute escalation procedures | ~$70–90 |

### Motivational Interviewing
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Miller & Rollnick, *Motivational Interviewing* (3rd ed., Guilford) | Tier 1 / Tier 2| Core MI procedures; OARS, rolling with resistance, evoking change talk | ~$60–80 |

### In-session clinical reasoning.
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | McWilliams, *Psychoanalytic Diagnosis* (2nd ed.) | Tier 1 / Tier 2| Character structure and defense mechanism recognition; in-session clinical reasoning | ~$60–80 |

### Alliance, Rupture & Repair 
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Safran & Muran, *Negotiating the Therapeutic Alliance* | Tier 1 / Tier 2| Rupture/repair transcripts with annotation; confrontation and withdrawal rupture procedures | ~$50–70 |


# TIER 2 Recommendations
### CBT + sub-domains (PE, DBT, ACT)
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Foa et al., *Prolonged Exposure Therapy for PTSD* — Therapist Guide (Oxford, 2022) | Tier 2 | Core PE protocol; step-by-step imaginal/in-vivo procedures; session-moment resolution |  ✓ IN  |
| 2 | *Comprehensive CBT for Social Phobia — Treatment Manual* | Tier 2 | Session structure, cognitive restructuring scripts for social anxiety | ✓ IN  |
| 3 | Linehan, *Cognitive-Behavioral Treatment of Borderline Personality Disorder* — case material chapters | Tier 2 | Annotated case material for BPD; in-session technique illustration | ~$80–100 (if not acquired in Domain 2) |
| 4 | Rudd et al., *Brief Cognitive Behavioral Therapy for Suicide Prevention* | Tier 2 | CBT-SP procedures; crisis management within CBT frame | ~$60–80 |

### IPT
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Klerman et al., *Interpersonal Psychotherapy of Depression* (IPT manual) | Tier 2 | Core IPT procedures; grief, role disputes, role 

### Motivational Interviewing
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Jobes, *Managing Suicidal Risk: A Collaborative Approach* (CAMS framework) | Tier 2 | CAMS collaborative framework; MI-informed crisis work; lethality assessment | ~$70–90 |

### In-Session Clinical Reasoning
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Herman, *Trauma and Recovery* | Tier 2 | Complex PTSD conceptual framework; historical trauma presentations | ~$20–30 |
