# human_workflow.md — How Humans Work With These Documents

**Audience:** human clinicians and human developers on this project.
**Companion:** `ORCHESTRATOR.md` (the machine-facing governance contract). This file is the human-facing "how do I actually use it" guide.
**Last reconciled:** 2026-07-20.

> **One-sentence version:** clinicians edit `clinical_document.md`, developers edit `dev_document.md` (and code), nobody routinely edits `ORCHESTRATOR.md`, and every internal task note carries a date so staleness is obvious at a glance.

---

## 1. Which document do I edit? (decision tree)

```
Are you a CLINICIAN giving feedback on labels, therapies, or safety flags?
   → Edit  <directory>/clinical_document.md   — add your note at the TOP.
     (Vocabulary/schema decisions live in  config/clinical_document.md.)
     (Tagging-quality spot-checks live in  ingestion/clinical_document.md.)

Are you a DEVELOPER doing or reviewing engineering work?
   → Edit  <directory>/dev_document.md        — add feedback at the TOP.
   → You may also revise code and any other file directly.
   → If your change encodes a clinician suggestion into logic → write an MIU
     (copy MIU_TEMPLATE.md → miu/MIU-<NNN>-<slug>.md) FIRST.

Are you changing the WORKFLOW ITSELF (the rules, the boundaries, the tag
convention, adding a new directory triad)?
   → Edit  ORCHESTRATOR.md  — but only with orchestrator-level review
     (see §4). This is rare. Do NOT edit it for routine feature work.

Are you triggering an AUTOMATED agent?
   → Point it at  <directory>/agentic_document.md. It ingests ORCHESTRATOR.md
     first, does the work, and writes a dated handoff entry back.
```

**Rule of thumb:** `ORCHESTRATOR.md` and `MIU_TEMPLATE.md` are the *constitution*; the directory triads are where the *day-to-day work* is recorded. Edit the most specific document that fits your change. Never start by editing `ORCHESTRATOR.md` unless the workflow rules are what you're changing.

## 2. The loop (what happens after you edit)

1. **Clinician** writes narrative feedback at the top of `clinical_document.md`. Done — no technical follow-through expected.
2. **Developer** reads it, and if it changes logic/vocabulary/a filter, writes an **MIU** (deterministic spec) and updates `dev_document.md`. May implement directly or hand to an agent.
3. **Agent** (triggered via `agentic_document.md`) implements, updates the "points for review" in the clinical + dev docs, appends a dated handoff entry, and — if the change touched the schema source of truth — walks the propagation chain (`ORCHESTRATOR.md §4.2`).
4. Your original feedback is never deleted; it is marked `#DONE[date]` with a one-line resolution so the trail survives.

## 3. Where feedback goes, exactly

- **Newest at the top.** Each doc has a `Feedback log (newest first)` (clinician/dev) or `Handoff log (newest first)` (agent). Prepend; don't append.
- **One marker line** (`▲ unprocessed above this line ▲`) separates new, unprocessed feedback from what's already been actioned. Readers process everything above it.
- **Don't reformat old entries.** Add yours; leave history intact.

## 4. Editing the governance files (rare, higher bar)

`ORCHESTRATOR.md`, `MIU_TEMPLATE.md`, and this file govern everything. Change them only when the *process* changes, and:

- State the change at the top of the affected file and bump its `Last reconciled` date.
- If it changes how agents behave, note it in every `agentic_document.md` handoff log so the next agent sees it.
- Prefer a proposal in a `dev_document.md` first (`#TODO(governance-change)[date]`) over a silent edit to the constitution.

## 5. The dated-tag convention (read this once)

Every internal task note is a **dated tag**. The date is *when the status was last affirmed* — it is what lets anyone tell, at a glance or by `grep`, whether a note is still trustworthy.

**Form:** `#TAG(anchor)?[YYYY-MM-DD]`

| Example | Read as |
|---|---|
| `#TODO[2026-07-20]` | still to do, confirmed current on 2026-07-20 |
| `#TODO(front-matter)[2026-07-20]` | same, with a cross-doc anchor `front-matter` |
| `#DONE[2026-07-20]` | completed 2026-07-20 |
| `#NOTE(asa-preserved)[2026-07-20]` | context note, anchored, affirmed 2026-07-20 |
| `#STALE[2026-07-20]` | found contradicted by the authoritative set on 2026-07-20 |

**The three habits that keep it honest:**
1. **When you touch a tag, bump its date to today.** Re-reading a `#TODO` and confirming it's still true? Change its date. That single act records "someone checked this today."
2. **Completing a `#TODO` → `#DONE[today]`**, keeping the anchor and adding a one-line resolution (+ a `CHANGELOG.md` pointer if code/schema changed).
3. **If a tag's date is older than the newest `CHANGELOG.md` entry for that directory, treat it as suspect** — re-verify and re-date, or resolve it.

**Where it applies:** `ORCHESTRATOR.md`, `MIU_TEMPLATE.md`, this file, every `agentic_document.md`, every `dev_document.md`. **Not** `clinical_document.md` — clinicians use plain `#TODO`/`#DONE`; the dating machinery is internal.

## 6. Checking freshness yourself (no tooling needed beyond grep)

```bash
# Everything still open or noted, oldest first — your staleness worklist.
grep -rEoh '#(TODO|NOTE|STALE|PARTIAL)(\([a-z0-9-]+\))?\[[0-9]{4}-[0-9]{2}-[0-9]{2}\]' \
  ORCHESTRATOR.md human_workflow.md MIU_TEMPLATE.md */agentic_document.md */dev_document.md \
  | sort -t'[' -k2

# Is a document stale? Compare its newest tag date / "Last reconciled" header
# against the newest entry in that directory's CHANGELOG.md. Older = suspect.
```

**The authoritative set** (what's actually current) is narrow: everything in `config/`, plus `config/rta_v1.json`, `config/schema_recommendations.md`, `config/summary.md`. Treat other root-level `.md` docs as out of date until reconciled (`ORCHESTRATOR.md §8`).

## 7. Worked examples

- **Clinician:** "Add a caution — don't do exposure when the patient is intoxicated." → Add it to the top of `config/clinical_document.md`. A developer turns it into an MIU that adds/uses the `intoxication` state and the `directionality: contraindicated` + `applies_when: [intoxication]` pairing; you later see your item flip to `#DONE` with a plain-language note.
- **Developer:** tightening the `applies_when` state vocabulary once clinicians answer Q2 → write `miu/MIU-002-state-vocab.md`, update `config/rta_v1.json` `$defs.state_vocab`, re-register the filterable array, add a `config/CHANGELOG.md` entry, then flip `#TODO(applies-when-vocab)[…]` to `#DONE[today]` in `config/dev_document.md` and `config/agentic_document.md`.
- **Anyone:** you notice `BOOTSTRAP.md` claims something the schema contradicts → mark that line `#STALE[today]` and move on; don't silently trust or delete it.

## 8. Current state you should know (2026-07-20)

- The **RTA ingestion schema migration is done**: the pipeline now uses `config/rta_v1.json` (23 fields). `config/metadata_schema.json` is kept for future after-session analysis (ASA) and as history. Details: `config/agentic_document.md` and `ORCHESTRATOR.md §7`.
- **No documents have been ingested yet.** The first ingest is still ahead — see the runbook in `ingestion/agentic_document.md §2` / `scripts/agentic_document.md`.
- **Known live gap:** front-matter (title pages, TOC) is not yet filtered under the new schema — spot-check the first ingest (`ingestion/dev_document.md`).

---

## Staleness note

- This guide tracks the tag convention in `ORCHESTRATOR.md §3` and the workflow in §1. If either changes, re-date this file.
- Mark any contradicted line `#STALE[date]`; re-verify against the authoritative set.
