# devlog.md — Engineering Change Log & Open Decisions

Central record of non-trivial changes, the decisions behind them, and items that
need human input before they can be implemented sensibly. Governed by
`ORCHESTRATOR.md`; uses its dated-tag convention (`#TAG(anchor)?[YYYY-MM-DD]`).

Newest entry on top.

---

## 2026-07-26 — Response to `scripts/dev_document.md` change requests

Source: the `#TODO[2026-07-25]` feedback block at the top of `scripts/dev_document.md`
(9 numbered notes + 3 lead items). Status of each below. Verification: `57 passed`
on the schema/loader/metadata suite after all changes; every touched script
byte-compiles; `bash -n` clean on `preflight_check.sh`.

### Implemented

- `#DONE(region-fix)[2026-07-26]` **(note 8 — the crash).** Root cause: runtime
  clients used the raw `GCP_LOCATION` (`us-central1`) against the **global**
  Discovery Engine endpoint, while `setup_vertex_search.py` correctly derived the
  multi-region. Routed everything through settings, as requested (no new `.env` rules):
  - `config/settings.py`: added `discovery_engine_location` (derives `us`/`eu`/`global`
    from `gcp_location`) and `discovery_engine_endpoint` (regional endpoint or None).
  - `ingestion/indexer.py`: `VertexSearchIndexer` takes `api_endpoint` and applies it
    via `ClientOptions`.
  - `scripts/batch_ingest.py`, `scripts/purge_datastore.py`, `scripts/review_datastore.py`:
    construct clients from the two new settings.
  - `scripts/setup_vertex_search.py`: `_client_options()` now delegates to the shared
    setting (deduped).
  - `scripts/preflight_check.sh` §5: derives the DE region (accepts compute regions,
    maps `us-central1`→`us`) instead of rejecting them.
  - Verified: `us-central1` → `us` + `us-discoveryengine.googleapis.com`; `global` → None.

- `#DONE(env-autoload)[2026-07-26]` **(note 1).** `config/settings.py` now loads `.env`
  at import (`_load_dotenv`, `override=False`, python-dotenv with a plain-parser
  fallback). No more `set -a; source .env` needed. `ENV_FILE` overrides the path.

- `#DONE(progress)[2026-07-26]` **(note 6).** `batch_ingest.py` logs `…metadata X/N (Y%)`
  at the default level (~every 5%), so a long run shows progress without `--verbose`.

- `#DONE(checkpoint)[2026-07-26]` **(notes 9 + 4).** `batch_ingest.py` writes each chunk's
  metadata to `ingestion_checkpoints/<doc_id>.jsonl` as it is generated (crash-safe), and
  a re-run **resumes** from it — no re-paying for already-tagged chunks. A `--dry-run`
  populates the same checkpoint, so its tags are reused by the real run (answers note 4).
  `test_ingestion.md §3d` updated to state dry-run *does* call Gemini and how resume works.

- `#DONE(preflight-iam)[2026-07-26]` **(lead item + note 2, partial).** `preflight_check.sh`:
  added `generativelanguage.googleapis.com` to required APIs and expanded the IAM list to
  the full end-to-end set (documents import/list/get/delete, GCS objects/buckets). A `warn()`
  helper was added for advisories.

- `#DONE(model-check)[2026-07-26]` **(lead item — "check the LLM is available").**
  New `scripts/check_llm.py`: verifies the configured Gemini model is reachable and supports
  `generateContent`; `--list` shows usable models. Catches the "gemini < 3.x retired" failure
  in one call instead of mid-ingest.

- `#DONE(prompt-config)[2026-07-26]` **(note 7).** Hard-coded prompt strings moved out of
  `ingestion/metadata_gen.py` into `config/ingestion_prompt.yaml` (system preamble, output/
  closing instructions, guidance bullets). The enum vocabulary stays generated from the schema
  (never duplicated). Missing/invalid file → built-in defaults, so a bad edit can't break
  ingestion. **Recommendation for future prompt edits:** edit the YAML, not the Python.

### Flagged — need input before sensible implementation

- `#TODO(genai-migration)[2026-07-26]` **(notes 2 & 3 — `google-generativeai` → `google-genai`
  + Vertex).** The bundled `google-generativeai` is deprecated. Recommend migrating
  `metadata_gen` to the unified `google-genai` SDK with `vertexai=True` + ADC (drops the
  API-key path, unifies with the Discovery Engine auth, VPC-friendly). **Decision needed:**
  (a) Vertex-only (ADC, enterprise) or (b) keep the Gemini Developer API key as a dev/offline
  fallback? This changes `metadata_gen._get_client/_call_gemini`, `settings` (GEMINI_API_KEY),
  `check_llm.py`, and the preflight API (`aiplatform` vs `generativelanguage`). Well-scoped,
  ~half a day; not started because the a/b choice affects the whole design.

- `#TODO(sh-to-rest)[2026-07-26]` **(note 3 — `.sh` gcloud → curl/REST).** Adopted as a
  **design principle** (recorded below in "Standing decisions"). Recommend *selective*
  conversion: keep `gcloud auth`/`gcloud services enable` (user-facing, stable) but prefer
  REST for programmatic checks (preflight already calls the IAM `testIamPermissions` RPC via
  curl). Not a bulk rewrite. Confirm you want this as policy.

- `#TODO(throughput)[2026-07-26]` **(note 5 — 5 h for 921 chunks).** Bootstrap written:
  `ingestion/INGESTION_PERFORMANCE.md`. The current loop is serial with no script-side rate
  limit — the ~10 req/min ceiling is the **Gemini free-tier quota**, not the code. Biggest wins:
  a paid tier + bounded concurrency (ThreadPoolExecutor) or Vertex Batch Prediction. **Decision
  needed** before implementing concurrency: see `processing_strategem` below.

- `#TODO(processing-strategem)[2026-07-26]` **(note 5, second half).** You asked whether a
  `processing_strategem` object is appropriate for "does this chunk need chapter context."
  **Yes — recommend a `ChunkProcessingStrategy` object** (see INGESTION_PERFORMANCE.md §4).
  **Clinical/technical question for you:** does good tagging need cross-chunk (chapter) context,
  or is each chunk independent? Today `metadata_gen.generate(chunk, context_window="")` passes
  *no* context, so chunks are already independent → safe to parallelize fully. If you want
  chapter context, that caps concurrency to per-chapter and the strategy object earns its keep.
  Not implemented pending your answer.

- `#TODO(ci-cd)[2026-07-26]` **(lead item — CI/CD).** Starter added:
  `.github/workflows/ci.yml` (schema parse gate + the 57 stable tests). **Decision needed on
  trigger:** you floated "push to a `release` directory" vs manual. Recommendation: run on
  **PRs to `main` + manual dispatch** (standard; catches regressions before merge). A
  path-filtered "release directory" trigger is non-standard and easy to bypass — not
  recommended as the primary gate. See "Open decisions" below.

- `#TODO(iam-completeness)[2026-07-26]` The expanded preflight IAM list is derived from the
  code paths, not yet validated against a live grant. Confirm against an actual service account
  once one is provisioned.

---

## Standing decisions (project-wide)

- `#NOTE(sh-rest-policy)[2026-07-26]` **Prefer REST/curl over `gcloud` for programmatic checks**
  in shell scripts where it improves portability/stability; keep `gcloud` for interactive auth
  and one-shot enablement. (Pending your confirmation — `#TODO(sh-to-rest)`.)
- `#NOTE(prompt-location)[2026-07-26]` Hand-authored LLM prompt text lives in
  `config/ingestion_prompt.yaml`; generated vocabulary stays in the schema. Do not hard-code
  prompt strings in `metadata_gen.py` again.
- `#NOTE(de-routing)[2026-07-26]` All Discovery Engine calls route through
  `settings.discovery_engine_location` / `discovery_engine_endpoint`. Never pass the raw
  `gcp_location` to a Discovery Engine client.

## Open decisions (need a one-line answer from you)

1. **Gemini backend:** migrate to `google-genai` + Vertex/ADC only, or keep the API-key path as
   a fallback? (`#TODO(genai-migration)`)
2. **Chapter context:** do metadata tags need cross-chunk context, or is per-chunk independent
   tagging acceptable? (`#TODO(processing-strategem)` — determines the concurrency ceiling)
3. **CI trigger:** PRs-to-main + manual (recommended), or a `release/` path trigger?
   (`#TODO(ci-cd)`)
4. **`.sh` → REST policy:** adopt as standing policy? (`#TODO(sh-to-rest)`)
