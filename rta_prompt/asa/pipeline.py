"""
After-session analysis (ASA) pipeline orchestrator.

Runs after session close. Takes the full session transcript and patient history
and produces a multi-section post-session analysis report structured around
ASA analysis functions.

Pipeline: sequential multi-hop retrieval where each hop targets one
analysis_function value and its output is injected into subsequent hop queries.

Hop sequence (fixed order; individual hops skipped if not applicable):

  Hop 1 — session_autopsy
      Query: full transcript
      Purpose: identify and name clinical events, evaluate therapist response,
               surface missed opportunities
      Output: injected into all subsequent hop queries as context

  Hop 2 — case_formulation_update
      Query: transcript + autopsy output
      Purpose: update working case formulation with this session's events
      Output: injected into treatment_plan_revision query

  Hop 3 — treatment_plan_revision
      Query: transcript + autopsy output + formulation update
      Purpose: evidence-based recommendations for next steps (RCT and
               meta-analytic evidence filtered to patient population)
      Output: independent; not injected downstream

  Hop 4 — risk_documentation (conditional)
      Condition: crisis_escalation or risk-related events in autopsy output,
                 OR risk_events list passed explicitly by caller
      Query: transcript
      Purpose: post-session safety plan review, duty-to-warn, level-of-care
      Output: independent

  Hop 5 — homework_resource (conditional)
      Condition: treatment plan output references homework, OR
                 PatientContext.session_phase is mid_treatment or late_treatment
      Query: transcript + treatment plan output
      Purpose: retrieve patient-facing materials for next session
      Output: independent

  Hop 6 — outcome_monitoring (conditional)
      Condition: instrument acronyms detected in transcript
      Query: instrument tags detected in transcript
      Purpose: interpretation guidance for outcome scores discussed in session
      Output: independent

  Final generation pass — one ResponseGenerator call per non-empty hop,
      each with its own PromptBuilder persona. Results assembled into ASAResponse.

Conditional hops are evaluated by _should_run_*() methods which parse the
transcript and prior hop outputs. Skipped hops produce empty strings in the
final ASAResponse.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Optional

from config.settings import settings
from generation.citation_builder import CitationBuilder
from generation.prompt_builder import PromptBuilder
from generation.response_gen import ResponseGenerator
from models import SearchResult
from rta_prompt.models import (
    ASAHopResult,
    ASAResponse,
    PatientContext,
)
from rta_prompt.asa.searcher import ASASearcher

logger = logging.getLogger(__name__)

# Outcome instrument acronyms to detect in the transcript for hop 6.
# Matched case-insensitively; extend as new instruments are added to the corpus.
_OUTCOME_INSTRUMENT_PATTERN = re.compile(
    r"\b(PHQ-?9|GAD-?7|PCL-?5|BDI-?II|DASS-?21|HAM-?D|ORS|SRS|C-?SSRS|"
    r"Columbia|AUDIT|MDQ|HCL-?32|OQ-?45|CORE-?OM|IES-?R)\b",
    re.IGNORECASE,
)

_ASA_PERSONA_DOMAIN = "psychotherapy_asa"
_RTA_PERSONA_DOMAIN = "psychotherapy_rta"


class ASAPipeline:
    """Orchestrates the full ASA multi-hop pipeline.

    Instantiated once per ASA run (i.e. once after each session). Unlike
    RTAPipeline, this is not reused across sessions — instantiate fresh for
    each post-session analysis.

    Usage:
        ctx = PatientContext(
            therapeutic_modality=["DBT"],
            clinical_presentation=["BPD"],
            session_phase="mid_treatment",
            patient_population=["adult_general"],
        )
        pipeline = ASAPipeline(patient_context=ctx)
        response = pipeline.run(
            transcript=full_transcript_text,
            patient_history="Prior sessions: ...",
        )
        print(response.autopsy_text)
        print(response.treatment_plan_text)
    """

    def __init__(
        self,
        patient_context: PatientContext,
        prompt_config_path: Optional[Path] = None,
    ) -> None:
        """
        Args:
            patient_context: Static session metadata. Provides filter axes for
                all retrieval hops and controls which conditional hops run.
            prompt_config_path: Path to prompt_config.yaml. Defaults to the
                project-level config/prompt_config.yaml.
        """
        self._context = patient_context

        self._searcher = ASASearcher(
            patient_context=patient_context,
            project_id=settings.gcp_project_id,
            location=settings.gcp_location,
            engine_id=settings.vertex_search_engine_id,
        )
        self._prompt_builder = PromptBuilder(config_path=prompt_config_path)
        self._response_generator = ResponseGenerator(
            model_name=settings.gemini_model_generation,
        )
        self._citation_builder = CitationBuilder()

    def run(
        self,
        transcript: str,
        patient_history: str = "",
        risk_events: Optional[list[str]] = None,
    ) -> ASAResponse:
        """Execute the full ASA multi-hop pipeline.

        This is the primary external interface. Accepts the complete session
        transcript and optional patient history, runs all applicable hops in
        sequence, and returns a structured ASAResponse.

        Hops 1–3 always run. Hops 4–6 run conditionally based on transcript
        content analysis and session context.

        Args:
            transcript: Full session transcript as a plain text string.
            patient_history: Optional summary of prior sessions, current
                formulation, and outcome score trajectory. If provided, this
                is injected into hop 1 (session_autopsy) and hop 2
                (case_formulation_update) queries to provide longitudinal context.
            risk_events: Optional list of risk-related events to force-trigger
                the risk_documentation hop (hop 4). If None, the hop runs only
                if crisis or risk signals are detected in the transcript or
                autopsy output. Pass an explicit list to guarantee risk
                documentation when the caller has independent risk knowledge.

        Returns:
            ASAResponse with populated section strings and citation lists.
            Sections for skipped hops are empty strings. The hop_results list
            contains ASAHopResult objects for all hops that ran, in order.
        """
        raise NotImplementedError

    def _run_autopsy_hop(
        self,
        transcript: str,
        patient_history: str,
    ) -> ASAHopResult:
        """Execute hop 1: session_autopsy.

        Retrieves session_autopsy-function passages. Query is the full
        transcript plus patient history (if provided). Generates a session
        autopsy section: named clinical events, evaluation of therapist
        responses, missed opportunities.

        Args:
            transcript: Full session transcript.
            patient_history: Prior context string. May be empty.

        Returns:
            ASAHopResult for the session_autopsy function.
        """
        raise NotImplementedError

    def _run_formulation_hop(
        self,
        transcript: str,
        autopsy_output: str,
    ) -> ASAHopResult:
        """Execute hop 2: case_formulation_update.

        Query enriched with autopsy output to provide session event context.
        Generates an updated case formulation section reflecting this session's
        clinical events.

        Args:
            transcript: Full session transcript.
            autopsy_output: Generated text from the autopsy hop.

        Returns:
            ASAHopResult for the case_formulation_update function.
        """
        raise NotImplementedError

    def _run_treatment_plan_hop(
        self,
        transcript: str,
        autopsy_output: str,
        formulation_output: str,
    ) -> ASAHopResult:
        """Execute hop 3: treatment_plan_revision.

        Evidence-base filter restricts retrieval to rct_primary, rct_moderator,
        and meta_analytic chunks matched to patient_population. Query enriched
        with both autopsy and formulation outputs for full longitudinal context.

        Args:
            transcript: Full session transcript.
            autopsy_output: Generated text from the autopsy hop.
            formulation_output: Generated text from the formulation hop.

        Returns:
            ASAHopResult for the treatment_plan_revision function.
        """
        raise NotImplementedError

    def _run_risk_hop(self, transcript: str) -> ASAHopResult:
        """Execute hop 4: risk_documentation.

        Retrieves risk_documentation-function passages. Uses the full transcript
        as the query to capture the complete risk context from the session.
        Appropriate persona tone: structured, documentation-focused, non-alarming.

        Args:
            transcript: Full session transcript.

        Returns:
            ASAHopResult for the risk_documentation function.
        """
        raise NotImplementedError

    def _run_homework_hop(
        self,
        transcript: str,
        treatment_plan_output: str,
    ) -> ASAHopResult:
        """Execute hop 5: homework_resource.

        Retrieves homework_resource-function passages with target_audience=patient
        allowed (the only ASA hop that surfaces patient-facing materials).
        Filtered to clinical_presentation and therapeutic_modality match.
        Query enriched with treatment plan output to align homework with the
        recommended next steps.

        Args:
            transcript: Full session transcript.
            treatment_plan_output: Generated text from the treatment plan hop.

        Returns:
            ASAHopResult for the homework_resource function.
        """
        raise NotImplementedError

    def _run_outcome_hop(self, instrument_tags: list[str]) -> ASAHopResult:
        """Execute hop 6: outcome_monitoring.

        Retrieves outcome_monitoring-function passages filtered to the specific
        instrument acronyms detected in the session transcript. Generates
        interpretation guidance for the scores discussed in session.

        Args:
            instrument_tags: Instrument acronyms detected in the transcript
                by _detect_outcome_instruments().

        Returns:
            ASAHopResult for the outcome_monitoring function.
        """
        raise NotImplementedError

    def _generate_section(
        self,
        analysis_function: str,
        query: str,
        results: list[SearchResult],
    ) -> tuple[str, list]:
        """Assemble prompt and call ResponseGenerator for a single ASA section.

        Uses the psychotherapy_asa persona from prompt_config.yaml. The query
        is passed as the "user query" and the retrieved passages are the
        grounding context.

        Args:
            analysis_function: The analysis function being generated. Used to
                select the appropriate persona sub-variant if configured.
            query: The semantic query string for this hop (used as user query
                in the prompt — provides the specific question for this section).
            results: Retrieved passages for this hop.

        Returns:
            Tuple of (generated_section_text, attributions).
        """
        raise NotImplementedError

    def _should_run_risk_hop(
        self,
        transcript: str,
        autopsy_output: str,
        forced_risk_events: Optional[list[str]],
    ) -> bool:
        """Determine whether the risk_documentation hop should run.

        Returns True if any of:
          - forced_risk_events is non-None and non-empty
          - crisis-related keywords appear in the transcript
          - the autopsy output contains risk-related language

        Args:
            transcript: Full session transcript.
            autopsy_output: Generated autopsy section text.
            forced_risk_events: Explicit risk event list from the caller.

        Returns:
            True if the risk hop should execute.
        """
        raise NotImplementedError

    def _should_run_homework_hop(self, treatment_plan_output: str) -> bool:
        """Determine whether the homework_resource hop should run.

        Returns True if treatment plan output references homework or between-
        session assignments, or if session_phase is mid_treatment or later.

        Args:
            treatment_plan_output: Generated treatment plan section text.

        Returns:
            True if the homework hop should execute.
        """
        raise NotImplementedError

    def _detect_outcome_instruments(self, transcript: str) -> list[str]:
        """Find outcome instrument acronyms mentioned in the session transcript.

        Used to decide whether to run hop 6 and to seed the outcome_measure_tags
        filter for that hop.

        Args:
            transcript: Full session transcript.

        Returns:
            Deduplicated list of instrument acronyms found (uppercase normalised).
            Empty list if no instruments are mentioned.
        """
        raise NotImplementedError

    def _build_hop_query(self, *text_parts: str) -> str:
        """Concatenate non-empty text parts into a single hop query string.

        Used to build enriched queries for later hops by combining the
        transcript with outputs from earlier hops.

        Args:
            *text_parts: Strings to join. Empty strings are omitted.

        Returns:
            Single string with non-empty parts joined by double newlines.
        """
        raise NotImplementedError
