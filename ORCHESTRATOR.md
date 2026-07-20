# ORCHESTRATOR.md

**Governs:** the entire `rag_guidance` repository.
**Ingested by:** every automated (agentic) developer at the start of every session, before touching any file.
**Owner role:** interim Lead Project Orchestrator / Clinical-Technical Liaison.
**Last reconciled:** 2026-07-20 (against `config/` + `rta_v1.json` + `schema_recommendations.md` + `summary.md`).

> This document is the contract. If a directory-level `agentic_document.md` conflicts with this file, **this file wins** and the conflict is logged as a `#TODO` in that directory's `dev_document.md`.

---

## 0. Read-this-first — three operating rules

1. **The authoritative set is narrow.** Only these are current: everything in **`config/`**, plus **`config/rta_v1.json`**, **`config/schema_recommendations.md`**, **`config/summary.md`**. **Every other `.md` in the repo root and subdirectories is presumed out of date** until re-reconciled (see §8). Do not cite root-level docs (`BOOTSTRAP.md`, `architecture_bootstrap.md`, `JULY_TECHNICAL.md`, `metadata_summary.md`, `structure.md`, `issues.md`, `DISCREPANCIES.md`, `presentation.md`, `caveats.md`, etc.) as ground truth.
2. **The vocabulary source of truth is `config/rta_v1.json`.** Everything else derives from or annotates it. There is a live migration gap: the *code* still loads `config/metadata_schema.json` (see §7). Never assume a field exists in the running pipeline just because it exists in `rta_v1.json`, or vice-versa — check both.
3. **Safety fields are validated, never inferred loosely.** `therapeutic_modality`, `directionality`+`applies_when`, `clinical_caution`, `risk_dimension_tags`, and the duty-of-care `session_event_tags` (`disclosure_SI`/`disclosure_HI`/`disclosure_abuse`/`crisis_escalation`) are **high-stakes**. Changes to them require the validation gate in §6 and an MIU (§5). No exceptions.

---

## 1. The workflow this repository runs on

Three actors, one loop, per functional directory:

```
        ┌─────────────────────────────────────────────────────────────┐
        │  clinical_document.md   (external-facing — clinicians)       │
        │  dev_document.md        (internal-facing — architects)       │
        │  agentic_document.md    (internal-facing — automated agents) │
        └─────────────────────────────────────────────────────────────┘

  1. CLINICIAN   reviews clinical_document.md, writes feedback AT THE TOP
                 (free narrative; high-stakes items flagged for validation).
                          │
  2. DEVELOPER   reviews dev_document.md, writes feedback AT THE TOP;
                 may revise any other file; translates clinical narrative
                 into an MIU spec (MIU_TEMPLATE.md) when it touches logic.
                          │
  3. AGENT       is triggered via agentic_document.md. It:
                   a. ingests ORCHESTRATOR.md (this file) first,
                   b. reads the relevant clinical_document.md + dev_document.md
                      + any files the developer updated,
                   c. continues the programming work,
                   d. updates the "points for review" sections in
                      clinical_document.md and dev_document.md,
                   e. appends a handoff entry to agentic_document.md for the
                      next agent.
                          │
                          └──────────► loop repeats
```

**Feedback goes at the TOP.** New clinician/developer feedback is prepended (newest first) under the `## Feedback log (newest first)` heading in the respective document. Agents read the top entries first and treat anything above the last-processed marker as unprocessed.

**Agents never delete human feedback.** They mark it `#DONE` with a dated one-line resolution and leave it in place. Change history lives in the relevant `CHANGELOG.md`, not in erased feedback.

---

## 2. Document taxonomy

### 2.1 Governance layer (root)

| File | Role | Audience |
|---|---|---|
| `ORCHESTRATOR.md` (this file) | Whole-repo protocol, boundaries, cohesion, staleness | All agents (ingest first) |
| `MIU_TEMPLATE.md` | Clinical-to-Engineering "Minimum Implementable Unit" spec template | Developers + agents |
| `CLAUDE.md` | Claude Code operating notes for this repo | Agents (harness) |

### 2.2 Directory layer (the dual-audience triad)

Every **functional directory that requires clinical feedback** carries three documents. Currently in scope: **`config/`**, **`ingestion/`**. `scripts/` is operational and carries the internal two plus a thin clinical pointer (see §2.3).

| File | Facing | Audience | Technical depth | May contain |
|---|---|---|---|---|
| `clinical_document.md` | **External** | Clinicians | Minimal | Plain-language behavior, clinical decisions needed, open questions, validation asks. **No internal system detail.** |
| `dev_document.md` | **Internal** | Architects / technical auditors | Moderate | Design rationale, schema/field mechanics, known defects, migration state, review points. |
| `agentic_document.md` | **Internal** | Automated agents | Full | Exact file paths, commands, invariants, step-by-step continuation instructions, handoff log. |

### 2.3 The external/internal boundary (anti-overexposure rule)

The boundary exists to prevent internal system details from leaking into clinician-facing text, and to keep unvalidated clinical claims out of engineering specs.

**`clinical_document.md` (external-facing) MUST NOT contain:**
- GCP resource names, project IDs, bucket names, datastore/engine IDs, regions
- Model IDs, API keys, credentials, cost or latency numbers
- Code paths, function/class names, schema field names *as code* (translate to plain language)
- Security-sensitive configuration or infrastructure topology
- Known-defect detail that implies an exploit or unsafe interim state

**`clinical_document.md` (external-facing) SHOULD contain:**
- What the system does, in clinical language
- Which clinical decisions are pending clinician input (e.g. the modality co-retrieval matrix)
- The exact questions needing answers, framed clinically (mirror `schema_recommendations.md` §9)
- What "validated" means for modalities and clinical flags, and why it matters for patient safety

**`dev_document.md` / `agentic_document.md` (internal-facing) MUST NOT contain:**
- Patient data, PHI, or any real clinical case content
- Unvalidated clinical assertions presented as settled (mark them `#TODO — clinician sign-off pending`)

When an agent needs to reference an internal detail while answering a clinician's question, it puts the plain-language answer in `clinical_document.md` and the mechanism in `dev_document.md`, linked by a shared `#NOTE` id (e.g. `#NOTE(applies-when-vocab)`).

---

## 3. Notation standard (every generated doc uses this)

Documents are organized in **sections** with inline status tags. Tags are the first token on a line or the first token of a bullet.

| Tag | Meaning | Required trailer |
|---|---|---|
| `#TODO` | Not done; still required | Owner hint + what "done" looks like |
| `#DONE` | Completed | Date (`YYYY-MM-DD`) + one-line resolution |
| `#NOTE` | Context, decision, or cross-reference that is neither a task nor a completion | Optional `#NOTE(id)` anchor for cross-doc linking |

**Extension tags** (permitted, inherited from `schema_recommendations.md` so the two vocabularies stay compatible): `#PARTIAL` (done with a known gap — must link the gap as a `#TODO`), `#DROPPED` (deliberately out of scope — must record rationale so it is not relitigated).

**Rules:**
- Every `#TODO` that touches a high-stakes field (§6) must link an MIU or say `MIU: none yet`.
- Every `#DONE` carries a date and a changelog pointer where a code/schema change was involved.
- Cross-document references use `#NOTE(id)` anchors, resolvable across the whole repo.

---

## 4. Cohesion strategy across edits

The maintenance risk in a multi-artifact, multi-actor repo is drift: four documents describing three subtly different versions of one schema. The strategy is a **single source of truth with a fixed propagation order**.

### 4.1 Source-of-truth hierarchy

```
config/rta_v1.json                 ← SoT for RTA vocabulary (fields, enums)
   ├─ derives → ingestion prompt enum lists      (must be generated, not hand-kept)
   ├─ derives → DataStore filterable registration (setup_vertex_search.py)
   ├─ annotated by → schema_recommendations.md    (analysis, open questions, rationale)
   ├─ extracted to → summary.md                    (actionable contract for agents)
   └─ history in  → config/CHANGELOG.md            (append-only, dated)
```

`config/metadata_schema.json` is the **currently-wired** schema (37 fields, unified RTA+ASA). It is *operationally* authoritative for the code until the migration in §7 completes, but it is *not* the design SoT. This dual status is the single most error-prone fact in the repo — every config-layer doc restates it.

### 4.2 Propagation order when anything changes

A change is not "done" until it has walked the whole chain. Steps 5–6 are the ones that fail silently.

1. **Record** the trigger verbatim in the owning `CHANGELOG.md` under a dated heading.
2. **Edit the SoT** (`rta_v1.json`), bump the version (`_v1` → `_v1_1` additive, `_v2` breaking), update `title`/`description`.
3. **Resolve** the matching open question in `schema_recommendations.md` (§9) and flip the annotation `#TODO → #DONE`.
4. **Update** `summary.md` if the implementation contract changed.
5. **Regenerate** ingestion prompt enum lists; re-register filterable attributes in `setup_vertex_search.py`. ← *silent failure if skipped: filters no-op, retrieval under-returns*
6. **Re-ingest** if breaking (`purge_datastore.py --confirm` → full re-ingest).
7. **Back-annotate** the three directory docs (`clinical`/`dev`/`agentic`) and this file's §7 snapshot.

### 4.3 Consistency invariants (checkable)

- No `clinical_document.md` names a code symbol, GCP resource, or model ID.
- Every enum value quoted in prose exists in `rta_v1.json` (or is tagged `#TODO(proposed)`).
- Every `#DONE` in a directory doc has a changelog date.
- The ingestion prompt's enum legend equals the schema's enums (target state; today it reads from `metadata_schema.json`).

---

## 5. Minimum Implementable Unit (MIU) — mandatory translation layer

Narrative clinician suggestions are never handed to engineering as prose. They are converted into an **MIU spec** first, using **`MIU_TEMPLATE.md`**. An MIU is required whenever clinician feedback would change *logic, vocabulary, or a filter* — trivially cosmetic changes are exempt.

An MIU is not accepted unless it binds all four:
1. **Decision rules** — deterministic `WHEN … THEN …` logic, no adjectives.
2. **Input variables** — every input named, typed, and bounded (closed vocabulary or numeric range).
3. **Edge cases** — the empty case, the conflict case, the missing-input case, the out-of-vocab case.
4. **Acceptance criteria** — observable pass/fail tests an engineer or agent can execute.

MIUs for high-stakes fields additionally pass the §6 validation gate. See `MIU_TEMPLATE.md` for the form and a worked example.

---

## 6. Validation focus — high-stakes clinical elements

Clinician feedback on **therapeutic modalities** and **clinical flags** is validated strictly before it reaches the index. "Clinical flags" = `directionality` + `applies_when`, `clinical_caution`, `risk_dimension_tags`, and duty-of-care `session_event_tags` (`disclosure_SI`, `disclosure_HI`, `disclosure_abuse`, `crisis_escalation`).

**The validation gate (all must hold):**

| Check | Field(s) | Fail action |
|---|---|---|
| Value ∈ closed vocabulary in `rta_v1.json` | modality, presentation, events, risk tags | **Reject** — out-of-vocab is the primary drift vector |
| `directionality ∈ {contraindicated, cautionary}` ⇒ `applies_when` non-empty | directionality/applies_when | **Reject** — "contraindicated for nothing" is a data error |
| `applies_when` values ∈ (events ∪ presentations ∪ state_vocab) | applies_when | **Reject** (state_vocab still `#TODO`, see §7) |
| Contraindication is never dropped by a relevance threshold | directionality | **Block ship** — invariant, must be enforced in the searcher |
| Modality/flag change carries clinician sign-off | all high-stakes | **Hold** — mark `#TODO — clinician sign-off pending` |
| Ingestion vs detection semantics kept separate for `session_event_tags` | events | **Reject** shared prompt — ingestion tags "about"; detection tags "happening" |

These derive from `summary.md` §0 invariants and §3.3. Any agent implementing retrieval or ingestion enforces them in code, not in ranking.

---

## 7. Current-state snapshot (reconcile before trusting)

> This is the fast briefing an agent needs before working. Re-verify against `config/` on each session — mark this section stale if the date below is older than the newest `config/CHANGELOG.md` entry.

**As of 2026-07-20:**

- **Ingest path is implemented and runnable** (`ingestion/` + `scripts/batch_ingest.py`). Query path (`retrieval/`, `generation/`, `rta_prompt/`) is stubbed.
- **Corpus:** 5 PDFs staged in `corpus/` (CBT/PE/social-phobia/cultural-adaptation). **No `.ingestion_manifest.json` yet → nothing has been ingested.** First ingest is genuinely first.
- **Schema migration gap (blocking clean first ingest):**
  - `#NOTE(schema-split)` `config/rta_v1.json` (23 fields, RTA-only, `directionality`+`applies_when` design) is the **design SoT**.
  - `#NOTE(schema-wired)` The **code loads `config/metadata_schema.json`** (37 fields, unified RTA+ASA) via `settings.metadata_schema_path` → `schema_loader.py`, `metadata_gen.py`, `setup_vertex_search.py`.
  - `#TODO(schema-migration)` Decide the first-ingest schema (see `config/agentic_document.md`). Until decided, an ingest today tags against the **37-field** schema, including fields (`corpus_scope`, `analysis_function`, `missingness`, …) that `rta_v1.json` intentionally dropped.
- **`rta_v1.json` open blocking items** (from `summary.md` §2, re-verified):
  - `#DONE` 2026-07-19 file parses (trailing-comma bug already fixed; `summary.md §2.1` text is now stale).
  - `#TODO(applies-when-vocab)` `applies_when` is unconstrained `{"type":"string"}` — no `state_vocab`. Highest-severity gap.
  - `#TODO(directionality-default)` `directionality` has no default and is not `required` — may be silently absent.
  - `#TODO(pairing-conditional)` No `if/then` enforcing directionality↔applies_when pairing.
  - `#TODO(stale-notes)` `notes.routing_safety`, `notes.representation_and_implementation_fields`, `notes.recommended_change_items` describe removed fields and are still read into the ingestion prompt via `metadata_gen._extraction_guidance()`.
- **Open clinician questions:** `schema_recommendations.md` §9, Q1–Q10. Priority Q2 (state vocab) → Q1 (modality matrix) → Q7 (session-context availability).

---

## 8. Out-of-date mitigation protocol (staleness)

Applies to **every** document in the repo, and is restated (in brief) in each generated doc's final section.

### 8.1 How staleness is flagged

- **Freshness header.** Every governed doc carries `Last reconciled: YYYY-MM-DD` near the top. A doc is **suspect** if that date is older than the newest entry in the `CHANGELOG.md` of the directory it describes.
- **`#STALE` tag.** Any reader (human or agent) who finds a claim contradicted by the authoritative set marks the line `#STALE — <reason>` in place, rather than silently trusting or deleting it.
- **Authoritative-set rule.** Anything outside the authoritative set (§0.1) is presumed stale by default and must be re-verified before citation.
- **Provenance-mismatch check.** If a doc references a field/enum/flag not in `rta_v1.json` (design) or `metadata_schema.json` (wired), that reference is stale.

### 8.2 How staleness is resolved

1. **Confirm** against the authoritative set (`config/` + the three named files).
2. **Update or deprecate:**
   - *Update* — rewrite the line, refresh the `Last reconciled` date, add a `#DONE` with today's date.
   - *Deprecate* — if a whole doc is superseded, add a top banner `> DEPRECATED YYYY-MM-DD — superseded by <path>. Retained for history; do not cite.` and stop referencing it. Do not delete (history value).
3. **Record** the reconciliation in the directory `CHANGELOG.md`.
4. **Propagate** via §4.2 if the correction changes the SoT.

### 8.3 Cadence

- **Every agent session:** verify §7 snapshot date vs `config/CHANGELOG.md`; reconcile if behind before doing feature work.
- **Every merged human change to `config/`:** the triggering developer (or the next agent) reconciles the affected directory triad.
- **Weekly (interim orchestrator):** sweep for `#STALE` tags and un-dated `#DONE`s.

### 8.4 Known deprecations (as of 2026-07-20)

- `#NOTE` Root-level narrative docs (`BOOTSTRAP.md`, `architecture_bootstrap.md`, `JULY_TECHNICAL.md`, `metadata_summary.md`, `structure.md`, `issues.md`, `DISCREPANCIES.md`, `discovery_engine_comparison.md`, `schema_notes.md`, `presentation.md`, `caveats.md`) predate the RTA schema split and are **presumed stale**. They have not been individually banner-marked yet — `#TODO(deprecate-root-docs)`.
- `#NOTE` `summary.md §2.1` (trailing-comma fix) is resolved; that subsection is stale but harmless.
- `#NOTE` `CLAUDE.md` still references the older generic-biomedical framing in places (it says so itself) — treat its schema claims as suspect, its command/wiring claims as current.

---

## 9. Document registry

| Path | Type | In scope | Status |
|---|---|---|---|
| `ORCHESTRATOR.md` | Governance | — | Active |
| `MIU_TEMPLATE.md` | Governance | — | Active |
| `config/clinical_document.md` | External | Yes | Active |
| `config/dev_document.md` | Internal | Yes | Active |
| `config/agentic_document.md` | Internal | Yes | Active |
| `ingestion/clinical_document.md` | External | Yes | Active |
| `ingestion/dev_document.md` | Internal | Yes | Active |
| `ingestion/agentic_document.md` | Internal | Yes | Active |
| `scripts/clinical_document.md` | External (pointer) | Operational | Active |
| `scripts/dev_document.md` | Internal | Operational | Active |
| `scripts/agentic_document.md` | Internal | Operational | Active |

**Next directories to onboard when they leave stub state:** `retrieval/`, `generation/`, `rta_prompt/` (query path). Create the triad there at implementation start, not before.

---

*End ORCHESTRATOR.md — reconcile §7 and §8.4 before relying on any snapshot.*
