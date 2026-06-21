"""
Real-time analysis (RTA) pipeline orchestrator.

Entry point for in-session guidance. Called once per speaker turn (or on a
configurable stride). Takes the rolling session transcript and returns
generated clinical guidance grounded in the psychotherapy corpus.

Pipeline stages (designed to run within a live clinical exchange):

  1. Transcript window selection — extract the last N turns as the query
  2. Event detection — heuristic pass first, then LLM pass concurrently with
     retrieval start (see implementation note on concurrency below)
  3. Retrieval — RTASearcher issues the main event-filtered query; the passive
     risk pass runs in parallel if PatientContext.enable_risk_pass is True
  4. Optional re-ranking — LLMReranker if PatientContext.enable_reranker is True
  5. Prompt assembly — PromptBuilder with the psychotherapy_rta persona
  6. Generation — ResponseGenerator streaming from first passages
  7. Citation building — CitationBuilder resolves page metadata

Concurrency note: stages 2 and 3 partially overlap. The heuristic pass
completes synchronously and immediately seeds the retrieval filter. The LLM
detection pass and the search call can be issued as concurrent async tasks —
the search result is post-filtered by any LLM detections that complete before
the response arrives. This module exposes a synchronous interface; the async
implementation is internal.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from config.settings import settings
from generation.citation_builder import CitationBuilder
from generation.prompt_builder import PromptBuilder
from generation.response_gen import ResponseGenerator
from models import SearchResult
from retrieval.reranker import LLMReranker
from rta_prompt.models import (
    DetectedEvent,
    PatientContext,
    RTAResponse,
    SessionTranscript,
)
from rta_prompt.rta.event_detector import EventDetector, EventDetectorConfig
from rta_prompt.rta.searcher import RTASearcher

logger = logging.getLogger(__name__)

_DEFAULT_WINDOW_TURNS = 6
_RTA_PERSONA_DOMAIN = "psychotherapy_rta"


class RTAPipeline:
    """Orchestrates the full RTA pipeline for a single transcript update.

    Instantiated once per session (not per turn). Heavy clients
    (CorpusSearcher, EventDetector's Gemini client, ResponseGenerator's
    Gemini client) are lazy-initialized on first use and reused across turns.

    Usage:
        ctx = PatientContext(
            therapeutic_modality=["CBT"],
            clinical_presentation=["PTSD"],
            session_phase="mid_treatment",
        )
        pipeline = RTAPipeline(patient_context=ctx)
        response = pipeline.run("Therapist: Let's begin the exposure...\nPatient: I can't.")
    """

    def __init__(
        self,
        patient_context: PatientContext,
        prompt_config_path: Optional[Path] = None,
        window_turns: int = _DEFAULT_WINDOW_TURNS,
    ) -> None:
        """
        Args:
            patient_context: Static session metadata. Must not change across
                calls during a session — the RTASearcher pre-filter is compiled
                from it at init time.
            prompt_config_path: Path to prompt_config.yaml. Defaults to the
                project-level config/prompt_config.yaml.
            window_turns: Number of most-recent turns to extract as the query
                window. Defaults to 6 (approximately 3 exchange pairs).
        """
        self._context = patient_context
        self._window_turns = window_turns

        self._searcher = RTASearcher(
            patient_context=patient_context,
            project_id=settings.gcp_project_id,
            location=settings.gcp_location,
            engine_id=settings.vertex_search_engine_id,
        )
        self._event_detector = EventDetector(
            config=EventDetectorConfig(
                model_name=settings.gemini_model_reranker,
                window_turns=window_turns,
            )
        )
        self._prompt_builder = PromptBuilder(config_path=prompt_config_path)
        self._response_generator = ResponseGenerator(
            model_name=settings.gemini_model_generation,
        )
        self._citation_builder = CitationBuilder()
        self._reranker: Optional[LLMReranker] = (
            LLMReranker(model_name=settings.gemini_model_reranker)
            if patient_context.enable_reranker
            else None
        )

    def run(self, transcript: str) -> RTAResponse:
        """Execute the full RTA pipeline on the current transcript state.

        This is the primary external interface. Accepts the full rolling
        transcript as a plain string and returns an RTAResponse.

        Pipeline:
          1. Extract the query window from the transcript
          2. Run event detection (heuristic pass always; LLM pass unless
             heuristic already detected crisis_escalation with skip_llm=True)
          3. Run main retrieval with static + event filters
          4. Run passive risk retrieval in parallel (if enabled)
          5. Optionally re-rank main results
          6. Assemble prompt and generate guidance text
          7. Build citations for both guidance and risk outputs

        Args:
            transcript: The full session transcript up to and including the
                current turn, as a plain text string. Speaker turns should be
                formatted consistently (e.g. "Therapist: ...\nPatient: ...")
                but freeform text is also accepted.

        Returns:
            RTAResponse with guidance_text, risk_guidance, detected_events,
            citations, and clinical_cautions populated.
        """
        raise NotImplementedError

    def _extract_window(self, transcript: str) -> str:
        """Extract the query window from the transcript.

        Splits the transcript by newline and returns the last
        self._window_turns lines as the query string. If the transcript has
        fewer lines than the window size, returns the full transcript.

        Args:
            transcript: Full session transcript.

        Returns:
            Transcript window string (the most recent turns).
        """
        raise NotImplementedError

    def _retrieve_main(
        self,
        window: str,
        detected_events: list[DetectedEvent],
    ) -> list[SearchResult]:
        """Retrieve corpus passages for the main clinical guidance path.

        Calls RTASearcher.search() then optionally applies LLMReranker if
        self._reranker is not None.

        Args:
            window: Transcript window as the semantic query.
            detected_events: Events from the detector for the event filter.

        Returns:
            Ranked SearchResult list. May be empty if no results pass filters.
        """
        raise NotImplementedError

    def _retrieve_risk(self, transcript: str) -> list[SearchResult]:
        """Retrieve corpus passages for the passive risk-monitoring path.

        Calls EventDetector.detect_risk_signals() on the full transcript (not
        just the window), then calls RTASearcher.search_risk() with the
        resulting tags.

        Args:
            transcript: Full session transcript (not just the window).

        Returns:
            SearchResult list for the risk path. Empty list if risk pass is
            disabled or no risk tags were detected.
        """
        raise NotImplementedError

    def _extract_clinical_cautions(self, results: list[SearchResult]) -> list[str]:
        """Collect clinical_caution metadata strings from retrieved passages.

        Reads the clinical_caution field from each SearchResult's metadata.
        Deduplicates across results. Cautions are surfaced alongside guidance
        text so they are not buried in citation footnotes.

        Args:
            results: Retrieved SearchResult objects from the main path.

        Returns:
            Deduplicated list of clinical caution strings. May be empty.
        """
        raise NotImplementedError

    def _generate_guidance(
        self,
        window: str,
        results: list[SearchResult],
    ) -> tuple[str, list]:
        """Assemble prompt and call ResponseGenerator for the main guidance path.

        Args:
            window: Transcript window used as the query context.
            results: Retrieved passages for the main path.

        Returns:
            Tuple of (generated_text, attributions).
        """
        raise NotImplementedError

    def _generate_risk_guidance(
        self,
        window: str,
        risk_results: list[SearchResult],
    ) -> tuple[str, list]:
        """Assemble prompt and call ResponseGenerator for the risk monitoring path.

        Uses a risk-specific prompt tone: passive, monitoring-focused, not
        alarming. Only called if risk_results is non-empty.

        Args:
            window: Transcript window for context.
            risk_results: Retrieved passages from the risk path.

        Returns:
            Tuple of (generated_risk_text, risk_attributions).
        """
        raise NotImplementedError
