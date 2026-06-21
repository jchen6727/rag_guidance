"""
ASA-scoped Vertex AI Search wrapper.

Wraps CorpusSearcher for the after-session analysis (ASA) pipeline. Unlike
RTASearcher, which applies a static pre-filter once per session, ASASearcher
issues targeted retrievals for each analysis function hop, varying the filter
expression per hop.

Key differences from RTASearcher:
  - corpus_scope filter is lifted — asa_only documents are accessible
  - target_audience = patient IS accessible (for homework_resource hops only)
  - analysis_function field routes each hop to a different document class
  - evidence_base and patient_population filters are applied for treatment-
    matching hops (treatment_plan_revision, prognosis_trajectory)
  - time_horizon filter is applied for longitudinal planning hops

All hard safety filters still apply:
  - training_level_required gate (same as RTA)
  - target_audience = patient is allowed ONLY when analysis_function is
    homework_resource — enforced inside search_by_function(), not by the caller

Filter expressions use AIP-160 syntax. See rta_prompt/rta/searcher.py for
syntax notes.
"""

from __future__ import annotations

import logging
from typing import Optional

from retrieval.searcher import CorpusSearcher
from models import SearchResult
from rta_prompt.models import PatientContext

logger = logging.getLogger(__name__)

# analysis_function values that may surface target_audience=patient documents.
# All other functions must exclude patient-facing materials.
_PATIENT_FACING_ALLOWED_FUNCTIONS = {"homework_resource"}

# analysis_function values that should apply evidence_base + patient_population filters.
_EVIDENCE_FILTERED_FUNCTIONS = {
    "treatment_plan_revision",
    "prognosis_trajectory",
    "case_formulation_update",
}

# analysis_function values that apply time_horizon filtering.
_TIME_FILTERED_FUNCTIONS = {
    "treatment_plan_revision",
    "prognosis_trajectory",
    "referral_coordination",
    "termination_planning",
}


class ASASearcher:
    """Issues analysis-function-routed queries for the ASA multi-hop pipeline.

    Instantiated once per ASA run. Exposes search_by_function() which builds
    the appropriate filter expression for each hop automatically.

    Usage:
        searcher = ASASearcher(
            patient_context=ctx,
            project_id=settings.gcp_project_id,
            location=settings.gcp_location,
            engine_id=settings.vertex_search_engine_id,
        )
        autopsy_results = searcher.search_by_function(
            query=transcript,
            analysis_function="session_autopsy",
            top_k=10,
        )
        plan_results = searcher.search_by_function(
            query=autopsy_context,
            analysis_function="treatment_plan_revision",
            evidence_base=["rct_primary", "rct_moderator", "meta_analytic"],
            top_k=8,
        )
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
            patient_context: Static session metadata. Provides therapeutic_modality,
                clinical_presentation, session_phase, patient_population, and
                clinician_training_level for filter construction.
            project_id: GCP project ID.
            location: Vertex AI Search engine location.
            engine_id: Search engine resource ID.
        """
        self._context = patient_context
        self._base_searcher = CorpusSearcher(
            project_id=project_id,
            location=location,
            engine_id=engine_id,
        )

    def search_by_function(
        self,
        query: str,
        analysis_function: str,
        top_k: int = 10,
        evidence_base: Optional[list[str]] = None,
        time_horizon: Optional[str] = None,
        outcome_measure_tags: Optional[list[str]] = None,
    ) -> list[SearchResult]:
        """Execute a single ASA retrieval hop routed by analysis_function.

        Builds the appropriate filter expression for the given function:
          - analysis_function filter is always applied
          - corpus_scope is not restricted (asa_only allowed)
          - target_audience = patient is allowed only for homework_resource
          - evidence_base filter applied if provided or if function is in
            _EVIDENCE_FILTERED_FUNCTIONS and PatientContext has no override
          - patient_population filter applied for evidence-filtered functions
          - time_horizon filter applied for time-filtered functions
          - training_level_required gate always applied
          - therapeutic_modality and clinical_presentation filters applied
            unless analysis_function is "outcome_monitoring" (instrument
            guidance is presentation-agnostic)

        Args:
            query: Semantic query string. For later hops, this typically includes
                text from earlier hop outputs to provide context continuity.
            analysis_function: One of the analysis_function controlled vocabulary
                values (session_autopsy, treatment_plan_revision, homework_resource,
                case_formulation_update, outcome_monitoring, risk_documentation,
                referral_coordination, prognosis_trajectory, supervision_preparation,
                termination_planning).
            top_k: Number of passages to retrieve.
            evidence_base: Override for the evidence_base filter. If None,
                defaults are applied based on the function (see above).
            time_horizon: Override for the time_horizon filter. If None,
                defaults are applied based on the function.
            outcome_measure_tags: For outcome_monitoring hops — restrict to
                passages tagged with these specific instrument acronyms.

        Returns:
            Ranked list of SearchResult objects. May be shorter than top_k if
            the filter is too narrow for current corpus coverage.

        Raises:
            ValueError: If analysis_function is not a recognised value.
                Callers should handle this by logging and skipping the hop.
        """
        raise NotImplementedError

    def search_outcome_instruments(
        self,
        instrument_tags: list[str],
        top_k: int = 6,
    ) -> list[SearchResult]:
        """Retrieve passages tagged with specific outcome measurement instruments.

        Convenience wrapper around search_by_function for the outcome_monitoring
        hop. Filters to chunks where outcome_measure_tags contains one of the
        requested instrument acronyms.

        Args:
            instrument_tags: Instrument acronyms as they appear in the
                outcome_measure_tags controlled vocabulary (e.g. ["PHQ-9", "PCL-5"]).
            top_k: Number of passages to retrieve.

        Returns:
            SearchResult objects for the requested instruments.
        """
        raise NotImplementedError

    def _build_asa_filter(
        self,
        analysis_function: str,
        evidence_base: Optional[list[str]],
        time_horizon: Optional[str],
        outcome_measure_tags: Optional[list[str]],
    ) -> str:
        """Build the complete AIP-160 filter expression for an ASA hop.

        Assembles clauses for:
          - analysis_function (required)
          - therapeutic_modality (optional — omitted for outcome_monitoring)
          - clinical_presentation (optional — omitted for outcome_monitoring)
          - patient_population (applied for evidence-filtered functions)
          - evidence_base (applied for evidence-filtered functions)
          - time_horizon (applied for time-filtered functions)
          - training_level_required (always applied)
          - target_audience (patient excluded unless homework_resource)
          - outcome_measure_tags (applied for outcome_monitoring hops)

        Args:
            analysis_function: The analysis function for this hop.
            evidence_base: Evidence type filter values, or None.
            time_horizon: Time horizon filter value, or None.
            outcome_measure_tags: Instrument tag filter values, or None.

        Returns:
            AIP-160 filter expression string.
        """
        raise NotImplementedError

    def _default_evidence_base(self, analysis_function: str) -> Optional[list[str]]:
        """Return the default evidence_base filter for a given analysis function.

        For treatment_plan_revision and prognosis_trajectory: restrict to
        empirical evidence types (rct_primary, rct_moderator, meta_analytic).
        For case_formulation_update: include expert_clinical alongside empirical.
        For all others: no evidence_base filter (all types admitted).

        Args:
            analysis_function: The hop's analysis function value.

        Returns:
            List of evidence_base values to filter on, or None for no filter.
        """
        raise NotImplementedError

    def _default_time_horizon(self, analysis_function: str) -> Optional[str]:
        """Return the default time_horizon filter for a given analysis function.

        treatment_plan_revision → near_term or short_term (next 1–4 sessions)
        prognosis_trajectory    → treatment_course or post_termination
        referral_coordination   → any (referral decisions are not time-bound)
        termination_planning    → post_termination

        Args:
            analysis_function: The hop's analysis function value.

        Returns:
            time_horizon value, or None if no time filter applies.
        """
        raise NotImplementedError
