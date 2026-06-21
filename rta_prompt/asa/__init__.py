"""
After-session analysis (ASA) pipeline.

Entry point: ASAPipeline.run(transcript) → ASAResponse
"""

from rta_prompt.asa.pipeline import ASAPipeline

__all__ = ["ASAPipeline"]
