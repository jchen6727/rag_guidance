# devlog.md — Engineering Change Log & Open Decisions

Central record of non-trivial changes, the decisions behind them, and items that
need human input before they can be implemented sensibly. Governed by
`ORCHESTRATOR.md`; uses its dated-tag convention (`#TAG(anchor)?[YYYY-MM-DD]`).

Newest entry on top.

---

## 2026-07-27 — Four decisions implemented

All four `2026-07-26` open decisions were answered and built. Verification:
`107 passed` (was 97; +10 strategy tests), every touched module compiles,
`bash -n` clean on `preflight_check.sh`, CI YAML valid. The 17 failing tests are
the unchanged pre-existing stubs (`test_retrieval.py`, one `test_chunker`).

- `#DONE(genai-migration)[2026-07-27]` **Decision 1 — migrate to `google-genai` + Vertex/ADC only.**
  - `ingestion/metadata_gen.py`: `from google import genai`; `_get_client()` builds
    `genai.Client(vertexai=True, project=GCP_PROJECT_ID, location=GCP_LOCATION)`;
    `_call_gemini()` uses `client.models.generate_content(...)`. Dropped the `api_key`
    ctor param, `GEMINI_API_KEY` usage, and `import os`.
  - `scripts/check_llm.py`: rewritten to the Vertex client; definitive check is a 1-token
    `generate_content`. `--list` uses `client.models.list()`.
  - `config/settings.gemini_api_key` marked DEPRECATED (retained, unused).
  - `requirements.txt`, `ingestion/requirements.txt`, `.github/workflows/ci.yml`:
    `google-generativeai` → `google-genai>=1.0.0`. `_gcp_logging` auth hint updated to ADC.
  - `#NOTE(vertex-region)[2026-07-27]` The Vertex Gemini client uses the **raw** `GCP_LOCATION`
    (a compute region / "global"), unlike Discovery Engine (multi-region). If a model isn't
    served in that region, `generate` fails — `scripts/check_llm.py` catches it up front.
  - `#NOTE(model-id)[2026-07-27]` Default model is still `gemini-1.5-pro` (`settings.gemini_model_metadata`).
    You flagged that Google is retiring older Gemini models — update `GEMINI_MODEL_METADATA`
    in `.env` (e.g. a `gemini-2.x`) and confirm with `check_llm.py` before a big run. Not
    changed by me because it's a config/cost choice.
  - `#TODO(genai-migration-querypath)[2026-07-27]` The **stubbed query path** still contains
    old-SDK *usage* (`genai.GenerativeModel`, `genai.configure`) inside `retrieval/reranker.py`,
    `generation/response_gen.py`, `rta_prompt/rta/event_detector.py`. Their import lines were
    swapped to `from google import genai` so the repo stays installable with only `google-genai`
    (bodies raise `NotImplementedError`, so the old calls never run), but the method bodies must
    be rewritten to `genai.Client(vertexai=True)` + `client.models.generate_content(...)` when
    the query path is implemented. Tracked here so it isn't forgotten.

- `#DONE(processing-strategem)[2026-07-27]` **Decision 2 — chapter context + pluggable framework.**
  - New `ingestion/processing_strategy.py`: `ProcessingStrategy` base + `IndependentStrategy`
    (full concurrency, no context) and `ChapterContextStrategy` (default: groups consecutive
    chunks by `parent_section`, tags each with chapter heading + preceding in-chapter text,
    runs chapters concurrently / chunks-within-chapter sequentially). Register new strategies
    in `_STRATEGIES` — the ingest loop doesn't change.
  - `scripts/batch_ingest.py`: `_generate_all_metadata()` runs units via a bounded
    `ThreadPoolExecutor`, threads chapter context into `metadata_gen.generate(chunk, context)`,
    writes the checkpoint under a lock (crash-safe), reuses cached chunks, logs progress. New
    flags `--strategy` / `--concurrency`; settings `INGEST_STRATEGY` (default `chapter`) /
    `INGEST_CONCURRENCY` (default 4). Tests: `tests/test_processing_strategy.py` (10).
  - `#NOTE(context-content)[2026-07-27]` The chapter-context *content* (heading + preceding
    text, 1500-char budget) is a heuristic. Whether it improves tag quality is empirical —
    tune `context_char_budget` / the `context_for` text once you can eval tags. Not blocking.

- `#DONE(sh-to-rest)[2026-07-27]` **Decision 4 — route `.sh` checks through curl/REST.**
  Adopted as standing policy. `preflight_check.sh` now uses REST for the programmatic checks:
  project (`cloudresourcemanager projects.get`), billing (`cloudbilling …/billingInfo`),
  and enabled APIs (`serviceusage services.list`, paginated via a `python3`/`urllib` helper).
  A single ADC token is acquired once (§1) and reused (incl. the existing IAM check). Kept on
  gcloud per policy: `gcloud auth …` (auth), `gcloud config get-value` (local, no REST
  equivalent), and `gcloud services enable` / IAM binding commands in *fix* text (guidance).

- `#DONE(ci-cd)[2026-07-27]` **Decision 3 — CI on PRs-to-main + manual; CI IAM.**
  `.github/workflows/ci.yml`: `pull_request` → `main` + `workflow_dispatch`; runs the schema
  parse gate + the stable cloud-free tests (now incl. strategy tests). **CI IAM:** the current
  job needs **no GCP credentials** (cloud-free). See "CI IAM" below for the future
  integration-CI grant.

### CI IAM (for a future live-integration job)

The stable CI needs nothing. If/when a job actually runs `batch_ingest` against a **test**
project, provision a service account via **Workload Identity Federation** (no exported keys)
with least-privilege roles:

| Role | Why |
|---|---|
| `roles/discoveryengine.editor` | create/import/list/delete DataStore documents |
| `roles/storage.objectAdmin` (scoped to the test bucket) | stage PDFs + chunk JSONL |
| `roles/aiplatform.user` | Vertex Gemini `generate_content` |
| `roles/serviceusage.serviceUsageViewer` | preflight's services check |

Keep this off the default PR gate (it costs money and needs secrets); make it a manual /
labeled workflow. `#TODO(ci-integration)[2026-07-27]` — build only when a test project exists.

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

## Open decisions — ALL RESOLVED 2026-07-27 (implemented; see the 2026-07-27 entry at top)

All four answered and built. Remaining follow-ups are non-blocking notes in the 2026-07-27
entry: `#NOTE(model-id)` (pick a current Gemini model in `.env`), `#NOTE(context-content)`
(tune chapter-context heuristic once tags can be evaluated), `#TODO(ci-integration)` (live CI
only when a test project exists). Original answers retained below for the record.

1. **Gemini backend:** migrate to `google-genai` + Vertex/ADC only, or keep the API-key path as
   a fallback? (`#TODO(genai-migration)`)
   answer: decision to migrate to google-genai + Vertex/ADC only
2. **Chapter context:** do metadata tags need cross-chunk context, or is per-chunk independent
   tagging acceptable? (`#TODO(processing-strategem)` — determines the concurrency ceiling)
   answer: use chapter context, acceptable to limit concurrency ceiling to handle this process, have framework in proper directory so that
3. **CI trigger:** PRs-to-main + manual (recommended), or a `release/` path trigger?
   (`#TODO(ci-cd)`)
   PRs-to-main + manual for CI trigger. Establish any additional IAM permissions that may be needed.
4. **`.sh` → REST policy:** adopt as standing policy? (`#TODO(sh-to-rest)`)
   adopt as standing policy, 
