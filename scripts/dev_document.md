# scripts/ — Developer Guide (Internal-Facing)

**Audience:** technical auditors / architects.
**Scope:** operational entry points — GCP provisioning, batch ingest, purge, and verification helpers.
**Governed by:** `ORCHESTRATOR.md`. Ingest correctness depends on `config/` (schema) and `ingestion/` (pipeline).
**Last reconciled:** 2026-07-20.

---

## Feedback log (newest first)

<!-- Developers: prepend dated feedback here. -->

*(no developer feedback recorded yet)*

`<!-- ▲ unprocessed above this line ▲ -->`

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

- **#NOTE(schema-wired)** `setup_vertex_search.py` registers whatever `settings.metadata_schema_path` points at — today `config/metadata_schema.json` (37 fields). So the **DataStore schema and the ingestion tags are consistent with each other but with the 37-field schema, not `rta_v1.json`.**
- **#TODO(schema-migration)** If/when the code repoints to `rta_v1.json`, `setup_vertex_search.py` must re-register the new field set and the array-field filterable list changes (`rta_v1.json` array fields: `therapeutic_modality, clinical_presentation, session_event_tags, applies_when, risk_dimension_tags, patient_population, clinical_measure_tags, technique_tags, clinical_caution`). This is a breaking, purge-and-re-ingest change.

## 4. Safety notes

- `purge_datastore.py` is the only destructive script and is gated behind `--confirm`. **Never run it without `--dry-run` first**, and never as a casual "reset." It maps to the human-in-the-loop confirmation the orchestrator requires for hard-to-reverse actions.
- `verify_datastore.sh` contains an editable hardcoded `PROJECT_ID` — treat as a scratch helper, not a committed source of truth; do not rely on its defaults.
- These scripts touch external cloud state (create datastores, upload PDFs, index/delete documents). Per `ORCHESTRATOR`, outward-facing actions are confirmed before running unless explicitly authorized.

## 5. Review points (kept current)

- **#TODO** First provisioning + ingest not yet run from this environment (`.env` not verified here).
- **#TODO(schema-migration)** `setup_vertex_search.py` re-registration is a downstream step of the config-layer migration decision.
- **#NOTE** `verify_datastore.sh` hardcoded IDs should be parameterized or the script marked scratch-only.

---

## Staleness note

- Re-verify §3 (which schema is registered) against `settings.metadata_schema_path` before trusting any DataStore contents.
- The order dependency (§2) and purge safety (§4) are invariant; re-verify script flags against the files if a script changes.
- Reconcile if a newer `CHANGELOG.md` entry exists than the date above.
