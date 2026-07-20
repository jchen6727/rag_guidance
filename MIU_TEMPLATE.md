# MIU_TEMPLATE.md — Clinical-to-Engineering Spec Template

**MIU = Minimum Implementable Unit.** The smallest self-contained specification that converts one narrative clinician suggestion into deterministic, bounded, testable engineering logic.

**Governed by:** `ORCHESTRATOR.md` §5 (requirement) and §6 (validation gate).
**When required:** any clinician/developer feedback that changes *logic, vocabulary, or a filter*. Cosmetic/documentation-only changes are exempt.
**Rule of acceptance:** an MIU is rejected unless **all four core blocks** (Decision Rules, Input Variables, Edge Cases, Acceptance Criteria) are complete and bound. High-stakes MIUs additionally pass the Validation Gate block.

> **Why this exists.** Clinicians write "surface a caution when the patient is in crisis." Engineers need "WHEN `applies_when ∩ fired_states ≠ ∅` AND `directionality ∈ {contraindicated, cautionary}` THEN return chunk with `never_filter=true`." The MIU is the lossless translation between the two. No prose adjective survives into code.

---

## How to use this file

1. Copy the **Template** section below into a new file: `miu/MIU-<NNN>-<slug>.md` (create `miu/` if absent).
2. Fill every field. `TBD` is only allowed in `Open questions`, never in the four core blocks.
3. If the MIU touches a high-stakes field (see Validation Gate), complete that block and obtain clinician sign-off.
4. Link the MIU from the triggering `#TODO` in the relevant `dev_document.md` and `agentic_document.md`.
5. On implementation, flip the source `#TODO → #DONE` with the MIU id and a changelog date.

---

## Template (copy below this line)

```markdown
# MIU-<NNN>: <imperative title>

- **Status:** #TODO | #PARTIAL | #DONE | #DROPPED
- **Source feedback:** <verbatim clinician/dev quote + where it came from (doc + date)>
- **Owning directory:** <config/ | ingestion/ | retrieval/ | ...>
- **High-stakes:** yes | no   (yes ⇒ Validation Gate block is mandatory)
- **Affects SoT (`rta_v1.json`):** yes | no   (yes ⇒ version bump + propagation per ORCHESTRATOR §4.2)
- **Author:** <name/agent>  •  **Created:** <YYYY-MM-DD>  •  **Sign-off:** <clinician name / pending>

## 1. Clinical intent (plain language, one paragraph)
<What the clinician wants the system to do, and the patient-safety reason. This is the
only prose block; it is the anchor the four bound blocks are checked against.>

## 2. Decision rules (deterministic)
State every rule as `WHEN <condition> THEN <action>`. No adjectives, no "should",
no "generally". Conditions reference only named Input Variables. Enumerate branches
exhaustively — the reader must be able to compute the output for any input.

- R1. WHEN <...> THEN <...>
- R2. WHEN <...> THEN <...>
- R3. (default / else) WHEN none of the above THEN <...>

## 3. Input variables (named, typed, bounded)
Every input the rules read. No unbounded free text on a decision path.

| Variable | Type | Domain / bound | Source | Default if absent |
|---|---|---|---|---|
| <name> | enum/int/array/bool | <closed set or numeric range> | <detector / session ctx / schema field> | <value or "reject"> |

## 4. Edge cases (must cover all four classes)
- **Empty:** <behavior when the input set is empty / applies_when = []>
- **Conflict:** <two rules or two chunks disagree — which wins, and why>
- **Missing input:** <a required variable is absent — reject vs. safe default>
- **Out-of-vocab:** <a value not in the closed vocabulary arrives — reject/quarantine>
- (add domain-specific edges as needed)

## 5. Acceptance criteria (observable pass/fail)
Executable tests. Each is a concrete input → expected output an engineer or agent can run.

- AC1. GIVEN <input state> WHEN <trigger> THEN <exact observable output>.
- AC2. GIVEN <...> THEN <...>.
- AC3. (negative) GIVEN <bad input> THEN <reject/quarantine with reason>.

## 6. Validation gate — HIGH-STAKES ONLY
Required when this MIU touches: therapeutic_modality, directionality+applies_when,
clinical_caution, risk_dimension_tags, or duty-of-care session_event_tags
(disclosure_SI/HI/abuse, crisis_escalation). Ref ORCHESTRATOR §6.

- [ ] All emitted values ∈ the closed vocabulary in `config/rta_v1.json`.
- [ ] If directionality ∈ {contraindicated, cautionary} → applies_when is non-empty.
- [ ] applies_when values ∈ (session_event_tags ∪ clinical_presentation ∪ state_vocab).
- [ ] Contraindication path cannot be dropped by a relevance threshold (searcher-enforced).
- [ ] Ingestion ("about") vs detection ("happening") semantics kept in separate prompts.
- [ ] Clinician sign-off recorded (name + date) for any modality/flag change.
- **Sign-off:** <clinician name, YYYY-MM-DD | PENDING — do not ship>

## 7. Rollout & reversal
- **Re-ingest required?** yes/no (breaking schema change ⇒ purge + full re-ingest).
- **DataStore re-registration required?** yes/no (new/renamed array field ⇒ yes).
- **Reversal plan:** <how to back this out if a defect surfaces>.

## 8. Open questions
- <TBD items blocked on clinician input; link to schema_recommendations.md §9 Qn>
```

---

## Worked example (reference — do not edit; copy the Template above instead)

```markdown
# MIU-001: Surface trauma-processing contraindication under acute suicidality

- **Status:** #TODO
- **Source feedback:** "Don't let the system push exposure/CPT work when the patient is
  acutely suicidal — it should flag the caution instead." — clinical_document.md, 2026-07-18
- **Owning directory:** config/ (schema) + retrieval/ (searcher, when implemented)
- **High-stakes:** yes
- **Affects SoT (`rta_v1.json`):** yes — requires state_vocab (#TODO applies-when-vocab)
- **Author:** orchestrator  •  **Created:** 2026-07-20  •  **Sign-off:** PENDING

## 1. Clinical intent
When a patient is acutely suicidal, initiating trauma-processing work (PE/CPT imaginal or
in-vivo exposure) can destabilize them. The system must not present that work as indicated
in that moment; it must surface the documented contraindication instead. Missing this is a
patient-safety failure, so recall on the caution matters more than precision.

## 2. Decision rules
- R1. WHEN session state includes `acute_suicidality` AND a candidate chunk has
      `therapeutic_modality ∩ {PE, CPT} ≠ ∅` AND `directionality = contraindicated`
      AND `acute_suicidality ∈ applies_when` THEN return the chunk with `never_filter = true`
      and rank it above indicated chunks.
- R2. WHEN `acute_suicidality` holds AND a candidate chunk describes exposure with
      `directionality = indicated` THEN retain it but demote below any R1 chunk and attach
      its `clinical_caution` text.
- R3. (default) WHEN `acute_suicidality` does not hold THEN normal ranking applies; the
      contraindication chunk is retrievable only when its `applies_when` matches.

## 3. Input variables
| Variable | Type | Domain / bound | Source | Default if absent |
|---|---|---|---|---|
| session_states | array<enum> | state_vocab (incl. `acute_suicidality`) | session context / detector | `[]` |
| chunk.therapeutic_modality | array<enum> | rta_v1 modality enum | schema field | reject chunk |
| chunk.directionality | enum | {indicated,contraindicated,cautionary,neutral} | schema field | `neutral` |
| chunk.applies_when | array<enum> | events ∪ presentations ∪ state_vocab | schema field | `[]` |

## 4. Edge cases
- **Empty:** `applies_when = []` on a contraindicated chunk ⇒ **data error, quarantine** (a
  contraindication with no scope is invalid — ORCHESTRATOR §6).
- **Conflict:** an indicated exposure chunk and a contraindicated one both match ⇒ R1 wins;
  contraindication ranks first, indicated chunk kept with caution attached (never silently dropped).
- **Missing input:** `session_states` unavailable ⇒ fail safe: still surface contraindications
  tagged for trauma modalities (broad-net, per schema_recommendations.md §2.4), do not suppress.
- **Out-of-vocab:** `applies_when` contains `active_SI` (not `acute_suicidality`) ⇒ reject at
  ingestion; never index. This is the exact drift the state_vocab closes.

## 5. Acceptance criteria
- AC1. GIVEN session_states=["acute_suicidality"] and a CPT contraindication chunk with
       applies_when=["acute_suicidality"] WHEN the event fires THEN that chunk is returned,
       marked never_filter, ranked #1.
- AC2. GIVEN the same session and an "indicated imaginal exposure" chunk THEN it is returned
       but ranked below AC1's chunk with its clinical_caution text attached.
- AC3. (negative) GIVEN a contraindication chunk with applies_when=[] THEN ingestion rejects
       it to the QA queue and it never reaches the index.

## 6. Validation gate — HIGH-STAKES
- [x] Values ∈ closed vocabulary — **blocked on** #TODO(applies-when-vocab): `acute_suicidality`
      must be added to a defined `state_vocab` in rta_v1.json first.
- [x] contraindicated ⇒ applies_when non-empty (enforced by R1 + AC3).
- [x] applies_when ∈ (events ∪ presentations ∪ state_vocab).
- [x] contraindication not droppable by threshold (R1 never_filter).
- [x] ingestion vs detection prompts separate.
- **Sign-off:** PENDING — do not ship until clinician confirms the state list (Q2) and the
  PE/CPT contraindication scope (Q9).

## 7. Rollout & reversal
- Re-ingest required? yes — adding state_vocab and re-tagging applies_when is a breaking change.
- DataStore re-registration? yes — applies_when must be a registered filterable array.
- Reversal: feature-flag the never_filter rule; revert to prior ranking if false-positive
  caution rate degrades usability (measure before flipping default).

## 8. Open questions
- Blocked on schema_recommendations.md §9 Q2 (state vocabulary) and Q9 (contraindication breadth).
```

---

## Staleness (per ORCHESTRATOR §8)

- **Last reconciled:** 2026-07-20.
- This template tracks the high-stakes field list in `ORCHESTRATOR.md §6` and the vocabulary in `config/rta_v1.json`. If either changes, update the Validation Gate block and re-date this line.
- Mark any contradicted line `#STALE — <reason>`; do not silently trust or delete.
