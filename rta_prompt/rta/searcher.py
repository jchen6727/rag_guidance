"""
RTA-scoped Vertex AI Search wrapper.

Wraps CorpusSearcher with the hard pre-filters required for real-time retrieval:
  - corpus_scope != "asa_only"       (exclude post-session-only documents)
  - target_audience != "patient"     (exclude patient-facing materials)
  - therapeutic_modality match       (static; from PatientContext)
  - clinical_presentation match      (static; from PatientContext)
  - session_phase match              (static; from PatientContext)
  - training_level_required gate     (static; from PatientContext.clinician_training_level)

Dynamic event filters (session_event_tags) are added per call by passing
detected events. The passive risk pass runs as a separate search call keyed
on risk_dimension_tags.

Filter expressions use AIP-160 syntax. Array-type schema fields registered
as key type in Vertex AI Search use: field: ANY("v1", "v2")
String equality uses: field = "value"
Negation uses: NOT field = "value"

See retrieval/searcher.py for the base CorpusSearcher implementation.
"""

from __future__ import annotations

import logging
from typing import Optional

from retrieval.searcher import CorpusSearcher, SearchFilter
from models import SearchResult
from rta_prompt.models import DetectedEvent, PatientContext

logger = logging.getLogger(__name__)

# Vertex AI Search training level ordering — used to build the upper-bound filter.
# Only retrieve chunks whose required level is <= the clinician's level.
_TRAINING_LEVEL_ORDER = [
    "generalist",
    "supervised_trainee",
    "post_licensure",
    "specialist_trained",
]


class RTASearcher:
    """Issues RTA-scoped queries against the psychotherapy corpus.

    Instantiated once per session with the patient context. The static pre-filter
    expression is compiled at init time and reused for every search call, so the
    per-turn cost is only the dynamic event-filter extension.

    Usage:
        searcher = RTASearcher(
            patient_context=ctx,
            project_id=settings.gcp_project_id,
            location=settings.gcp_location,
            engine_id=settings.vertex_search_engine_id,
        )
        results = searcher.search(query, detected_events, top_k=8)
        risk_results = searcher.search_risk(risk_tags, top_k=4)
    """

    def __init__(
        self,
        patient_context: PatientContext,
        project_id: str,
        location: str,
        engine_id: str,
    ) -> None:
        """
        Args:
            patient_context: Static session metadata. Drives the static pre-filter
                expression compiled at init. Must remain constant for the session.
            project_id: GCP project ID, passed to CorpusSearcher.
            location: Vertex AI Search engine location.
            engine_id: Search engine resource ID.
        """
        self._context = patient_context
        self._base_searcher = CorpusSearcher(
            project_id=project_id,
            location=location,
            engine_id=engine_id,
        )
        self._static_filter = self._build_static_filter()

    def search(
        self,
        query: str,
        detected_events: list[DetectedEvent],
        top_k: int = 8,
    ) -> list[SearchResult]:
        """Execute the main RTA retrieval pass.

        Combines the static pre-filter (patient context) with the dynamic event
        filter (detected session events) into a single AIP-160 expression.
        Falls back to the static-filter-only query if detected_events is empty
        (retrieves broadly relevant guidance rather than event-specific guidance).

        Args:
            query: Semantic query string. Typically the last N turns of the
                transcript — the transcript window that drove event detection.
            detected_events: Events from EventDetector.detect(). Used to extend
                the filter with session_event_tags constraints.
            top_k: Number of results to return.

        Returns:
            Ranked list of SearchResult objects. May be shorter than top_k if
            the filter expression is too narrow for the current corpus coverage.
        """
        raise NotImplementedError

    def search_risk(
        self,
        risk_tags: list[str],
        top_k: int = 4,
    ) -> list[SearchResult]:
        """Execute the passive background risk-monitoring retrieval pass.

        Runs independently of the main event path. Uses risk_dimension_tags as
        the primary filter. The static pre-filter (excluding asa_only and
        patient-facing documents) still applies, but the modality/presentation
        filter is intentionally omitted — risk monitoring guidance should not be
        restricted to the patient's primary modality.

        Args:
            risk_tags: risk_dimension_tags values detected by
                EventDetector.detect_risk_signals(). If empty, this method
                returns an empty list without querying the DataStore.
            top_k: Number of risk-relevant passages to retrieve.

        Returns:
            SearchResult objects matched to risk_dimension_tags. Returns []
            if risk_tags is empty.
        """
        raise NotImplementedError

    def _build_static_filter(self) -> str:
        """Build the AIP-160 pre-filter expression from the patient context.

        Components (all ANDed):
          - NOT corpus_scope = "asa_only"
          - NOT target_audience = "patient"
          - therapeutic_modality: ANY(...) if context has modalities
          - clinical_presentation: ANY(...) if context has presentations
          - session_phase = <phase> if phase is not "any"
          - training_level_required filter from clinician_training_level

        Returns:
            AIP-160 filter expression string. Never empty — at minimum the
            corpus_scope and target_audience guards are always present.
        """
        raise NotImplementedError

    def _build_event_filter(self, detected_events: list[DetectedEvent]) -> str:
        """Build the AIP-160 session_event_tags filter from detected events.

        Filters to chunks whose session_event_tags field contains at least one
        of the detected event tags. Chunks tagged "none" are included as a
        fallback when no events were detected.

        Args:
            detected_events: Events from the detector. If empty, returns a
                filter that includes the "none" tag (reference/background chunks).

        Returns:
            AIP-160 fragment string for the event filter, e.g.:
            'session_event_tags: ANY("rupture_withdrawal", "rupture_repair", "none")'
        """
        raise NotImplementedError

    def _build_training_level_filter(self, clinician_level: str) -> str:
        """Build an AIP-160 training_level_required upper-bound filter.

        Only retrieve chunks appropriate for the clinician's level. A generalist
        should not receive specialist-certification-required technique guidance.

        Uses the ordering defined in _TRAINING_LEVEL_ORDER to include all
        levels at or below the clinician's level.

        Args:
            clinician_level: The PatientContext.clinician_training_level value.

        Returns:
            AIP-160 fragment string, e.g.:
            'training_level_required: ANY("generalist", "supervised_trainee")'
            Returns "" if clinician_level is not in _TRAINING_LEVEL_ORDER
            (logs a warning; no filter applied).
        """
        raise NotImplementedError
