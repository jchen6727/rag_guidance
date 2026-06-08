"""
Generation package — expert-persona prompt assembly, Gemini response generation,
and citation building.

End-to-end usage:
    builder = PromptBuilder(config_path=Path("config/prompt_config.yaml"))
    prompt = builder.build(query, domain="cardiology", results=search_results)

    generator = ResponseGenerator()
    response = generator.generate(prompt, results=search_results, query=query, domain=domain)
    # response.text contains inline [n] markers; response.citations is the reference list
"""

from generation.prompt_builder import PromptBuilder
from generation.response_gen import ResponseGenerator
from generation.citation_builder import CitationBuilder

__all__ = ["PromptBuilder", "ResponseGenerator", "CitationBuilder"]
