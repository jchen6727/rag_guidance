# rag_guidance

A Python RAG system providing clinical guidance to psychotherapists trained in **CBT, DBT, and IPT**. Two modes: **RTA** (real-time, in-session) and **ASA** (after-session analysis). Pipeline: corpus ingestion → Vertex AI Search indexing → prompt engineering → grounded, cited guidance.

**Status:** ingest path implemented; query path (`retrieval/`, `generation/`, `rta_prompt/`) still stubbed.

Start with `BOOTSTRAP.md` for the authoritative reading order, then `CLAUDE.md`. Known cross-file inconsistencies are tracked in `DISCREPANCIES.md`.
