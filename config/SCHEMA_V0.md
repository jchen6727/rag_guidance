# Initial Rough (v0) of proposed Real Time Analysis (RTA) Corpus Schema

Author: James Chen (Backend AI/LLM Architect)

### RE: Lack of Clinical SME in Generating this Document (Most Important!)
As before, I am not a clinical SME for the purpose of psychotherapy. This document is considered a rough draft only, and is only included as an example of the organization and structure of our work.

Again, it is done agnostic to:
1. what occurs during a clinical session, including what is appropriate reasoning pre session vs. in session vs. after session.

2. what set of tags accurately span the breadth and depth of CBT, DBT and IPT care.

Instead, this list is simply used as an example organization and tier structure that we will be using to help determine our approach to corpus ingestion (see notes)

### RE: Current Absence of Non-Event Reasoning Tags ("Awareness Tags")
As discussed in the powerpoint, it is possible that event detection may need to be supplemented by its own smaller corpus (i.e., how to detect therapeutic rupture) to detect the nuances of what occurs during a therapy session. For now, those tags are not included here.


### RE: Real Time Analysis Focus Only
To narrow the scope of this document, we are only considering metadata tags for information relevant to the real time analysis provided during a therapy session. Elements that may fall into materials relevant after the session (for instance, tags to indicate a document is a homework assignment, or helps planning longitudinal care) are not included here.

### RE: Document vs .json
For the purposes of reader clarity, I am translating our .json to a technically agnostic explanation of schema. Instead
I am going to define two sets of tags. *SESSION TAGS* help organize chunks that are pre-loaded at the "Session Level" -- for instance, chunks tagged with *CBT* and *Depression* will likely be loaded into the analytical reasoning LLM before the session starts based on matching the intervention and presentation defined by the case (i.e. treating a patient with depression with CBT techniques). *EVENT TAGS* help organize chunks to be pulled up during an event -- for instance, how to handle therapeutic rupture will not be provided to the analytical reasoning LLM throughout the session, but only when a therapeutic rupture event occurs.

### RE: Chunks vs. Books
Tags do not have to refer to entire books, part of the ingestion process is ensuring that we chunk any relevant excerpts of a text with the metadata appropriate to that individual excerpt, not the entire book. So a comprehensive manual on CBT will not have its entire contents tagged with *Depression*, just any chapters specific to that clinical presentation.

### RE: Non-reasoning Tags
As Vikki mentioned, there are numerous additional tags that are relevant for data post-processing or data-audits. For the sake of conciseness to the backend architectural specifications and reasoning logic, I am only including tags that 

## SESSION TAGS

Session tags are intended to help provide an overall context to the analytical LLM prior to/regardless of any event occuring. In other words, a therapist holding a CBT session for someone with depression would likely be thinking of this material as they enter the room, and throughout the intervention to guide the rough framework of the treatment.

### Therapeutic Modality Session Tags
    "CBT", "CBT-I", "BA", "REBT", "Schema", 
    "DBT", "CPT", "PE", "IPT", "IPSRT",
    "MI", "MBCT", "UP", "supportive", "integrative"

### Clinical Presentation Session Tags
    "depression", "bipolar", "anxiety_general", "panic_disorder",
    "social_anxiety", "specific_phobia", "GAD",
    "PTSD", "complex_trauma",
    "OCD", "hoarding", "bfrb",
    "BPD", "ADHD",
    "SUD", "eating_disorder",
    "grief_bereavement", "chronic_pain", "somatic", "health_anxiety",
    "psychosis",
    "narcissistic", "antisocial", "avoidant", "dependent",
    "dissociative_disorders",
    "relationship_family", "medical_stress", "impulse_control", "insomnia",
    "autism_spectrum", "perinatal",
    "other"

## EVENT TAGS

Event tags are intended to help provide additional moment-to-moment context, retrieved and provided to the analytical LLM in response to event triggers. In other words, if a patient responds in a certain way, the therapist may refer to specific "in the moment" responses before returning to their overall session treatment framework.

### All Event Tags
    "rupture_withdrawal", "rupture_confrontation", "rupture_repair",
    "transference_enactment", "countertransference",
    "doorknob_disclosure", "historical_disclosure",
    "crisis_escalation", "decompensation",
    "flight_into_health", "resistance_avoidance",
    "intellectualization", "boundary_testing",
    "alliance_building", "psychoeducation",
    "exposure_in_session", "homework_review",
    "termination_process", "shame_activation",
    "somatic_activation", "therapist_self_disclosure",
    "avoidance_safety_behavior", "minority_stress_disclosure",
    "cultural_mismatch", "premature_termination_signal",
    "grief_loss_activation",

