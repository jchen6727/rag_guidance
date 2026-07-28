# INGESTION_PERFORMANCE.md — Speeding Up Metadata Tagging

**Problem (observed 2026-07-25):** one 216-page book = 921 chunks took ~5 hours,
apparently capped near ~10 requests/min. This bootstraps the options for making
ingestion faster, in rough order of effort-vs-payoff.
**Governed by:** `ORCHESTRATOR.md`. Related: `devlog.md` `#TODO(throughput)`.
**Last reconciled:** 2026-07-26.

---

## 0. First, find the actual bottleneck

The ~10 req/min ceiling is almost certainly the **Gemini free-tier quota**, not the
script. `batch_ingest.py` runs a serial loop with **no script-side rate limit**
(`generate_batch`'s optional delay is not used by the batch path). So:

- `#NOTE` The retry/backoff in `metadata_gen._call_gemini` will *look* like throttling
  if you are hitting `ResourceExhausted` (429s) — each 429 sleeps and retries, dragging
  throughput down. Run `scripts/check_llm.py` and check your tier's quota first.
- Token limits: `gemini-1.5-pro` handles these chunks (≤512 tokens) easily; a "token
  limit" symptom is more likely per-minute **token quota** on the free tier, not context size.

**Action before optimizing code:** move off the free tier (or raise quota). A paid tier
often lifts the per-minute ceiling 10–60× and may make the serial loop acceptable on its own.

---

## 1. Bounded concurrency (biggest code win, low risk)

Chunks are tagged **independently** today (`generate(chunk, context_window="")` passes no
cross-chunk context), so they can be processed in parallel. Replace the serial loop with a
bounded `ThreadPoolExecutor`:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed
with ThreadPoolExecutor(max_workers=settings.ingest_concurrency) as ex:
    futures = {ex.submit(metadata_gen.generate, c): c for c in chunks}
    for fut in as_completed(futures):
        c = futures[fut]; c.metadata = fut.result(); _append_metadata_checkpoint(...)
```

- Keep `max_workers` modest (e.g. 4–8) and **respect the quota** — combine with a token-bucket
  rate limiter so you approach, but don't exceed, your requests/min.
- The existing checkpoint (`ingestion_checkpoints/<doc_id>.jsonl`) already makes this crash-safe;
  writes must be guarded by a lock under concurrency.
- Expected: near-linear speedup up to the quota ceiling. 5 h → tens of minutes on a paid tier.

`#TODO(throughput)` — gated on the concurrency ceiling, which depends on §4.

## 2. Vertex AI Batch Prediction (best for large corpora)

For thousands of chunks, submit them as one batch job instead of N online calls:

- Write all prompts to a JSONL in GCS, submit a Vertex batch prediction, poll, collect results.
- Pros: highest throughput, lowest per-unit cost, no per-request rate dance.
- Cons: higher setup complexity; asynchronous (minutes-to-hours latency for the job).
- `metadata_gen.py` already flags this: ">1000 chunks, consider Vertex AI Batch Prediction."
- Natural fit alongside the `google-genai`/Vertex migration (`devlog.md#TODO(genai-migration)`).

## 3. Cheaper model for the easy fields

`gemini-1.5-flash` is much faster/cheaper and is fine for most tagging. Consider a two-pass
approach: flash for everything, pro only re-runs chunks that hit the safety fields
(`directionality != neutral`, non-empty `clinical_caution`). Set `GEMINI_MODEL_METADATA` to try.

## 4. The `ChunkProcessingStrategy` object (design — NEEDS INPUT)

You asked whether a "processing strategem" object is appropriate. **Yes**, if processing rules
vary. Proposed shape:

```python
class ChunkProcessingStrategy:
    max_concurrency: int          # 1 = serial; N = parallel
    context_scope: str            # "none" | "chapter" | "document"
    group_key: Callable[[Chunk], str] | None   # e.g. chunk.parent_section for chapter grouping
    model_name: str
    # → yields batches of chunks that may be processed concurrently
    def batches(self, chunks: list[Chunk]) -> Iterable[list[Chunk]]: ...
```

- `context_scope="none"` (today's behavior) → one big batch → full concurrency.
- `context_scope="chapter"` → chunks grouped by `parent_section`; concurrency **within** a group
  is limited if each chunk's prompt needs its siblings' context. Groups still run in parallel.

**The decision that gates this (for you):** *does good tagging need cross-chunk context?*
- If **no** (independent per chunk) — skip the object, just do §1 concurrency. Simplest.
- If **yes** (a chunk's tags depend on its chapter) — the strategy object earns its place, and it
  becomes the single place that encodes "what can run concurrently." This is also where a future
  "summarize the chapter first, then tag each chunk with that summary" flow would live.

Recommendation: **start with §1 (independent, concurrent)**; introduce the strategy object only
when/if a real context-dependence requirement appears. Don't build the abstraction speculatively.

---

## Suggested order

1. Confirm/raise the Gemini quota (paid tier) — may be enough on its own.
2. Add `scripts/check_llm.py` to your pre-ingest routine (already added) to catch quota/model issues early.
3. Implement §1 bounded concurrency + a rate limiter (small, high payoff).
4. Revisit §2 (Vertex batch) once the corpus is large or the migration lands.
5. Only build §4's strategy object if chapter-context tagging is actually required.

## Staleness note
Re-verify the quota/rate assumptions against the current Gemini tier before acting. Reconcile
with `devlog.md` if the `genai-migration` or `processing-strategem` decisions are made.
