RTA schema ---

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

ASA schema --- 

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