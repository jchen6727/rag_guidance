# rta_prompt/

Real-time analysis (RTA) and after-session analysis (ASA) pipelines for the psychotherapy guidance system. Both pipelines share the same corpus and generation infrastructure as the ingestion pipeline but are designed around fundamentally different latency and depth constraints.

See `PIPELINE_DIAGRAM.md` in this directory for visual architecture diagrams.

---

## I/O Contract

### RTA

| | Type | Description |
|---|---|---|
| **Input** | `str` | Rolling session transcript — all speaker turns up to and including the current moment, in chronological order |
| **Input** | `PatientContext` | Static patient/session metadata loaded at session open (modality, presentation, phase, clinician level) |
| **Output** | `RTAResponse` | Generated guidance text with inline citations, flagged clinical cautions, and a parallel low-priority risk-monitoring output |

The RTA pipeline is called once per speaker turn (or on a configurable stride). It must return within the timeframe of a live clinical exchange — typically under 5 seconds end-to-end.

### ASA

| | Type | Description |
|---|---|---|
| **Input** | `str` | Full session transcript |
| **Input** | `PatientContext` | Static patient/session metadata |
| **Input** | `str` | Patient history summary (prior sessions, formulation, outcome scores) — optional |
| **Output** | `ASAResponse` | Multi-section post-session report: autopsy, formulation update, treatment plan, homework, risk documentation |

The ASA pipeline runs once after session close. Latency is not a binding constraint; it issues multiple sequential retrieval hops.

---

## Directory Structure

```
rta_prompt/
├── README.md                  # this file
├── PIPELINE_DIAGRAM.md        # Mermaid architecture diagrams
├── models.py                  # RTA/ASA-specific dataclasses (PatientContext, RTAResponse, etc.)
├── rta/
│   ├── __init__.py
│   ├── event_detector.py      # Lightweight classifier → session_event_tags + risk_dimension_tags
│   ├── searcher.py            # RTA-scoped Vertex AI Search wrapper (hard pre-filters + event filter)
│   └── pipeline.py            # RTAPipeline — main entry point: transcript → RTAResponse
└── asa/
    ├── __init__.py
    ├── searcher.py            # ASA-scoped searcher (analysis_function-routed multi-hop)
    └── pipeline.py            # ASAPipeline — main entry point: transcript → ASAResponse
```

---

## How This Fits Into the Broader Project

The ingestion path (`scripts/batch_ingest.py` → `CorpusScanner` → Vertex AI Search) is a prerequisite — the corpus must be indexed with the full psychotherapy schema (see `corpus/CORPUS_NOTES_RTA.md` and `corpus/CORPUS_NOTES_ASA.md`) before either pipeline can run.

The existing infrastructure reused without modification:

| Module | Reused by |
|---|---|
| `retrieval.searcher.CorpusSearcher` | Both `rta.searcher.RTASearcher` and `asa.searcher.ASASearcher` (composition, not inheritance) |
| `retrieval.reranker.LLMReranker` | RTA pipeline (optional, controlled by `PatientContext.enable_reranker`) |
| `generation.prompt_builder.PromptBuilder` | Both pipelines (with psychotherapy persona from `config/prompt_config.yaml`) |
| `generation.response_gen.ResponseGenerator` | Both pipelines |
| `generation.citation_builder.CitationBuilder` | Both pipelines |
| `models.SearchResult`, `GeneratedResponse`, `Citation` | Passed through unchanged |
| `config.settings.settings` | GCP credentials, model names, engine IDs |

---

## Schema Field Usage

### Static fields — set once at session open from patient record

| Field | Used as |
|---|---|
| `therapeutic_modality` | Hard pre-filter on every RTA/ASA query |
| `clinical_presentation` | Hard pre-filter on every RTA/ASA query |
| `session_phase` | Hard pre-filter on every RTA/ASA query |
| `target_audience` | Hard pre-filter: always exclude `patient` documents |
| `corpus_scope` | Hard pre-filter: RTA excludes `asa_only`; ASA allows both |
| `training_level_required` | Hard pre-filter: only surface guidance appropriate for clinician's level |

### Dynamic fields — inferred per speaker turn by `EventDetector`

| Field | Used as |
|---|---|
| `session_event_tags` | Event-triggered retrieval filter (main clinical guidance path) |
| `risk_dimension_tags` | Passive background retrieval (runs every turn, low-priority channel) |

### ASA routing fields — set at session open or post-session

| Field | Used as |
|---|---|
| `analysis_function` | Hop routing: each ASA retrieval hop targets one function |
| `evidence_base` | Filter: treatment-matching hops require `rct_primary`, `rct_moderator`, or `meta_analytic` |
| `patient_population` | Filter: match to current patient profile for treatment matching |
| `time_horizon` | Filter: near-term vs. treatment-course vs. post-termination queries |
| `outcome_measure_tags` | Filter: instrument-specific routing for outcome monitoring hop |

---

## Running the Pipelines

```bash
# RTA (single turn):
PYTHONPATH=. python -c "
from rta_prompt.models import PatientContext
from rta_prompt.rta.pipeline import RTAPipeline
ctx = PatientContext(therapeutic_modality=['CBT'], clinical_presentation=['PTSD'], session_phase='mid_treatment')
pipeline = RTAPipeline(patient_context=ctx)
response = pipeline.run(transcript='Therapist: Let us start the exposure today. Patient: I don't want to.')
print(response.guidance_text)
"

# ASA (full session):
PYTHONPATH=. python -c "
from rta_prompt.models import PatientContext
from rta_prompt.asa.pipeline import ASAPipeline
ctx = PatientContext(therapeutic_modality=['DBT'], clinical_presentation=['BPD'], session_phase='mid_treatment')
pipeline = ASAPipeline(patient_context=ctx)
response = pipeline.run(transcript=open('session.txt').read())
print(response.autopsy_text)
"
```

---

## Known Issues Inherited from Scaffolding

The issues in `CLAUDE.md §Known Issues` apply here. Additionally:

- **`prompt_config.yaml` has no psychotherapy persona.** Current personas are biomedical (cardiology, oncology, etc.). A `psychotherapy` persona and modality sub-personas (`cognitive_behavioral`, `trauma_focused`, `psychodynamic`) must be added before the pipelines produce appropriate guidance tone.
- **Schema fields in `config/metadata_schema.json` do not yet include the psychotherapy fields** (`therapeutic_modality`, `session_event_tags`, `analysis_function`, etc.) described in the corpus notes. Schema registration and full re-ingestion are required before the filters in these pipelines will match anything.
- **`EventDetector` LLM path uses a small Gemini model** (configurable, defaults to `gemini-1.5-flash`). The heuristic path runs first and short-circuits to avoid the LLM call for obvious events.
