# scripts/ — Developer Guide (Internal-Facing)

**Audience:** technical auditors / architects.
**Scope:** operational entry points — GCP provisioning, batch ingest, purge, and verification helpers.
**Governed by:** `ORCHESTRATOR.md`. Ingest correctness depends on `config/` (schema) and `ingestion/` (pipeline).
**Last reconciled:** 2026-07-20.

---

## Feedback log (newest first)

<!-- Developers: prepend dated feedback here. -->
#TODO[2026-07-25]

`preflight_check.sh` does not validate the entire IAM permission list against google cloud (for instance, `google-genai`) -- implement entire IAM permission list for the end to end of the software project.

additionally, Google is limiting deprecated LLM calls, for instance, script seems to fail when using gemini < 3.x , see if there is a method of doing a simple query to check the LLM specified is available.

begin documentation of the CI/CD process--especially ensuring that changes do not break functionality--, should a test run be triggered on pushes to a specific `release` directory? or a manual run?

notes from test_ingestion.md (project root):
1. 
    need to load the `.env` from the terminal after creating it:

    ```
    set -a
    source .env  # or: export $(grep -v '^#' .env | xargs)
    set +a
    ```

2.
    preflight_check.sh does not handle gemini (or generative ai) checks 
    additionally, internal calls should be migrated to vertex instead of generative ai, as google-generativeai is deprecated for google-genai

3.
    ensure for any .sh script that `gcloud` commands are converted to more stable curl & REST API equivalents if possible. this should be tracked as a overall project note/design decisions for any future code work.

4.
    clarify -- check that the --dry-run (if it generates tags as indicated by it comment `splits and tags but uploads nothing`) preserves them so we do not need additional API calls (cost) from --dry-run to actual run, or note that it does not generate tags in the test_ingestion.md documentation

5.
    ingestion is single threaded and takes about 5 hours for 921 chunks, it seems rate limited on script end to 10 requests per minute though it appears that the service allows significantly more requests at a time than that. additionally, it seems like it may be hitting a token limit as well. Look into ways to improve this (concurrent or batch calls?) and set up a bootstrap document for best method of improving ingestion speed.
    Addtionally, looking forward, if chunk processing needs context from chapter (thus preventing concurrent processing of all chunks from a chapter), implement some framework that allows for a chunking or processing "strategem" -- would an object be appropriate for this ("processing_strategem")?

6. 
    additionally, ingestion does not print anything during long ingestion without `verbosity`, but then prints too much with `verbosity`, have some default behavior that indicates some level of progress > for instance x/921 chunks processed.

7.
    `ingestion/metadata_gen.py` contains hard coded LLM prompts (e.g. `parts[0]` on line 160 and `guidance` on line 209). Implement some method to expose this to a user (for instance, in the `config/rta_v1.json` each `tag` has a `description` field, could this be used, or describe the best `.json` or `.env` location for prompt instructions to be placed. Can implement a place to store the LLM prompt string?

8.
    noted crash on attempting ingestion -- remarks after running
    python scripts/batch_ingest.py --file corpus/APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf --verbose
    which failed while attempting to upload to the Vertex AI Search data store. implement region fix. Of note: `config/settings.py` contains logic to derive the appropriate data store location `self.gcs_datastore_region`, check that these API calls can be "routed" via settings attributes rather than adding additional `.env` rules.

9.
    implement some checkpointing method in the scripts/batch_ingest.py to preserve state of `.jsonl` or any already parsed information in case of crash.

`<!-- ▲ unprocessed above this line ▲ -->`

**Resolution `#DONE[2026-07-27]`:** the `#TODO[2026-07-25]` block above is fully actioned — see `devlog.md` (2026-07-26 + 2026-07-27 entries) for per-item status. 2026-07-26: region fix (8), `.env` autoload (1), progress (6), checkpoint+resume (9, 4), preflight IAM/API (lead + 2), `check_llm.py` (lead), prompt externalization (7). 2026-07-27 (the four decisions): `google-genai`+Vertex/ADC migration (2), pluggable chapter-context processing framework `ingestion/processing_strategy.py` + concurrency (5), `.sh`→REST in `preflight_check.sh` (3), CI on PRs-to-main + manual with CI-IAM doc (lead). Non-blocking follow-ups tracked in `devlog.md`: pick a current Gemini model id, tune chapter-context heuristic, live integration CI.

---

## 1. Scripts inventory

| Script | Purpose | Destructive? | Key flags |
|---|---|---|---|
| `preflight_check.sh` | Verifies gcloud/login, project, billing, required APIs, IAM before provisioning; reports **all** failures with fix commands | No | — |
| `setup_vertex_search.py` | Creates the Discovery Engine DataStore and **registers the metadata schema** (converts `metadata_schema.json` → Discovery Engine `json_schema`) | No (creates) | `--dry-run` |
| `batch_ingest.py` | Runs the full pipeline over `corpus/`; skips manifest'd files unless `--force`; single-file mode via `--file` | No (writes index) | `--dry-run`, `--force`, `--file` |
| `purge_datastore.py` | Deletes documents from the DataStore | **YES** | `--confirm` (required), `--dry-run`, `--doc-id`, `--reingest` |
| `verify_context.py` | Validates project context + IAM permissions for the active identity | No | — |
| `verify_datastore.sh` | Fetches the registered DataStore schema (has a hardcoded `PROJECT_ID`/`DATA_STORE_ID` to edit) | No | edit vars in file |
| `inspect_chunks.py` | **Local** extract→chunk→(optional Gemini tag) preview; writes `ingestion_review/*.review.md` + `.chunks.jsonl`. No cloud. | No | `--no-metadata`, `--limit`, `--out`, `--verbose` |
| `review_datastore.py` | Lists indexed docs + their tags from the DataStore (CLI counterpart to the Cloud console) | No | `--doc-id`, `--limit`, `--count-only`, `--out`, `--verbose` |
| `check_llm.py` | Verifies the configured Gemini model is reachable + supports generateContent (catches retired-model failures pre-ingest) | No | `--model`, `--list`, `--verbose` |
| `_gcp_logging.py` | Shared helper: `setup_logging(verbose)` + `describe_google_error()` (actionable Google API error hints) | — | imported by the scripts |

## 2. Order dependency (must hold)

```
preflight_check.sh  →  setup_vertex_search.py (register schema)  →  batch_ingest.py
                                                                        │
                                              purge_datastore.py --confirm (only to reset)
```

- **Schema registration precedes first import.** Chunks indexed before the schema is registered silently drop unregistered fields (`CLAUDE.md`, `summary.md §4.4`). `setup_vertex_search.py` must run — and succeed — first.
- **Region is immutable** after DataStore creation; `GCP_LOCATION` must be correct before `setup_vertex_search.py`.
- Schema changes after ingestion require `purge_datastore.py --confirm` then full re-ingest.

## 3. Schema coupling (the cross-cut to watch)

- `#DONE(schema-wired)[2026-07-20]` `setup_vertex_search.py` registers whatever `settings.metadata_schema_path` points at — now `config/rta_v1.json` (23 fields). Verified: `_create_discoveryengine_schema(rta_v1)` emits 23 fields with the 10 array fields (`therapeutic_modality, clinical_presentation, session_event_tags, applies_when, risk_dimension_tags, patient_population, clinical_measure_tags, technique_tags, clinical_caution, keywords`) marked `indexable`, and `directionality` (scalar enum) indexable+searchable. DataStore schema and ingestion tags are now mutually consistent on `rta_v1.json`.
- `#NOTE[2026-07-20]` `_INFORMATIONAL_ONLY_FIELDS = {"missingness"}` and some docstrings still name `metadata_schema.json` — harmless (no `missingness` field in `rta_v1.json`; the function reads `settings.metadata_schema_path` at runtime), but a low-priority cleanup `#TODO(setup-docstrings)[2026-07-20]`.

## 4. Safety notes

- `purge_datastore.py` is the only destructive script and is gated behind `--confirm`. **Never run it without `--dry-run` first**, and never as a casual "reset." It maps to the human-in-the-loop confirmation the orchestrator requires for hard-to-reverse actions.
- `verify_datastore.sh` contains an editable hardcoded `PROJECT_ID` — treat as a scratch helper, not a committed source of truth; do not rely on its defaults.
- These scripts touch external cloud state (create datastores, upload PDFs, index/delete documents). Per `ORCHESTRATOR`, outward-facing actions are confirmed before running unless explicitly authorized.

## 5. Review points (kept current)

- `#TODO[2026-07-20]` First provisioning + ingest not yet run from this environment (`.env` not verified here).
- `#DONE(schema-migration)[2026-07-20]` `setup_vertex_search.py` now registers `rta_v1.json` (reads `settings.metadata_schema_path`). Any DataStore already created against the old 37-field schema must be purged + re-provisioned.
- `#NOTE[2026-07-20]` `verify_datastore.sh` hardcoded IDs should be parameterized or the script marked scratch-only.

---

## Staleness note

- Re-verify §3 (which schema is registered) against `settings.metadata_schema_path` before trusting any DataStore contents.
- The order dependency (§2) and purge safety (§4) are invariant; re-verify script flags against the files if a script changes.
- Reconcile if a newer `CHANGELOG.md` entry exists than the date above.
