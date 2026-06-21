"""
RTA/ASA-specific data models.

These types define the I/O boundary of both pipelines. They extend the core
models in the top-level models.py — SearchResult, GeneratedResponse, and
Citation pass through unchanged; the new types here carry the session and
patient context that drives psychotherapy-specific retrieval routing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


# ---------------------------------------------------------------------------
# Session / patient context (set once at session open)
# ---------------------------------------------------------------------------


@dataclass
class PatientContext:
    """Static session metadata loaded from the patient record before session start.

    These fields translate directly to Vertex AI Search hard pre-filters that
    remain constant for the entire session. They are never re-inferred during
    the session — only the event-level fields (session_event_tags,
    risk_dimension_tags) change per speaker turn.

    All controlled-vocabulary values must match the enums registered in the
    Vertex AI Search DataStore schema. Invalid values are logged as warnings
    and omitted from filter expressions (the query still runs; it just loses
    that axis of filtering).
    """

    # Primary retrieval filters — required for modality-matched guidance
    therapeutic_modality: list[str] = field(default_factory=list)
    """Therapy modality tags for this patient's treatment.

    Examples: ["CBT"], ["DBT", "ACT"], ["PE"]
    Must be values from the therapeutic_modality enum in the corpus schema.
    """

    clinical_presentation: list[str] = field(default_factory=list)
    """Diagnostic presentations or clinical themes for this patient.

    Examples: ["PTSD", "depression"], ["BPD", "SUD"]
    Must be values from the clinical_presentation enum in the corpus schema.
    """

    session_phase: str = "any"
    """Current phase of treatment for this patient.

    Values: assessment_intake | early_treatment | mid_treatment |
            late_treatment | termination | crisis | any
    """

    # Clinician-level gate — prevents surfacing specialist-only guidance to trainees
    clinician_training_level: str = "generalist"
    """Minimum training level of the clinician using this tool.

    Values: generalist | supervised_trainee | post_licensure | specialist_trained
    Only chunks with training_level_required <= this level are retrieved.
    """

    # Optional ASA-specific fields
    patient_population: list[str] = field(default_factory=list)
    """Population descriptors for treatment-matching queries (ASA only).

    Examples: ["adult_general"], ["veteran_military"], ["adolescent", "lgbtq"]
    Used to filter RCT and meta-analysis chunks by applicable population.
    """

    # Pipeline behavior flags
    enable_reranker: bool = False
    """If True, apply LLMReranker after retrieval. Adds ~1–2s latency.

    Enable when retrieval precision measurements justify the cost. Disabled
    by default for RTA to preserve latency budget.
    """

    enable_risk_pass: bool = True
    """If True, run a passive background risk-monitoring retrieval pass every turn.

    Results are merged into RTAResponse.risk_guidance at lower priority than the
    main event-triggered guidance. Should remain True for all active clinical use.
    """

    rta_top_k: int = 8
    """Number of passages to retrieve for the main RTA guidance path."""

    risk_top_k: int = 4
    """Number of passages to retrieve for the passive risk-monitoring path."""


# ---------------------------------------------------------------------------
# Transcript representation
# ---------------------------------------------------------------------------


@dataclass
class TranscriptTurn:
    """A single speaker turn in the session transcript."""

    speaker: str
    """Speaker label. Conventionally "Therapist" or "Patient"; freeform string."""

    text: str
    """Verbatim or lightly edited text of the turn."""

    turn_index: int = 0
    """Zero-based position of this turn in the session."""


@dataclass
class SessionTranscript:
    """The rolling session transcript passed to the RTA pipeline.

    Populated incrementally as the session proceeds. The pipeline receives
    the full transcript-so-far on each call — not just the most recent turn.
    The pipeline internally selects the window to query with.
    """

    turns: list[TranscriptTurn] = field(default_factory=list)
    """All turns in chronological order."""

    raw_text: str = ""
    """Pre-formatted full transcript string. If provided, takes precedence over
    assembling from turns. Use this when the transcript is provided as a plain
    string rather than structured turn objects."""

    @classmethod
    def from_text(cls, text: str) -> "SessionTranscript":
        """Construct a SessionTranscript from a plain text transcript string.

        Args:
            text: Full transcript as a string. May be formatted as
                  'Therapist: ...\nPatient: ...' or unstructured prose.

        Returns:
            SessionTranscript with raw_text populated and turns left empty.
            Turn parsing is deferred to the pipeline if needed.
        """
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Event detection output
# ---------------------------------------------------------------------------


@dataclass
class DetectedEvent:
    """A single in-session event identified by EventDetector.

    Maps to a value in the session_event_tags controlled vocabulary.
    """

    tag: str
    """session_event_tags value (e.g. "rupture_withdrawal", "crisis_escalation")."""

    confidence: float = 1.0
    """Detection confidence [0.0, 1.0].

    Heuristic detections are always 1.0. LLM detections carry the model's
    expressed confidence. Detections below EventDetector.min_confidence are
    filtered before they reach the searcher.
    """

    source: str = "heuristic"
    """Detection method: "heuristic" | "llm".

    Heuristic detections fire on regex/keyword patterns and are logged
    separately from LLM detections for calibration monitoring.
    """

    trigger_text: str = ""
    """The transcript span that triggered this detection. Used for logging and
    debugging — not surfaced in clinical output."""


# ---------------------------------------------------------------------------
# RTA pipeline output
# ---------------------------------------------------------------------------


@dataclass
class RTAResponse:
    """Output of RTAPipeline.run() for a single transcript update.

    Designed to be rendered immediately as in-session guidance to the therapist.
    The main guidance_text is the primary clinical output. risk_guidance is a
    lower-priority parallel output that should be rendered separately (e.g. in
    a sidebar or at lower prominence) so it does not interrupt the primary flow.
    """

    guidance_text: str
    """Primary generated clinical guidance with inline [n] citation markers.

    Grounded in corpus passages matched to the detected session events and
    patient context. Empty string if retrieval returns no usable results.
    """

    risk_guidance: str = ""
    """Background risk-monitoring output from the passive risk pass.

    Grounded in risk_dimension_tags-matched passages. Lower priority than
    guidance_text. Empty string if no risk-relevant passages were retrieved
    or if PatientContext.enable_risk_pass is False.
    """

    detected_events: list[DetectedEvent] = field(default_factory=list)
    """Events identified by EventDetector that drove this retrieval."""

    citations: list = field(default_factory=list)
    """Citation objects for guidance_text. Type: list[models.Citation]."""

    risk_citations: list = field(default_factory=list)
    """Citation objects for risk_guidance. Type: list[models.Citation]."""

    clinical_cautions: list[str] = field(default_factory=list)
    """Explicit contraindication or precaution strings surfaced from retrieved
    passages' clinical_caution metadata field. Rendered prominently alongside
    any technique recommendations."""

    transcript_window: str = ""
    """The transcript window sent as the semantic query. Stored for logging."""

    query_filter_expression: str = ""
    """The Vertex AI Search AIP-160 filter expression used. Stored for debugging."""


# ---------------------------------------------------------------------------
# ASA pipeline output
# ---------------------------------------------------------------------------


@dataclass
class ASAHopResult:
    """Result of a single retrieval hop in the ASA multi-hop pipeline.

    Each hop targets one analysis_function value and produces its own
    set of retrieved passages and generated text. Hop results are injected
    as context into subsequent hops.
    """

    analysis_function: str
    """The analysis_function value this hop targeted."""

    generated_text: str
    """Generated section text for this analysis function."""

    citations: list = field(default_factory=list)
    """Citation objects for this hop's generated text. Type: list[models.Citation]."""

    passages_retrieved: int = 0
    """Number of passages retrieved for this hop."""


@dataclass
class ASAResponse:
    """Output of ASAPipeline.run() — the full post-session analysis report.

    Structured as named sections corresponding to ASA analysis functions.
    Empty string for a section means no relevant passages were retrieved
    for that function — the report is still returned, not failed.
    """

    autopsy_text: str = ""
    """Session autopsy: named clinical events, therapist response quality,
    missed opportunities. Grounded in session_autopsy hop results."""

    formulation_update_text: str = ""
    """Case formulation update: how session events revise the working formulation.
    Grounded in case_formulation_update hop results."""

    treatment_plan_text: str = ""
    """Treatment plan revision: evidence-based recommendations for next steps,
    modality adjustments, sequencing decisions. Grounded in
    treatment_plan_revision hop results, filtered to RCT and meta-analytic
    evidence matched to the patient population."""

    homework_text: str = ""
    """Homework recommendations: between-session assignments with rationale.
    Grounded in homework_resource hop results (asa_only passages,
    target_audience=patient documents, clinical presentation matched)."""

    risk_documentation_text: str = ""
    """Post-session risk documentation: safety plan review, duty-to-warn
    reasoning, level-of-care considerations. Grounded in
    risk_documentation hop results. Empty if no risk events occurred."""

    outcome_monitoring_text: str = ""
    """Outcome monitoring: interpretation of scores, trajectory review.
    Grounded in outcome_monitoring hop results. Empty if no outcome
    instruments are referenced in this session."""

    hop_results: list[ASAHopResult] = field(default_factory=list)
    """Individual hop results in execution order. Useful for debugging
    and for building custom report layouts."""

    all_citations: list = field(default_factory=list)
    """Union of all citations across all hops. Type: list[models.Citation].
    Individual hops also carry their own citations."""
