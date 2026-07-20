# RTA Schema — Implementation Summary for Programming Agents

**Audience:** Claude Code / programming agents implementing the RTA ingestion and retrieval pipeline.
**Companion:** `schema_recommendations.md` (analysis and rationale). This document is the actionable extract.
**Schema under implementation:** `rta_v1.json` (ChunkMetadata_v1).

---

## 0. Read this first — three invariants

These hold regardless of which task you're working on. Violating any one produces a silent failure, not an exception.

1. **`directionality` and `applies_when` are a single unit.** Never read, write, validate, or filter on one without the other. A `contraindicated` chunk with empty `applies_when` is a data error.
2. **Contraindications are never dropped by a relevance threshold.** If a chunk matches a fired event and carries `directionality: "contraindicated"`, it is returned. Ranking may reorder it; nothing may filter it out.
3. **The ingestion vocabulary and the detection vocabulary are the same enum with opposite semantics.** Ingestion tags what a chunk is *about*; detection emits what *is happening*. Never share a prompt between them.

---

## 1. System architecture — where each field is consumed

Three consumers, three clocks. Field placement follows from the clock.

```
SESSION START (slow path — no latency constraint)
  ├── read session context: diagnosis, modality, session N, risk flags, state flags
  ├── build working set = pre-filter corpus on:
  │     therapeutic_modality  (∪ MI, always)
  │     clinical_presentation
  │     session_phase          (soft — events override)
  │     patient_population     (ranking moderator, not hard filter)
  ├── preload mandatory-always content       (applies_when = [], high doc_type precedence)
  └── preload risk-monitoring content        (risk_dimension_tags ∩ patient risk profile)

MID-SESSION, PER UTTERANCE (fast path — latency-critical)
  ├── DETECTOR (thin)  → emits: session_event_tags value + confidence + span
  │                      reads NO other schema field
  └── ANALYSIS LLM     → queries INTO working set only:
        WHERE applies_when ∩ (fired_events ∪ session_states ∪ presentations) ≠ ∅
           OR applies_when = []
        RANK  boost directionality = "contraindicated"
              boost doc_type precedence
        ALWAYS attach clinical_caution + missingness when non-empty
```

**Do not** query the full corpus on the fast path. **Do not** put modality or presentation reasoning in the detector.

---

## 2. Immediate fixes required (blocking)

### 2.1 `rta_v1.json` does not parse — fix first

Trailing comma after the `missingness` block (~line 251), before the `properties` closing brace.

```jsonc
    "missingness": { ... "default": [] },   // <-- remove this comma
  },
  "additionalProperties": false,
```

Verify: `python3 -c "import json; json.load(open('rta_v1.json'))"` must exit cleanly.

### 2.2 Add a schema-parse CI gate

Any commit touching a `*.json` schema must fail CI if it does not parse. This defect class should never reach human review.

```python
# tests/test_schema_valid.py
import json, glob, pytest

@pytest.mark.parametrize("path", glob.glob("config/*.json"))
def test_schema_parses(path):
    with open(path) as f:
        json.load(f)
```

### 2.3 Define the `applies_when` vocabulary

`applies_when` is currently `{"type": "string"}` — unconstrained. This is the highest-severity design gap: ingestion drift here causes **silent** retrieval misses on the contraindication path.

Add to `rta_v1.json`:

```jsonc
"$defs": {
  "state_vocab": {
    "type": "string",
    "enum": [
      "acute_suicidality", "intoxication", "insufficient_stabilization",
      "active_dissociation", "acute_psychosis", "medical_instability",
      "cognitive_impairment", "active_self_harm"
    ]
  }
}
```

and constrain `applies_when.items` to the union of `session_event_tags` ∪ `clinical_presentation` ∪ `state_vocab`.

> **The enum values above are a placeholder pending clinician input (`schema_recommendations.md` §9, Q2).** Implement the *mechanism* now; treat the value list as provisional and version it when clinicians respond.

### 2.4 Enforce the directionality/applies_when pairing

Add the draft-07 conditional at schema root:

```jsonc
"if": {
  "properties": { "directionality": { "enum": ["contraindicated", "cautionary"] } },
  "required": ["directionality"]
},
"then": {
  "properties": { "applies_when": { "minItems": 1 } }
}
```

Also give `directionality` a default (`"neutral"`) or add it to `required` — it is currently optional with no default and may be silently absent.

### 2.5 Purge stale references

Descriptions are used to build ingestion prompts, so stale text is a live instruction to the model.

**Delete these notes entirely** (change history belongs in `changelog.md`):
- `notes.routing_safety` — describes removed `corpus_scope` / `target_audience` / `analysis_function` routing
- `notes.representation_and_implementation_fields` — all 9 fields removed
- `notes.recommended_change_items` — ~20 values not in any enum

**Rewrite** `notes.vertex_ai_search` against the actual 24 fields (it currently lists 7 that don't exist).

**Fix these descriptions:**
| Field | Problem |
|---|---|
| `patient_population` | references removed `evidence_base` |
| `session_phase` | describes `pre_intake_consultation`, not in enum — add value or drop mention |
| `clinical_measure_tags` | references removed `analysis_function=outcome_monitoring` |
| `session_event_tags` | truncated mid-sentence: `"...for the RTA pipeline. Motivational"` |

**Also:** normalize `C-SSRS` / `Columbia` in `clinical_measure_tags` (same instrument, two values).

---

## 3. Ingestion pipeline

### 3.1 Split the prompt: generated vocabulary + maintained guidance

The drift failure mode — hand-maintained prompt diverges from schema, ingestion emits unfilterable values — is eliminated by generating enum lists mechanically. Disambiguation guidance is clinical judgment and stays hand-written.

```
prompts/
  ingestion_vocab.generated.md   # BUILD ARTIFACT — never edit by hand
  ingestion_guidance.md          # hand-maintained: definitions, edge cases, few-shots
  ingestion_prompt.py            # concatenates the two at runtime
```

Build step reads `rta_v1.json` and emits every enum. Add a CI check that fails if `ingestion_vocab.generated.md` is stale relative to the schema.

### 3.2 Ask for `directionality` + `applies_when` as one question

Asking separately invites the model to fill one and default the other. Prompt as a single decision:

> "Does this passage say to **do** something, **avoid** something, or proceed with **caution** — and under exactly what patient states, presentations, or in-session events does that apply? If it applies whenever the modality is active, return an empty list."

### 3.3 Post-extraction validation (hard gate before write)

Run every chunk through validation; route failures to a QA queue, never to the index.

| Check | Action on failure |
|---|---|
| All array values ∈ declared enum | **Reject** — out-of-vocab is the primary drift vector |
| `directionality ∈ {contraindicated, cautionary}` → `applies_when` non-empty | **Reject** |
| `applies_when` values ∈ combined vocabulary | **Reject** |
| `page_end >= page_start` | Reject |
| `doc_id` matches `^[a-f0-9]{64}$` | Reject |
| `therapeutic_modality` length > 4 | **Warn** — usually mis-chunked protocol overview |
| `domain` vs `therapeutic_modality` mismatch | **Warn** — may be legitimate cross-reference |
| `clinical_caution` non-empty but `directionality == "indicated"` | **Warn** — likely missed contraindication |
| `technique_tags` > 10 or `keywords` > 10 | Truncate |

### 3.4 Ingestion QA sampling

Require a per-tag rationale field during QA runs; strip it before indexing. Sample ~5% of chunks per source and review tag density outliers. Tag drift is invisible in aggregate metrics — it only shows up in retrieval quality weeks later.

---

## 4. Retrieval pipeline

### 4.1 Session-start working set

```python
working_set = corpus.filter(
    therapeutic_modality__overlaps = active_modalities | {"MI"},   # MI always unioned
    clinical_presentation__overlaps = session.presentations,
)
preload  = working_set.filter(applies_when=[], doc_type__in=HIGH_PRECEDENCE)
preload += corpus.filter(risk_dimension_tags__overlaps=patient.risk_profile)
```

**MI is never filtered out.** It is unioned into every working set regardless of `domain`. `motivational_ambivalence` then boosts already-loaded MI content rather than triggering a cold fetch.

### 4.2 Event-time query

```python
def on_event(event_tag, session_state):
    active = {event_tag} | session_state.states | session_state.presentations
    hits = working_set.filter(
        Q(applies_when__overlaps=active) | Q(applies_when=[])
    )
    hits = rank(hits,
        boost_contraindicated = True,      # invariant #2
        boost_doc_type_precedence = True,
        relax_session_phase = True,        # events override phase
    )
    return attach_cautions(hits)           # clinical_caution + missingness
```

Three rules with safety consequences:

- **`applies_when` multi-value semantics are OR**, not AND (broader net; see `schema_recommendations.md` §8.3). Document this in the searcher.
- **`session_phase` is a soft filter that events relax.** A hard phase filter would suppress crisis content during a late-treatment session — exactly backwards. `crisis` is phase-agnostic by design.
- **`none` in `session_event_tags` is ingestion bookkeeping only.** Never a retrieval target; exclude from event-time candidates.

### 4.3 Precedence on conflict

Pending clinician confirmation (§9, Q6). Implement as configurable, defaulting to:

```
treatment_manual > clinical_guideline > textbook > other
tiebreaker: higher year_published
```

Do not hardcode — this ordering is a clinical decision that will likely change.

### 4.4 DataStore registration

All array fields must be explicitly registered as filterable attributes in `setup_vertex_search.py`, or filters silently no-op. For the current schema that is: `therapeutic_modality`, `clinical_presentation`, `session_event_tags`, `applies_when`, `risk_dimension_tags`, `patient_population`, `clinical_measure_tags`, `technique_tags`, `clinical_caution`.

`missingness` and `keywords` are informational; registration optional.

> **Verify registration after every schema change.** An unregistered filterable array fails *silently* — the filter is ignored and results look plausible. This is the single most likely production defect in this pipeline.

Schema changes require `purge_datastore.py --confirm` followed by full re-ingestion.

---

## 5. Detector implementation

Keep it thin. The detector reads **only** `session_event_tags` and emits:

```json
{ "event": "disclosure_SI", "confidence": 0.87, "span": [1204, 1261] }
```

It does not read `therapeutic_modality`, `applies_when`, `directionality`, or any other field. No retrieval, no modality reasoning, no contraindication logic — all of that belongs to the analysis LLM operating over the pre-narrowed working set. Every field added to the detector's context costs latency on the critical path.

Per-event confidence thresholds should be **asymmetric**: a missed `disclosure_SI` is categorically worse than a missed `nonadherence`. Set thresholds low (favor recall) for the duty-of-care events (`disclosure_SI`, `disclosure_HI`, `disclosure_abuse`, `crisis_escalation`) and higher (favor precision) for `nonadherence` and `avoidance_in_session`.

---

## 6. Open items — do not implement until resolved

These are blocked on clinician input. Build the mechanism; leave the values configurable.

| Item | Blocked on | Ref |
|---|---|---|
| `applies_when` state vocabulary values | Q2 | §7.2 |
| Modality hard-filter vs. soft-boost | Q1 | Alt A |
| `chunk_kind` field | Q8 | §1.2 |
| `severity` axis on events | Q4 | Alt C |
| `risk_dimension_tags` preload vs. background pass | Q5 | §3.0 |
| `doc_type` precedence order | Q6 | §7.4 |
| `dissociation` event retention | Q3 | §9 |
| Drop `missingness` | — | §8.4 — recommended drop; low risk to action now |
| Remove `emdr_therapy` from `domain` | — | §7.5 — no corresponding modality exists |

---

## 7. Updating documents as clinical feedback arrives

Keeping four artifacts consistent is the main maintenance risk. The rule: **`rta_v1.json` is the single source of truth for vocabulary; everything else derives from or annotates it.**

### 7.1 Document roles

| Artifact | Role | Edited by |
|---|---|---|
| `rta_v1.json` | Source of truth — field definitions and enums | Human, versioned |
| `schema_recommendations.md` | Analysis, open questions, rationale | Human, appended |
| `changelog.md` | Dated record of what changed and why | Human, append-only |
| `summary.md` (this doc) | Implementation contract for agents | Human, revised per schema version |
| `ingestion_vocab.generated.md` | Enum lists | **Generated — never hand-edit** |
| `ingestion_guidance.md` | Disambiguation, few-shots | Human |

### 7.2 Procedure when clinician feedback arrives

Follow in order — steps 4 and 5 are the ones most often skipped, and both cause silent failures.

1. **Record verbatim in `changelog.md`** under a dated heading, with the question asked and the answer given. Do not paraphrase into a decision yet — the raw answer often matters later.
2. **Update `rta_v1.json`.** Bump the version (`ChunkMetadata_v1` → `_v1_1` for additive, `_v2` for breaking). Update `title` and `description`.
3. **Resolve the corresponding open question** in `schema_recommendations.md` §9 — mark **#DONE** with a one-line answer and a changelog date. Move the annotation in §1–§5 from #TODO to #DONE.
4. **Regenerate `ingestion_vocab.generated.md`** and update `ingestion_guidance.md` if the change introduces an ambiguous boundary.
5. **Re-register filterable attributes** in `setup_vertex_search.py` for any new or renamed array field. ← *silent failure if skipped*
6. **Re-ingest** if the change is breaking: `purge_datastore.py --confirm`, then full re-ingestion. Additive enum values on existing fields do not require a purge, but previously-ingested chunks will not carry the new value until re-ingested.
7. **Update this document's §6** to move the item out of open items.

### 7.3 Which changes require full re-ingestion

| Change | Re-ingest? |
|---|---|
| New enum value on existing field | No — but old chunks won't have it |
| New field | Yes, to populate it |
| Removed field | No — but purge for a clean index |
| Renamed field | **Yes** — breaking |
| Changed field semantics | **Yes** — old tags mean something different now |
| Description-only edit | No — but regenerate prompts |

### 7.4 Answer-to-artifact map

When a §9 question is answered, these are the files that change:

- **Q1 (modality matrix)** → searcher filter logic; `notes` in `rta_v1.json`; possibly a new `modality_compatibility.json`
- **Q2 (state vocab)** → `$defs.state_vocab`; `applies_when` constraint; generated prompt; **DataStore re-registration**
- **Q3 (dissociation)** → `session_event_tags` enum; detector config
- **Q4 (severity)** → possible new `severity` field; detector output shape; **breaking, requires re-ingestion**
- **Q5 (risk preload)** → session-start logic only; no schema change
- **Q6 (precedence)** → ranking config; `doc_type` description
- **Q7 (session context)** → determines whether `session_phase` is usable at all; may retire the field
- **Q8 (actionability)** → possible `chunk_kind` field; **requires re-ingestion**
- **Q9 (contraindication breadth)** → ingestion tagging rule; searcher floor on contraindications
- **Q10 (preload budget)** → session-start injector; no schema change

---

## 8. Definition of done for the current phase

- [ ] `rta_v1.json` parses; CI gate added (§2.1, §2.2)
- [ ] `applies_when` constrained to a closed vocabulary (§2.3)
- [ ] Pairing conditional added; `directionality` has default or is required (§2.4)
- [ ] Stale notes deleted; four descriptions fixed (§2.5)
- [ ] Ingestion prompt split into generated + maintained (§3.1)
- [ ] Post-extraction validation gate with QA queue (§3.3)
- [ ] Searcher implements working-set pre-filter and event-time query separately (§4.1, §4.2)
- [ ] Contraindications exempt from relevance-threshold filtering (invariant #2)
- [ ] All array fields registered as filterable; registration verified post-change (§4.4)
- [ ] Detector reads only `session_event_tags`; asymmetric thresholds set (§5)
- [ ] §9 questions sent to clinicians, prioritized Q2 → Q1 → Q7 (§6)
