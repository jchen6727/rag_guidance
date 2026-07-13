# Initial Rough (v0) of Proposed Real Time Analysis (RTA) Corpus Schema

Author: James Chen (Backend AI/LLM Architect)

---

## How to Read This Document

This document describes the **tagging schema** — the system of labels we attach to individual sections of clinical texts so the AI knows what content each section covers and can retrieve the right passage at the right moment during a session.

**What we are asking of you:** Please review the tag categories and individual tags below. Your clinical expertise is essential for determining whether these labels accurately reflect the distinctions that matter in real-time clinical practice. Specifically: Are the right categories represented? Do the existing tags capture what a clinician would actually need in that moment?

**Key concepts:**

| Term | Plain-language meaning |
|---|---|
| **Schema** | The structured set of labels (tags) used to organize and retrieve content |
| **Tag** | A label attached to a passage in the corpus indicating its clinical relevance (e.g., `CBT`, `crisis_escalation`) |
| **Chunk** | A discrete excerpt from a clinical text — not the whole book, but a relevant passage or section. Tags are applied at the chunk level. For example, a comprehensive CBT manual's chapter on depression gets tagged `depression`; the rest of the book does not. This is intentional: we want the AI to retrieve the specific relevant section, not the entire book. |
| **SESSION TAG** | A label indicating content relevant to the *overall session frame* — pre-loaded before or throughout a session based on the treatment modality and patient presentation |
| **EVENT TAG** | A label indicating content relevant to a specific *in-session clinical moment* — retrieved only when that type of event is detected |
| **LLM (Large Language Model)** | The AI system that reads retrieved content and uses it to generate real-time clinical guidance |

---

## RE: Lack of Clinical SME in Generating This Document (Most Important)

As noted in the corpus document, I am not a clinical SME for psychotherapy. This document is a rough draft only and is included as a working example of how we propose to organize the schema.

It was generated agnostic to:

1. What occurs during a clinical session, including what reasoning is appropriate pre-session vs. in-session vs. after session.

2. What set of tags accurately spans the breadth and depth of CBT, DBT, and IPT care.

---

## RE: Absence of Non-Event Reasoning Tags ("Awareness Tags")

As discussed in the presentation, event detection may need to be supplemented by a smaller, separate reference set of materials focused on *how to recognize* therapeutic events (e.g., how to detect a therapeutic rupture), distinct from how to respond to them. Those tags are not included here yet and represent a design question for your team.

---

## RE: Real-Time Analysis Scope Only

This schema covers only content relevant to real-time, in-session guidance. Tags for materials relevant *after* the session (e.g., homework assignment templates, longitudinal care planning) are excluded here.

---

## RE: Tags vs. the Full Technical Schema

For readability, this document presents the schema in plain language rather than as a technical configuration file. In practice, the schema is implemented as structured data (JSON) used internally by the system. You do not need to understand the technical format — the tag names and their clinical meanings are what matter for your review.

---

## SESSION TAGS

Session tags are applied to content that provides the overall treatment framework context for a session — the clinical knowledge a therapist holds throughout a session based on the modality they are using and the patient's presentation.

**How they are used:** When a session begins with a defined modality (e.g., CBT) and presentation (e.g., depression), the system pre-loads chunks tagged with those values to give the AI its foundational session context.

---

### Therapeutic Modality Session Tags

These tags identify which treatment approach a given passage is relevant to.

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

---

### Clinical Presentation Session Tags

These tags identify the patient presentation or diagnosis a given passage is relevant to.

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

Event tags are applied to content relevant to specific clinical moments that occur during a session. These passages are retrieved only when that type of event is detected — they are not part of the baseline session context.

**How they are used:** When a clinical event is identified (e.g., the patient appears to disengage from the therapeutic process), the system retrieves chunks tagged for that event and surfaces them to the AI alongside the session-level context already loaded. Think of this as the knowledge a clinician might quickly reference when something unexpected or clinically significant occurs.

---

### All Event Tags

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
