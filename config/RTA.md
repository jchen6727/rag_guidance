# Real Time Analysis (RTA) — Clinician Review Document

**Author:** James Chen (Backend AI/LLM Architect)  
**Version:** v0 (Initial Draft)  
**Date:** June 2026

---

## What Is RTA?

**Real Time Analysis (RTA)** is an AI-assisted tool designed to support clinicians during psychotherapy sessions. It works by listening to the flow of a session and surfacing relevant clinical knowledge in real time — pulling from a curated library of psychotherapy texts to inform in-session guidance.

This document combines two related review documents into a single reference:

1. **The Corpus** — the library of clinical texts RTA draws from
2. **The Schema** — the tagging system that tells the AI what each section of each text covers

Both are rough drafts (v0) requiring clinical review. **Your team's input is the most important step before we proceed.**

---

## A Note on Limitations of This Draft

Both sections of this document were assembled without clinical expertise, and without knowledge of:

- What actually occurs during a clinical session, and what reasoning is appropriate pre-session, in-session, or post-session
- Whether these texts adequately span the breadth and depth of CBT, DBT, and IPT care
- The practical availability of these texts to clinician-academics

**We expect the majority of this document to change** based on your feedback. The structure and organization shown here are working examples — the clinical content within them is yours to define.

*Vikki's contributions (culturally responsive care corpus and schema notes) are treated as authoritative and are marked accordingly.*

---

## Key Terms

| Term | Plain-language meaning |
|---|---|
| **Corpus** | The complete library of clinical texts RTA draws from |
| **Corpus ingestion** | The technical process of reading, analyzing, and indexing a document so the AI can search and retrieve its contents |
| **Chunk** | A discrete excerpt from a text — not the whole book, but a relevant passage or section. Tags are applied at the chunk level so the AI retrieves the specific relevant section, not the entire book. |
| **Tag / Metadata** | A label attached to a chunk indicating its clinical relevance (e.g., `CBT`, `depression`, `crisis_escalation`) |
| **Schema** | The full structured set of tags used to organize and retrieve content |
| **RAG (Retrieval-Augmented Generation)** | The AI approach RTA uses: rather than relying solely on built-in knowledge, it retrieves relevant passages from the corpus in real time to ground its responses |
| **SESSION TAG** | A label for content relevant to the *overall session frame* — pre-loaded based on modality and presentation before or at the start of a session |
| **EVENT TAG** | A label for content relevant to a specific *in-session clinical moment* — retrieved only when that event is detected |
| **Tier** | A priority level indicating how much processing time and review effort we invest in a given text |
| **LLM (Large Language Model)** | The AI system that reads retrieved content and generates real-time clinical guidance |

---

---

# PART 1: CORPUS

## The Tier Structure

We allocate our processing effort across texts using a tiered priority system. Think of it as analogous to how a training curriculum organizes its reading list: foundational texts first, then targeted supplements, then specialized references.

**Tier 1 and Tier 2 documents are considered necessary for a functioning RTA system.** Tier 3 documents will be included if time and resources allow.

### Tier 1 — Foundational Texts

* Cover the core knowledge and conceptual framework of a primary treatment modality (CBT, DBT, or IPT)
* Address interventional techniques and presentations *across* the modality as a whole
* Think of these as the text you would recommend a prospective clinician read first

We invest the majority of our processing budget (~70%) on Tier 1 documents. Because they are broad, dense, and foundational, the AI draws on them constantly and accurate indexing is critical. We expect very few Tier 1 documents per modality (possibly 1–2 per treatment domain).

### Tier 2 — Supplemental Texts

* Cover necessary supplemental knowledge within a treatment modality
* May focus on a specific subgroup of patients or presentations (e.g., CBT for Anxiety)
* Think of these as the text you would recommend to a clinician treating a specific patient presentation

We invest a smaller portion of our budget (~20–30%) on Tier 2 documents. Their narrower focus makes them more straightforward to index. We can accommodate roughly 3–5 per modality subgroup.

> **Note:** Tier 2 does not mean the clinical content is less important. It reflects narrower scope, which simplifies — but does not reduce the value of — our processing.

### Tier 3 — Specialized References

* Cover highly specialized knowledge that may fall outside the everyday scope of a generalist clinician
* May address a very specific set of clinical problems

We may process these briefly or defer them to post-session analysis contexts, or drop them entirely depending on available resources.

---

## Culturally Responsive Care

Vikki is serving as clinical SME for this domain. She has recommended the following Tier 1 texts and has additional schema notes for each:

1. *CA-CBT for Black Populations: A Manual for Mental Health Practitioners* (CAMH, 2024)
2. *Cultural Adaptations of Evidence-Based Interventions for Latinx Populations* (National Hispanic and Latino MHTTC, 2022)

---

## TIER 1 Document List

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

## TIER 2 Document List

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
| 1 | Klerman et al., *Interpersonal Psychotherapy of Depression* (IPT manual) | Tier 2 | Core IPT procedures: grief, role disputes, role transitions | ~$50 |

### Motivational Interviewing
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Jobes, *Managing Suicidal Risk: A Collaborative Approach* (CAMS framework) | Tier 2 | CAMS collaborative framework; MI-informed crisis work; lethality assessment | ~$70–90 |

### In-Session Clinical Reasoning
| # | Document | Tier | Utility | Est. Acquisition |
|---|---|---|---|---|
| 1 | Herman, *Trauma and Recovery* | Tier 2 | Complex PTSD conceptual framework; historical trauma presentations | ~$20–30 |

---

---

# PART 2: SCHEMA

## How the Tagging System Works

Each chunk in the corpus is labeled with one or more tags that describe its clinical content. When RTA is running, it uses these tags to retrieve the right passages at the right moment:

- **SESSION TAGS** are matched against the session setup (modality + patient presentation) and pre-loaded before or at the start of the session. These give the AI its baseline clinical context — the knowledge a therapist holds throughout the intervention.

- **EVENT TAGS** are matched against detected in-session events. When something clinically significant occurs (e.g., a rupture, a crisis escalation, a doorknob disclosure), the system retrieves content tagged for that event and surfaces it to the AI alongside the existing session context.

Tags are applied at the chunk level, not the book level. A comprehensive CBT manual is not tagged `depression` in its entirety — only the specific chapters or sections addressing depression treatment receive that tag.

---

## SESSION TAGS

### Therapeutic Modality Tags

| Tag | Full Name |
|---|---|
| `CBT` | Cognitive Behavioral Therapy |
| `CBT-I` | CBT for Insomnia |
| `BA` | Behavioral Activation |
| `REBT` | Rational Emotive Behavior Therapy |
| `Schema` | Schema Therapy |
| `DBT` | Dialectical Behavior Therapy |
| `CPT` | Cognitive Processing Therapy |
| `PE` | Prolonged Exposure |
| `IPT` | Interpersonal Psychotherapy |
| `IPSRT` | Interpersonal and Social Rhythm Therapy |
| `MI` | Motivational Interviewing |
| `MBCT` | Mindfulness-Based Cognitive Therapy |
| `UP` | Unified Protocol (transdiagnostic CBT) |
| `supportive` | Supportive Therapy |
| `integrative` | Integrative / Eclectic approaches |

### Clinical Presentation Tags

| Tag | Full Name / Clarification |
|---|---|
| `depression` | Major depressive disorder and depressive presentations |
| `bipolar` | Bipolar spectrum disorders |
| `anxiety_general` | Non-specific anxiety not meeting criteria for a distinct anxiety disorder |
| `panic_disorder` | Panic disorder |
| `social_anxiety` | Social anxiety disorder |
| `specific_phobia` | Specific phobia |
| `GAD` | Generalized Anxiety Disorder |
| `PTSD` | Post-Traumatic Stress Disorder |
| `complex_trauma` | Complex or developmental trauma (C-PTSD presentations) |
| `OCD` | Obsessive-Compulsive Disorder |
| `hoarding` | Hoarding disorder |
| `bfrb` | Body-Focused Repetitive Behaviors (e.g., trichotillomania, excoriation disorder) |
| `BPD` | Borderline Personality Disorder |
| `ADHD` | Attention-Deficit/Hyperactivity Disorder |
| `SUD` | Substance Use Disorder |
| `eating_disorder` | Eating disorders |
| `grief_bereavement` | Grief and bereavement presentations |
| `chronic_pain` | Chronic pain with significant psychological components |
| `somatic` | Somatic symptom and related disorders |
| `health_anxiety` | Health anxiety / illness anxiety disorder |
| `psychosis` | Psychotic spectrum presentations |
| `narcissistic` | Narcissistic personality presentation |
| `antisocial` | Antisocial personality presentation |
| `avoidant` | Avoidant personality presentation |
| `dependent` | Dependent personality presentation |
| `dissociative_disorders` | Dissociative disorders |
| `relationship_family` | Relationship and family-system issues |
| `medical_stress` | Psychological distress related to medical illness |
| `impulse_control` | Impulse control disorders |
| `insomnia` | Insomnia and sleep difficulties |
| `autism_spectrum` | Autism spectrum presentations |
| `perinatal` | Perinatal mood and anxiety disorders (prenatal and postpartum) |
| `other` | Presentations not captured by the above tags |

---

## EVENT TAGS

| Tag | Clinical Meaning |
|---|---|
| `rupture_withdrawal` | Patient becomes emotionally distant, goes quiet, or disengages from the therapeutic process |
| `rupture_confrontation` | Patient directly expresses frustration, criticism, or disagreement toward the therapist or the treatment |
| `rupture_repair` | Active clinical work to restore the therapeutic alliance following a rupture |
| `transference_enactment` | Patient's past relational patterns become activated and play out within the therapeutic relationship |
| `countertransference` | Therapist's own emotional reactions, thoughts, or behaviors arising in response to the patient |
| `doorknob_disclosure` | Patient discloses significant information at the very end of the session, often as they are leaving |
| `historical_disclosure` | Patient reveals previously undisclosed past trauma, abuse, or significant life history during session |
| `crisis_escalation` | Acute increase in patient distress; may involve suicidal ideation, self-harm urges, or acute psychiatric symptoms |
| `decompensation` | Clinically significant deterioration in patient functioning during or across sessions |
| `flight_into_health` | Patient suddenly reports dramatic improvement and resistance to continuing treatment, often functioning as an avoidance defense |
| `resistance_avoidance` | Patient actively or passively avoids engaging with therapeutic material or agreed-upon tasks |
| `intellectualization` | Patient engages with emotionally charged material in a detached, overly analytical manner as a defense against affect |
| `boundary_testing` | Patient behavior that challenges or probes the therapeutic frame or professional limits |
| `alliance_building` | Active clinical work to develop or strengthen the therapeutic relationship |
| `psychoeducation` | Clinician-provided education about a diagnosis, symptom, or treatment rationale occurring within session |
| `exposure_in_session` | In-session confrontation with feared stimuli, memories, or situations (imaginal or in-vivo) |
| `homework_review` | Review of between-session skill practice or assigned tasks |
| `termination_process` | Clinical work related to ending the therapeutic relationship: processing the ending and consolidating progress |
| `shame_activation` | Patient experiences or expresses acute shame within the session |
| `somatic_activation` | Patient reports or displays physical sensations in session associated with emotional content (e.g., tension, nausea, trembling) |
| `therapist_self_disclosure` | Therapist shares personal information or reactions with the patient within the session |
| `avoidance_safety_behavior` | Patient engages in behavior that reduces immediate distress but maintains the underlying problem |
| `minority_stress_disclosure` | Patient discloses experiences of discrimination, marginalization, or identity-related stress |
| `cultural_mismatch` | Emerging tension between the therapeutic approach and the patient's cultural background or values |
| `premature_termination_signal` | Patient signals intent to end treatment before goals are met |
| `grief_loss_activation` | Patient engages with grief, loss, or bereavement themes during session |
