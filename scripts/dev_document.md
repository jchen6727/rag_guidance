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
