"""
Expert-persona prompt assembly for the RAG generation step.

Loads persona templates from config/prompt_config.yaml and combines them with:
  - Retrieved chunk passages (numbered for citation)
  - The user query
  - Domain-specific system instructions

The final prompt is structured so Gemini is instructed to:
  1. Adopt the expert persona for the specified domain
  2. Answer ONLY from the retrieved passages
  3. Cite each factual claim inline as [n] referencing the numbered passage list

See config/prompt_config.yaml for the template format.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from models import SearchResult

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG_PATH = Path("config/prompt_config.yaml")


class PromptBuilder:
    """
    Assembles the full generation prompt from templates + retrieved results.

    Usage:
        builder = PromptBuilder(config_path=Path("config/prompt_config.yaml"))
        prompt = builder.build(
            query="What are the first-line treatments for systolic heart failure?",
            domain="cardiology",
            results=search_results,
        )
    """

    def __init__(self, config_path: Optional[Path] = None) -> None:
        """
        Args:
            config_path: Path to the YAML prompt configuration file.
                         Defaults to config/prompt_config.yaml relative to cwd.
        """
        self._config_path = config_path or _DEFAULT_CONFIG_PATH
        self._config: dict = {}
        self._load_config()

    def build(
        self,
        query: str,
        domain: str,
        results: list[SearchResult],
        corpus_name: str = "RAG corpus",
    ) -> str:
        """Assemble the complete generation prompt.

        Sections (in order):
          1. System persona block (domain-matched from config)
          2. Retrieval instruction block
          3. Numbered retrieved passages
          4. User query

        Args:
            query: The user's question or instruction.
            domain: Specialty domain string used to select the persona template.
                    Falls back to the "default" persona if domain not found.
            results: Retrieved SearchResult objects to use as grounding context.
                     Passed to _format_retrieved_chunks() for numbered formatting.
            corpus_name: Human-readable corpus name inserted into the retrieval
                         instruction template.

        Returns:
            Full prompt string ready to send to Gemini.
        """
        raise NotImplementedError

    def _select_persona(self, domain: str) -> dict:
        """Look up the persona config block for the given domain.

        Looks for an exact match in the "personas" section of the YAML config.
        Falls back to the "default" persona if no exact match is found.

        Args:
            domain: Domain string (e.g. "cardiology", "oncology").

        Returns:
            Dict with keys: "system", "description", "style_notes".

        Raises:
            KeyError: If neither the domain nor "default" persona is configured.
        """
        raise NotImplementedError

    def _format_retrieved_chunks(self, results: list[SearchResult]) -> str:
        """Format retrieved chunks as a numbered passage list.

        Each passage is formatted as:
            [1] Source: <title>, <chapter>, pp. <page_start>–<page_end>
            <chunk text>

        The [n] numbers correspond to inline citation markers in the response.

        Args:
            results: List of SearchResult objects in display order
                     (typically already ranked by relevance).

        Returns:
            Formatted multi-line string of numbered passages.
        """
        raise NotImplementedError

    def _load_config(self) -> None:
        """Read and parse the YAML config file into self._config.

        Raises:
            FileNotFoundError: If the config file does not exist.
            yaml.YAMLError: If the file is not valid YAML.
        """
        raise NotImplementedError

    def list_available_domains(self) -> list[str]:
        """Return the list of domain names that have configured persona templates.

        Returns:
            List of domain strings from the "personas" section of the config,
            excluding the "default" entry.
        """
        raise NotImplementedError
