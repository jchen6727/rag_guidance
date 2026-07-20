# scripts/ — Agentic Instructions (Internal-Facing)

**Audience:** automated (agentic) developers. Full operational detail.
**Precondition:** ingest `/ORCHESTRATOR.md`; confirm the schema decision in `config/agentic_document.md §2` before provisioning or ingesting.
**Last reconciled:** 2026-07-20.

---

## Handoff log (newest first)

### 2026-07-20 — orchestrator bootstrap
- Created this triad. No scripts changed.
- Verified script interfaces: `setup_vertex_search.py --dry-run`; `batch_ingest.py --dry-run|--force|--file`; `purge_datastore.py --confirm|--dry-run|--doc-id|--reingest`.
- **Next agent should:** run `preflight_check.sh`, then the first-ingest runbook (`ingestion/agentic_document.md §2`) starting with `--dry-run`.
- Left open: first provisioning/ingest not yet performed; `.env` unverified.

`<!-- ▲ latest handoff above ▲ -->`

---

## 1. Guardrails (read before running anything)

1. **`purge_datastore.py` is destructive.** Do not run it without explicit user authorization for *this* run. Always `--dry-run` first. Approval to purge once does not carry to the next time.
2. **All these scripts touch external cloud state** (create datastores, upload PDFs, index/delete). These are outward-facing actions — confirm before executing unless durably authorized.
3. **Provisioning order is load-bearing:** `preflight_check.sh` → `setup_vertex_search.py` → `batch_ingest.py`. Do not import before the schema is registered.
4. **`GCP_LOCATION` is immutable post-creation.** Verify it before `setup_vertex_search.py`.
5. Whatever schema the code loads is what gets registered *and* what chunks are tagged against — keep them consistent (`config/agentic_document.md §2`).

## 2. Commands (canonical)

```bash
# Preflight (surfaces every failure at once with fix commands)
scripts/preflight_check.sh

# Provision (dry-run then execute). Registers the metadata schema.
PYTHONPATH=. python scripts/setup_vertex_search.py --dry-run
PYTHONPATH=. python scripts/setup_vertex_search.py

# Verify identity/permissions and the registered schema
PYTHONPATH=. python scripts/verify_context.py
# (edit PROJECT_ID / DATA_STORE_ID first) scripts/verify_datastore.sh

# Ingest (dry-run then execute)
PYTHONPATH=. python scripts/batch_ingest.py --dry-run
PYTHONPATH=. python scripts/batch_ingest.py

# Reset (DESTRUCTIVE — authorization + dry-run required)
PYTHONPATH=. python scripts/purge_datastore.py --confirm --dry-run
PYTHONPATH=. python scripts/purge_datastore.py --confirm
```

## 3. First-ingest checklist (this environment)

- [ ] Schema decision recorded (`config/agentic_document.md §2` + `config/CHANGELOG.md`).
- [ ] `.env` populated (`cp .env.example .env`; set `GCP_PROJECT_ID`, `GCS_BUCKET_NAME`, `VERTEX_SEARCH_DATASTORE_ID`, `VERTEX_SEARCH_ENGINE_ID`, `GCP_LOCATION`).
- [ ] `preflight_check.sh` passes.
- [ ] `setup_vertex_search.py` succeeded (schema registered; array fields filterable).
- [ ] `batch_ingest.py --dry-run` reviewed (chunk counts, metadata-failure rate, front-matter leakage).
- [ ] Real ingest run; import success/failure counts captured; `.ingestion_manifest.json` written.
- [ ] If this was an Option-A mechanics test, label the index disposable in the handoff log.

> **Note on running from here:** an interactive GCP login is out of band for the agent. If `preflight_check.sh` reports a login/auth failure, ask the user to run the suggested `gcloud auth login` themselves (they can type `! <command>` in the session so its output lands in the conversation).

## 4. Task queue

- **#TODO** Perform the first provisioning + dry-run once `.env` and the schema decision are in place.
- **#NOTE** `verify_datastore.sh` has hardcoded `PROJECT_ID="jchen-6727"` / placeholder `DATA_STORE_ID` — parameterize or treat as scratch; do not trust its defaults.
- **#TODO(schema-migration)** When config repoints to `rta_v1.json`, re-run `setup_vertex_search.py` to re-register; this is breaking (purge + re-ingest).

## 5. Update-on-exit checklist

- [ ] Append a dated Handoff log entry with exactly what ran and the resulting counts/errors.
- [ ] Record the schema used and any destructive action in `config/CHANGELOG.md`.
- [ ] Flip completed `#TODO → #DONE` here and in `dev_document.md`.
- [ ] Do **not** write operational detail into `clinical_document.md` (it is a pointer only).

---

## Staleness note

- Re-verify script flags (§2) against the files if any script changed; interfaces here were checked on the date above.
- Guardrails (§1) are invariant.
- Reconcile if a newer `CHANGELOG.md` entry exists than the date above.
