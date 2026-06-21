"""
Real-time analysis (RTA) pipeline.

Entry point: RTAPipeline.run(transcript) → RTAResponse
"""

from rta_prompt.rta.pipeline import RTAPipeline

__all__ = ["RTAPipeline"]
