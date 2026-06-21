# RAG Pipeline Architecture — Mermaid Diagrams

---

## 1. RTA Pipeline (Real-Time Analysis)

The optimized 1.5-pass design: static metadata from the patient record eliminates the first LLM classification pass for all non-event fields. Only `session_event_tags` and `risk_dimension_tags` require real-time inference.

```mermaid
flowchart TD
    subgraph SESSION_OPEN["Session Open — Pre-load from Patient Record"]
        PR[/"Patient Record"/]
        SF["Static Schema Fields\ntherapeutic_modality\nclinical_presentation\nsession_phase\ncorpus_scope = rta_and_asa\ntarget_audience = therapist"]
        PR --> SF
        SF -->|"background sweep at session start"| WARM["Warm Document Pool\nbroad modality + presentation filters\ncached in memory"]
    end

    TR[/"Rolling Transcript Window\nupdated per speaker turn"/]

    subgraph P1["Pass 1 — Concurrent Event Detection"]
        direction LR
        HEUR["Heuristic Triggers\nSI language → crisis_escalation\nsession-end marker → doorknob_disclosure\nrequest pattern → boundary_testing"]
        SMALL["Lightweight Classifier\nHaiku or fine-tuned model\nclassifies session_event_tags only"]
        HEUR --> EVT["session_event_tags\ndynamic per turn"]
        SMALL --> EVT
    end

    TR --> P1
    TR --> SQ["Semantic Query\ntranscript window as text"]

    subgraph P2["Pass 2 — Vertex AI Search"]
        direction TB
        HARD["Hard Pre-Filters\ncorpus_scope != asa_only\ntarget_audience != patient\ntherapeutic_modality match\nclinical_presentation match\nsession_phase match"]
        EF["Event Filter\nsession_event_tags IN detected events"]
        CAUTION["clinical_caution flag\nsurface contraindications\nalongside technique results"]
        TRAIN["training_level_required\npre-filter by clinician level"]
        RP["Passive Risk Pass\nrisk_dimension_tags\nruns every session\nlower-priority channel"]
    end

    SF --> HARD
    EVT --> EF
    SQ --> P2
    HARD --> P2
    EF --> P2
    CAUTION --> P2
    TRAIN --> P2
    WARM -.->|"post-filter warm pool\navoids cold DataStore hit"| P2

    subgraph P3["Pass 3 — Streaming Generation"]
        RG["ResponseGenerator.generate()\nstreams on first ranked passages\ndoes not wait for full retrieval window"]
        CB["CitationBuilder.build()\npage_start and page_end\nfrom SearchResult.metadata\nnot from grounding metadata"]
        RG --> CB
    end

    P2 --> RG
    RP -->|"low-priority merge"| RG
    CB --> OUT[/"Real-Time Clinical Guidance\n+ background risk monitoring output"/]
```

---

## 2. ASA Pipeline (After-Session Analysis)

Multi-hop retrieval is intentional here. Each hop is sequenced: the output of earlier hops is injected as context into later retrieval queries. Latency is not a binding constraint.

```mermaid
flowchart TD
    subgraph INPUTS["Inputs"]
        FT[/"Full Session Transcript"/]
        HIST[/"Patient History\nprior sessions, formulation, outcome scores"/]
        STATIC["Known-at-open Fields\ntherapeutic_modality\nclinical_presentation\nsession_phase\ncorpus_scope = rta_and_asa OR asa_only\npatient_population\ntime_horizon"]
    end

    subgraph HOP1["Hop 1 — Session Autopsy"]
        H1Q["Query: what clinical events occurred?\nanalysis_function = session_autopsy\nevidence_base = expert_clinical OR illustrative\nsession_event_tags match detected events"]
        H1R[/"Autopsy Passages\nnamed events, response evaluations\nmissed opportunities"/]
        H1Q --> H1R
    end

    subgraph HOP2["Hop 2 — Longitudinal Planning"]
        H2Q["Query: what does evidence say for next steps?\nanalysis_function = treatment_plan_revision\nevidence_base IN rct_primary, rct_moderator, meta_analytic\npatient_population match\ntime_horizon = near_term OR short_term OR treatment_course"]
        H2R[/"Evidence Passages\nRCTs, meta-analyses\ntreatment matching literature"/]
        H2Q --> H2R
    end

    subgraph HOP3["Hop 3 — Resource Retrieval (conditional)"]
        H3CHECK{"Homework or\nrisk documentation\nneeded?"}
        H3A["analysis_function = homework_resource\ntherapeutic_modality match\nclinical_presentation match\ntarget_audience = patient\ncorpus_scope = asa_only"]
        H3B["analysis_function = risk_documentation\nOR outcome_monitoring\nOR referral_coordination"]
        H3CHECK -->|"yes"| H3A
        H3CHECK -->|"yes"| H3B
        H3CHECK -->|"no"| SKIP["skip hop 3"]
    end

    subgraph GENERATE["Generation"]
        RG["ResponseGenerator.generate()\nall hop results as context\ncorpus_scope filter enforced\nno asa_only chunks in RTA path"]
        CB["CitationBuilder.build()"]
        RG --> CB
    end

    FT --> HOP1
    HIST --> HOP1
    STATIC --> HOP1
    H1R -->|"session events as context"| HOP2
    H1R --> H3CHECK
    H2R -->|"treatment context"| HOP3
    H2R --> RG
    H1R --> RG
    H3A --> RG
    H3B --> RG
    CB --> ASA_OUT[/"Post-Session Report\nSession autopsy\nCase formulation update\nTreatment plan revision\nHomework assignments\nRisk documentation"/]
```

---

## 3. Schema Field Taxonomy

Which fields are set statically (from patient record before session), which require real-time inference, which are ASA-only additions, and how each field is used in retrieval.

```mermaid
flowchart LR
    subgraph WHEN["When is this field set?"]
        direction TB
        STATIC_NODE["Static\nKnown at session open\nfrom patient record"]
        DYNAMIC_NODE["Dynamic\nInferred per speaker turn\nor post-session"]
    end

    subgraph RTA_FIELDS["RTA Schema Fields"]
        direction TB
        subgraph RTA_STATIC["Static — pre-loaded"]
            therapeutic_modality["therapeutic_modality\nprimary retrieval filter"]
            clinical_presentation["clinical_presentation\nprimary retrieval filter"]
            session_phase["session_phase\nretrieval filter"]
            target_audience["target_audience\nhard pre-filter: != patient"]
            corpus_scope_rta["corpus_scope\nhard pre-filter: != asa_only"]
        end
        subgraph RTA_DYNAMIC["Dynamic — real-time inference"]
            session_event_tags["session_event_tags\nprimary event trigger\nlightweight classifier"]
            risk_dimension_tags["risk_dimension_tags\npassive background pass\nevery session"]
        end
        subgraph RTA_CONTENT["Content-level — Gemini extraction at ingest"]
            technique_tags["technique_tags\nranking signal"]
            clinical_caution["clinical_caution\nsurface with technique results"]
            training_level_required["training_level_required\npre-filter by clinician level"]
            practice_recommendation_level["practice_recommendation_level\nranking signal"]
        end
    end

    subgraph ASA_FIELDS["ASA-Only Schema Fields"]
        direction TB
        subgraph ASA_ROUTING["Routing — set at session open or post-session"]
            corpus_scope_asa["corpus_scope\nasa_only lifts RTA exclusion"]
            analysis_function["analysis_function\nprimary hop-routing field\nsequences multi-hop retrieval"]
            time_horizon["time_horizon\nnear_term vs treatment_course vs post_termination"]
        end
        subgraph ASA_EVIDENCE["Evidence quality — Gemini extraction at ingest"]
            evidence_base["evidence_base\nrct_primary, rct_moderator\nmeta_analytic, expert_clinical"]
            patient_population["patient_population\ntreatment matching filter\ncross-matched to current patient"]
            outcome_measure_tags["outcome_measure_tags\nroutes to specific instrument guidance"]
        end
    end

    STATIC_NODE --> RTA_STATIC
    DYNAMIC_NODE --> RTA_DYNAMIC
    STATIC_NODE --> ASA_ROUTING
    DYNAMIC_NODE --> ASA_EVIDENCE
```

---

## 4. Field-to-Stage Mapping (Quick Reference)

```mermaid
flowchart LR
    subgraph FIELDS["Schema Fields"]
        F1["therapeutic_modality"]
        F2["clinical_presentation"]
        F3["session_phase"]
        F4["corpus_scope"]
        F5["target_audience"]
        F6["session_event_tags"]
        F7["risk_dimension_tags"]
        F8["clinical_caution"]
        F9["training_level_required"]
        F10["practice_recommendation_level"]
        F11["technique_tags"]
        F12["analysis_function"]
        F13["evidence_base"]
        F14["patient_population"]
        F15["time_horizon"]
        F16["outcome_measure_tags"]
    end

    subgraph STAGES["Pipeline Stage"]
        S1["Hard Pre-Filter\nblocks retrieval entirely"]
        S2["Event Filter\ntriggers retrieval path"]
        S3["Hop Routing\nASA multi-hop sequencer"]
        S4["Ranking Signal\nscores retrieved passages"]
        S5["Safety Gate\nsurfaces alongside results"]
    end

    F1 --> S1
    F2 --> S1
    F3 --> S1
    F4 --> S1
    F5 --> S1
    F9 --> S1

    F6 --> S2
    F7 --> S2

    F12 --> S3
    F13 --> S3
    F14 --> S3
    F15 --> S3
    F16 --> S3

    F10 --> S4
    F11 --> S4
    F13 --> S4

    F8 --> S5
```
