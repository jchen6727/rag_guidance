"""
Retrieval package — Vertex AI Search query wrapper and optional LLM re-ranker.

Typical usage:
    searcher = CorpusSearcher(project_id, location, engine_id)
    results = searcher.search(query, top_k=8, filters=SearchFilter(domain="cardiology"))

    # Optional: improve ranking with a Gemini re-ranker
    reranker = LLMReranker()
    results = reranker.rerank(query, results, top_n=5)
"""

from retrieval.searcher import CorpusSearcher, SearchFilter
from retrieval.reranker import LLMReranker

__all__ = ["CorpusSearcher", "SearchFilter", "LLMReranker"]
