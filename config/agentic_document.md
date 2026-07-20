# config/ — Agentic Instructions (Internal-Facing)

**Audience:** automated (agentic) developers. Full operational detail.
**Precondition:** you have already ingested `/ORCHESTRATOR.md` this session. If not, stop and read it.
**Source of truth:** `config/rta_v1.json` (design) / `config/metadata_schema.json` (wired). Reconcile both before editing.
**Last reconciled:** 2026-07-20.

---

## Handoff log (newest first)

<!-- Each agent appends a dated entry at the TOP describing what it changed, what it left open,
     and what the next agent should do first. Never rewrite prior entries. -->

### 2026-07-20 — orchestrator bootstrap
- Created the governance layer (`/ORCHESTRATOR.md`, `/MIU_TEMPLATE.md`) and this directory triad.
- Verified: `rta_v1.json` parses (23 fields); `metadata_schema.json` parses (37 fields); code loads the 37-field schema.
- **Next agent should:** resolve `#TODO(schema-migration)` (§2 decision) before any real ingest, and land the cheap `#TODO(stale-notes)` fix (§4) which currently pollutes the ingestion prompt.
- Left open: all §3 blocking items in `dev_document.md`; clinician Q2 unanswered.

`<!-- ▲ latest handoff above ▲ -->`

---

## 1. Operating rules for this directory

1. `rta_v1.json` is the vocabulary SoT. Do not change enums without a `config/CHANGELOG.md` entry and a version bump (`_v1` → `_v1_1` additive, `_v2` breaking).
2. Field **descriptions are prompt text** (`metadata_gen._build_extraction_prompt` embeds `properties` JSON + `notes`). Editing a description changes model behavior. Keep descriptions short and definitional; put disambiguation in a maintained ingestion-guidance file, not the schema.
3. Never hand-edit enum lists into `metadata_gen.py` — that reintroduces the drift `schema_loader.py` exists to kill. All vocabulary flows from the schema.
4. Any change to a **high-stakes field** (`ORCHESTRATOR §6`) requires an MIU and the validation gate.
5. After any schema edit that adds/renames an array field, you MUST re-register it in `scripts/setup_vertex_search.py` — unregistered filterable arrays fail silently.

## 2. DECISION REQUIRED before first ingest — which schema?

The code loads `metadata_schema.json` (37 fields); the design SoT is `rta_v1.json` (23 fields). Pick one, explicitly, and record it in `config/CHANGELOG.md`:

- **Option A — ingest now on `metadata_schema.json` (fastest path to a first ingest).**
  - Pro: code + DataStore registration already target it; no schema work needed.
  - Con: tags stale ASA fields (`corpus_scope`, `analysis_function`, `missingness`, …) the RTA design dropped; a later migration to `rta_v1.json` is a **breaking** change ⇒ `purge_datastore.py --confirm` + full re-ingest.
  - Use if the goal is to validate the *pipeline mechanics* end-to-end, not the final vocabulary.
- **Option B — migrate to `rta_v1.json` first, then ingest (correct end-state).**
  - Blocked on: `#TODO(applies-when-vocab)` (needs clinician Q2), `#TODO(directionality-default)`, `#TODO(pairing-conditional)`, `#TODO(stale-notes)`, and repointing `settings.metadata_schema_path` (or the three hardcoded defaults) at `rta_v1.json`.
  - Pro: first ingest tags against the intended vocabulary; no re-ingest churn.
  - Con: gated on clinician input (Q2) that is not yet in.

**Recommendation:** if a first ingest is needed *now* to prove the pipeline, do **Option A explicitly labeled as a throwaway validation run** (do not treat its index as production), and keep Option B as the real target. Do not silently drift into Option A by just running the script. Whichever you choose, write it down.

## 3. Task queue (execute top-down; each links a review point in `dev_document.md`)

- **#TODO(stale-notes)** — cheap, do first, no clinician input needed.
  - Delete `notes.routing_safety`, `notes.representation_and_implementation_fields`, `notes.recommended_change_items` from `rta_v1.json`.
  - Rewrite `notes.vertex_ai_search` to list the *actual* array fields in `rta_v1.json`: `therapeutic_modality, clinical_presentation, session_event_tags, applies_when, risk_dimension_tags, patient_population, clinical_measure_tags, technique_tags, clinical_caution` (keywords/missingness informational — but note `missingness` is not even in `rta_v1.json`).
  - Fix four descriptions: `patient_population` (drop `evidence_base` ref), `session_phase` (reconcile `pre_intake_consultation`: add to enum or drop from prose), `clinical_measure_tags` (drop `analysis_function`), `session_event_tags` (complete the sentence truncated at "Motivational").
  - Normalize `C-SSRS`/`Columbia` to one value.
  - Acceptance: `python3 -c "import json;json.load(open('config/rta_v1.json'))"` clean; no description references a field absent from the schema.
- **#TODO(directionality-default)** — add `"default": "neutral"` to `directionality` OR add it to `required`. One-line change; no clinician input.
- **#TODO(applies-when-vocab)** — BLOCKED on clinician Q2. When answered: add `$defs.state_vocab`, constrain `applies_when.items` to `oneOf` (event ∪ presentation ∪ state enums), re-register `applies_when` as filterable, add MIU. See `MIU_TEMPLATE.md` MIU-001.
- **#TODO(pairing-conditional)** — add the draft-07 `if/then` from `summary.md §2.4` after `applies_when` is constrained (order matters — the conditional references it).
- **#TODO(schema-migration)** — see §2. Do not close silently.

## 4. Invariants to preserve (from `summary.md §0`)

- `directionality` and `applies_when` are one unit — never read/write/validate one without the other.
- Contraindications are never dropped by a relevance threshold.
- Ingestion vocabulary and detection vocabulary are the same enum with opposite semantics — never share a prompt between them.

## 5. Verification commands

```bash
# schema parses
python3 -c "import json;print(len(json.load(open('config/rta_v1.json'))['properties']),'fields')"
python3 -c "import json;print(len(json.load(open('config/metadata_schema.json'))['properties']),'fields')"

# which schema the code will load
PYTHONPATH=. python3 -c "from config.settings import settings; print(settings.metadata_schema_path)"

# vocabulary the loader exposes (sanity-check enums after any edit)
PYTHONPATH=. python3 -c "from config.schema_loader import SchemaVocabulary as V; v=V.from_path(); print(sorted(v.array_fields))"
```

## 6. Update-on-exit checklist (before you hand off)

- [ ] Append a dated entry to the Handoff log above.
- [ ] Flip any completed `#TODO → #DONE` here **and** in `dev_document.md`, with a `config/CHANGELOG.md` date.
- [ ] Update the plain-language *Points for review* in `clinical_document.md` if a clinician-visible item changed (translate — no code symbols).
- [ ] If you touched the SoT, walk the full propagation chain (`ORCHESTRATOR §4.2`).
- [ ] Re-date the `Last reconciled` headers you touched.

---

## Staleness note

- Re-verify §2 (schema wiring) and §3 (blocking items) against the live files each session — this is the fastest-moving area of the repo.
- The trailing-comma items in `summary.md §2.1` / `schema_recommendations.md §7.1` are resolved (`#STALE`).
- If `config/CHANGELOG.md` has an entry newer than this file's date, reconcile before feature work.
