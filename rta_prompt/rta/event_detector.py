"""
Lightweight in-session event classifier.

Converts a transcript window into a list of DetectedEvent objects, each
carrying a session_event_tags value and a risk_dimension_tags value for the
passive background risk pass.

Two-stage design:
  1. Heuristic pass — regex/keyword patterns that fire deterministically on
     surface signals (e.g. explicit SI language → crisis_escalation). Fast,
     no LLM call, confidence = 1.0.
  2. LLM pass — a Gemini-flash call for nuanced events that require reading
     clinical intent (e.g. rupture_withdrawal, transference_enactment). Only
     runs if the heuristic pass does not already account for the turn.

The LLM pass uses a constrained output format (JSON array of tag strings)
and the event tag enum directly in the prompt to limit hallucination to known
vocabulary values.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

import google.generativeai as genai

from rta_prompt.models import DetectedEvent

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Heuristic trigger patterns
# (tag → list of compiled regex patterns; any match fires the event)
# ---------------------------------------------------------------------------

_HEURISTIC_PATTERNS: dict[str, list[re.Pattern]] = {
    "crisis_escalation": [
        re.compile(
            r"\b(kill myself|suicid|end my life|don'?t want to live|want to die"
            r"|hurt myself|self.harm|cut myself|overdose|homicid|hurt (him|her|them))\b",
            re.IGNORECASE,
        ),
    ],
    "doorknob_disclosure": [
        re.compile(
            r"\b(before (you go|we end|we stop|i leave)|one more thing|"
            r"actually.{0,20}(wanted to|need to) tell you|oh and|by the way)\b",
            re.IGNORECASE,
        ),
    ],
    "boundary_testing": [
        re.compile(
            r"\b(can (i|we) (text|call|meet) (you|outside)|"
            r"give me your (number|contact|email)|"
            r"can we (go longer|meet more|add a session))\b",
            re.IGNORECASE,
        ),
    ],
    "decompensation": [
        re.compile(
            r"\b(can'?t breathe|heart racing|everything (went|going) (black|blank)|"
            r"not (here|real|present)|dissociat|panic|can'?t (think|focus|hear you))\b",
            re.IGNORECASE,
        ),
    ],
}

# ---------------------------------------------------------------------------
# Risk dimension heuristic patterns
# (risk_dimension_tags value → patterns)
# ---------------------------------------------------------------------------

_RISK_HEURISTIC_PATTERNS: dict[str, list[re.Pattern]] = {
    "suicide_ideation_chronic": [
        re.compile(
            r"\b(still think(ing)? about (death|dying|not being here)|"
            r"thoughts (keep coming back|haven'?t gone away)|"
            r"passive(ly)?.{0,20}(wish|want).{0,20}(dead|gone|not alive))\b",
            re.IGNORECASE,
        ),
    ],
    "self_harm_nonsuicidal": [
        re.compile(
            r"\b(cutting|burning|hitting myself|scratching|"
            r"urge to (cut|hurt)|NSS?I|non.?suicidal)\b",
            re.IGNORECASE,
        ),
    ],
    "substance_relapse_monitoring": [
        re.compile(
            r"\b(used (again|last week)|slipped|relaps|had a (drink|few drinks|hit)|"
            r"cravings (are back|getting worse))\b",
            re.IGNORECASE,
        ),
    ],
}

# ---------------------------------------------------------------------------
# LLM-detectable event tags (not reliably caught by heuristics)
# ---------------------------------------------------------------------------

_LLM_DETECTABLE_TAGS = [
    "rupture_withdrawal",
    "rupture_confrontation",
    "rupture_repair",
    "transference_enactment",
    "countertransference",
    "historical_disclosure",
    "flight_into_health",
    "resistance_avoidance",
    "intellectualization",
    "alliance_building",
    "psychoeducation",
    "exposure_in_session",
    "homework_review",
    "termination_process",
    "shame_activation",
    "somatic_activation",
    "therapist_self_disclosure",
    "avoidance_safety_behavior",
    "minority_stress_disclosure",
    "cultural_mismatch",
    "premature_termination_signal",
    "grief_loss_activation",
]


@dataclass
class EventDetectorConfig:
    """Configuration for EventDetector behaviour."""

    model_name: str = "gemini-1.5-flash"
    """Gemini model for the LLM detection pass. Flash is sufficient — the task
    is constrained classification, not open-ended reasoning."""

    temperature: float = 0.0
    """Deterministic output for the classification pass."""

    min_confidence: float = 0.6
    """LLM detections below this confidence threshold are discarded before
    they reach the searcher. Heuristic detections are always 1.0 and exempt."""

    window_turns: int = 6
    """Number of most-recent turns to include in the LLM classification window.
    The heuristic pass receives only the single most-recent patient turn."""

    skip_llm_if_heuristic_crisis: bool = True
    """If a heuristic crisis_escalation fires, skip the LLM pass entirely and
    return immediately. Avoids adding LLM latency when the priority is speed."""


class EventDetector:
    """Detects in-session clinical events from a transcript window.

    Usage:
        detector = EventDetector()
        events = detector.detect(transcript_window)
        risk_tags = detector.detect_risk_signals(transcript_window)
    """

    def __init__(self, config: Optional[EventDetectorConfig] = None) -> None:
        """
        Args:
            config: Behaviour settings. Uses EventDetectorConfig defaults if None.
        """
        self._config = config or EventDetectorConfig()
        self._client: Optional[genai.GenerativeModel] = None

    def detect(self, transcript_window: str) -> list[DetectedEvent]:
        """Run both heuristic and LLM detection passes on the transcript window.

        Heuristic pass runs first. If crisis_escalation fires and
        config.skip_llm_if_heuristic_crisis is True, the LLM pass is skipped.
        Otherwise both passes run; their results are merged and deduplicated
        (heuristic detections take precedence over LLM detections of the same tag).

        Args:
            transcript_window: The transcript string to analyse. Typically the
                last config.window_turns turns, but the full transcript is
                accepted — the method takes only what it needs.

        Returns:
            List of DetectedEvent objects with unique tags, in descending
            confidence order. Never returns duplicate tags.
        """
        raise NotImplementedError

    def detect_risk_signals(self, transcript_window: str) -> list[str]:
        """Run heuristic-only risk signal detection.

        Returns risk_dimension_tags values for the passive background risk pass.
        Deliberately fast — no LLM call. The heuristic patterns are intentionally
        broad (high recall, lower precision) for the risk dimension because a
        missed chronic risk signal is a higher-cost error than a false positive.

        Args:
            transcript_window: The transcript string to scan. The full session
                transcript is recommended to catch cumulative risk signals
                that span multiple turns.

        Returns:
            List of risk_dimension_tags values found (may be empty).
            Values match the risk_dimension_tags enum from the corpus schema.
        """
        raise NotImplementedError

    def _run_heuristic_pass(self, transcript_window: str) -> list[DetectedEvent]:
        """Apply _HEURISTIC_PATTERNS to the transcript window.

        Iterates all patterns for each tag. The first matching pattern for a
        tag produces one DetectedEvent; additional matching patterns for the
        same tag are ignored (one event per tag).

        Args:
            transcript_window: Transcript text to scan.

        Returns:
            List of DetectedEvent objects with source="heuristic", confidence=1.0.
        """
        raise NotImplementedError

    def _run_llm_pass(
        self,
        transcript_window: str,
        already_detected: set[str],
    ) -> list[DetectedEvent]:
        """Call the Gemini flash model to detect nuanced session events.

        Presents the transcript window and the full _LLM_DETECTABLE_TAGS enum to
        Gemini with instructions to return a JSON array of objects:
            [{"tag": "<tag>", "confidence": <0.0–1.0>, "trigger": "<span>"}, ...]

        Tags already in already_detected are excluded from the returned list
        (heuristic detections take precedence).

        Args:
            transcript_window: Recent transcript turns for the LLM to read.
            already_detected: Tag strings already found by the heuristic pass.
                              These are omitted from the LLM classification prompt
                              to avoid redundant output.

        Returns:
            List of DetectedEvent objects with source="llm". Entries with
            confidence < config.min_confidence are filtered out before return.

        Raises:
            RuntimeError: If the Gemini response cannot be parsed as valid JSON.
                          Callers should catch and fall back to heuristic-only results.
        """
        raise NotImplementedError

    def _build_llm_prompt(
        self,
        transcript_window: str,
        exclude_tags: set[str],
    ) -> str:
        """Build the classification prompt for the LLM pass.

        Includes:
          - Role context: the model is acting as a clinical supervisor
          - The transcript window
          - The complete list of detectable tags with brief definitions
          - The exact JSON output format required
          - Instruction to return an empty array if no events are detected

        Args:
            transcript_window: Transcript text for the model to classify.
            exclude_tags: Tags to omit from the prompt (already found by heuristics).

        Returns:
            Full prompt string.
        """
        raise NotImplementedError

    def _get_client(self) -> genai.GenerativeModel:
        """Lazy-initialize the Gemini model client.

        Returns:
            Configured GenerativeModel instance.
        """
        raise NotImplementedError
