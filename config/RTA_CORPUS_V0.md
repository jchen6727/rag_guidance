# Initial Rough (v0) of Proposed Real Time Analysis (RTA) Corpus

Author: James Chen (Backend AI/LLM Architect)

---

## How to Read This Document

This document proposes an initial library of clinical texts (the **corpus**) to support an AI-assisted tool called **Real Time Analysis (RTA)**. RTA is designed to surface relevant clinical knowledge to clinicians in real time during psychotherapy sessions.

**What we are asking of you:** Please review the document list and tier assignments below. Your clinical expertise is authoritative here — we need you to tell us which texts to add, remove, or reclassify. We have not been able to evaluate these materials from a clinical practice standpoint and are relying on your team to do so.

**Key terms used in this document:**

| Term | Plain-language meaning |
|---|---|
| **Corpus** | The complete library of clinical texts the AI draws from when providing guidance |
| **Corpus ingestion** | The technical process of reading, analyzing, and indexing a document so the AI can search and retrieve its contents |
| **Metadata / Tags** | Labels attached to individual sections of a text (e.g., "CBT," "depression," "crisis_escalation") that tell the AI what clinical content each section covers |
| **RAG (Retrieval-Augmented Generation)** | The approach RTA uses: rather than relying solely on built-in AI knowledge, it retrieves relevant passages from the corpus in real time to ground its responses |
| **Tier** | A priority category indicating how much processing time and review effort we invest in a given document |

---

## RE: Lack of Clinical SME in Generating This Document (Most Important)

Except for Vikki's recommendations, our tier assignments, modality organization, and document searches were conducted without clinical expertise — specifically, without knowledge of:

1. What occurs during a clinical session, including what reasoning is appropriate pre-session vs. in-session vs. after session.

2. The degree to which these texts span the breadth and depth of CBT, DBT, and IPT care.

3. The practical availability of these texts to clinician-academics.

**We anticipate the majority — or all — of this list will change** as we work with your team to clarify what the corpus should contain and when content should be retrieved. We are relying on your team to add, remove, and reclassify documents.

This list exists only as a working example of the organizational structure we are proposing, not as a clinical recommendation.

---

## RE: The Tier Structure

We use a tiered system to allocate how much time and processing effort we invest in each document. Think of it as analogous to how a training curriculum might organize its reading list: some texts are foundational and essential, others are important supplements, and some are specialized references used only as needed.

**Tier 1 and Tier 2 documents are considered necessary for a functioning RTA system.** Tier 3 documents will be considered if time and resources permit.

### Tier 1 — Foundational Texts

* Cover the core knowledge and conceptual framework of a primary treatment modality (CBT, DBT, or IPT)
* Address interventional techniques and presentations *across* the modality as a whole
* Think of these as the text you would recommend a prospective clinician read first — a comprehensive guide to CBT, DBT, or IPT

We invest the majority of our processing budget (~70%) on Tier 1 documents. Because they are broad, dense, and foundational, accurate indexing of these texts is critical — the AI draws on them constantly. We expect very few Tier 1 documents per modality (possibly 1–2 per treatment domain).

### Tier 2 — Supplemental Texts

* Cover necessary supplemental knowledge within a treatment modality
* May focus on a specific subgroup of patients or presentations (e.g., CBT for Anxiety specifically)
* Think of these as the text you would recommend to a clinician looking at a specific clinical vignette

We invest a smaller portion of our budget (~20–30%) on Tier 2 documents. Their narrower focus makes indexing more straightforward. We can accommodate more of them — roughly 3–5 per modality subgroup.

> **Note:** Tier 2 does not mean the clinical content is less important. It reflects the narrower scope of the document, which simplifies — but does not reduce the value of — our processing of it.

### Tier 3 — Specialized References

* Cover highly specialized knowledge within a modality that may fall outside the everyday scope of a generalist clinician
* May address a very specific set of clinical problems

We may process these briefly or defer them to post-session analysis contexts. We may also drop them entirely depending on available time and resources.

---

## RE: Culturally Responsive Care

Vikki is serving as our clinical SME for corpus and schema in this domain. She has recommended two texts:

1. *CA-CBT for Black Populations: A Manual for Mental Health Practitioners* (CAMH, 2024)

2. *Cultural Adaptations of Evidence-Based Interventions for Latinx Populations* (National Hispanic and Latino MHTTC, 2022)

She also has additional schema notes for these texts. Because she is leading both the theoretical framing and the implementation of this area, these texts will be treated as Tier 1 documents.

---

# TIER 1 Recommendations

## Therapeutic Modalities

### All Modality Reference
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | APA Handbook of Psychiatry | Tier 1 | Chapters spanning multiple modalities, presentations, and interventional events | ~$400 |

### CBT and Sub-Domains (PE, DBT, ACT)
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Boswell & Constantino, *Deliberate Practice in CBT* (APA) | Tier 1 | Therapist skill refinement; annotated technique gaps; deliberate practice protocols | ✓ IN |
| 2 | Linehan, *DBT Skills Training Manual* (2nd ed., Guilford) — Clinician's Edition | Tier 1 | Core DBT skills procedures: chain analysis, diary card review, distress tolerance, emotion regulation | ~$80–100 |
| 3 | Hayes, Strosahl & Wilson, *Acceptance and Commitment Therapy* — Practitioner's Guide | Tier 1 | Core ACT procedures: defusion, values work, committed action in session | ~$70–90 |
| 4 | *Thousand Voices of Trauma* — Annotated Texts | Tier 1 | CBT session transcripts with clinical annotation | ✓ IN |

### IPT
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Weissman, Markowitz & Klerman, *Comprehensive Guide to Interpersonal Psychotherapy* | Tier 1 | Full IPT reference: session structure, problem area work, termination procedures | ~$70–90 |

---

## Cross-Modality Techniques

### Crisis Intervention / Safety
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Roberts (ed.), *Crisis Intervention Handbook* (Oxford) | Tier 1 | Step-by-step crisis response protocols; acute escalation procedures | ~$70–90 |

### Motivational Interviewing
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Miller & Rollnick, *Motivational Interviewing* (3rd ed., Guilford) | Tier 1 / Tier 2 | Core MI procedures: OARS, rolling with resistance, evoking change talk | ~$60–80 |

### In-Session Clinical Reasoning
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | McWilliams, *Psychoanalytic Diagnosis* (2nd ed.) | Tier 1 / Tier 2 | Character structure and defense mechanism recognition; in-session clinical reasoning | ~$60–80 |

### Alliance, Rupture & Repair
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Safran & Muran, *Negotiating the Therapeutic Alliance* | Tier 1 / Tier 2 | Rupture/repair transcripts with clinical annotation; confrontation and withdrawal rupture procedures | ~$50–70 |

---

# TIER 2 Recommendations

### CBT and Sub-Domains (PE, DBT, ACT)
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Foa et al., *Prolonged Exposure Therapy for PTSD* — Therapist Guide (Oxford, 2022) | Tier 2 | Core PE protocol: step-by-step imaginal and in-vivo exposure procedures | ✓ IN |
| 2 | *Comprehensive CBT for Social Phobia — Treatment Manual* | Tier 2 | Session structure; cognitive restructuring scripts for social anxiety | ✓ IN |
| 3 | Linehan, *Cognitive-Behavioral Treatment of Borderline Personality Disorder* — case material chapters | Tier 2 | Annotated case material for BPD; in-session technique illustration | ~$80–100 (if not acquired in Domain 2) |
| 4 | Rudd et al., *Brief Cognitive Behavioral Therapy for Suicide Prevention* | Tier 2 | CBT-SP procedures; crisis management within a CBT treatment frame | ~$60–80 |

### IPT
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Klerman et al., *Interpersonal Psychotherapy of Depression* (IPT manual) | Tier 2 | Core IPT procedures: grief, role disputes, role transitions *(entry incomplete — please verify and expand)* | — |

### Motivational Interviewing
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Jobes, *Managing Suicidal Risk: A Collaborative Approach* (CAMS framework) | Tier 2 | CAMS collaborative framework; MI-informed crisis work; lethality assessment | ~$70–90 |

### In-Session Clinical Reasoning
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Herman, *Trauma and Recovery* | Tier 2 | Complex PTSD conceptual framework; historical trauma presentations | ~$20–30 |
