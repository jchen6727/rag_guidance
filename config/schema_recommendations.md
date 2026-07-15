# Schema Recommendations: Corpus Tagging & Retrieval for Real-Time Therapeutic Analysis (RTA)

## 0. Framing: two clocks, two indices

Before adding labels, separate the two problems your architecture actually has, because they impose different constraints and want different index structures.

<NOTE>: should motivational interviewing be a "therapeutic modality" that is preloaded or retrieved by event?

- **The session-context clock (slow, warm):** presenting condition, modality, treatment plan. Known *before* the session. This should drive a **pre-filtered, pre-loaded working set** — not a live query. When a CBT-for-depression session starts, the retrievable corpus should already be narrowed to `CBT ∪ MI` × `depression` and warmed in the vector store / cache. Nothing about this needs to be fast because it happens at session setup.
- **The event clock (fast, cold):** the event detector fires mid-utterance and you need a document in front of the analysis LLM in near-real-time. This is where latency budget is spent, and it should query *into the already-narrowed working set*, not the whole corpus.

Almost every schema decision below is really a decision about **which clock a label serves**. A label that's known before the session should be a *partition/filter key* (cheap, pre-applied). A label that's only known at event time should be a *query-time predicate*. Mixing them is the main way these pipelines get slow. Keep this split in mind as the organizing principle for the rest of the document.

Concretely: **modality and clinical_presentation are session-clock filters. session_event_tags are event-clock predicates. Your `recommendation_level` question is really a question about which clock it belongs to — and the answer is "both, but for different values," which is why the flat enum feels wrong.** More on that in §2.

---

## 1. Additional schema labels to consider

### 1.1 Structural / provenance labels (chunk metadata, not clinical semantics)

These don't change retrieval logic much but materially change *trust, precedence, and debuggability*. You will want them the first time two chunks conflict.

| Label | Type | Purpose |
|---|---|---|
| `source_id` | string | Canonical source (e.g., `resick_cpt_manual_2017`). Enables source-level precedence and citation-back to clinicians. |
| `source_authority` | enum: `manual`, `peer_reviewed`, `practice_guideline`, `secondary_text`, `expert_annotation` | Lets retrieval and the analysis LLM prefer a treatment manual over a survey chapter when both match. Critical for safety content. |
| `evidence_tier` | enum: `established`, `probably_efficacious`, `emerging`, `expert_opinion` | Separates "this is APA Div12-supported" from "one RCT." Prevents the analysis LLM from asserting weak recommendations with manual-level confidence. |
| `chunk_kind` | enum: `procedure`, `rationale`, `verbatim_script`, `case_example`, `decision_rule`, `contraindication`, `assessment_item`, `psychoeducation` | Arguably the single highest-value addition below. See §1.2. |
| `granularity` | enum: `atomic_technique`, `session_segment`, `protocol_overview` | Lets you retrieve a one-line decision rule for a fast event vs. a full protocol section for analysis. |

### 1.2 `chunk_kind` — why this is the highest-leverage addition

Your current schema tells you *what a chunk is about* (modality, presentation, event) but not *what kind of thing it is*. At event time, the analysis LLM almost never wants "a passage about ruptures" — it wants **a decision rule or a verbatim repair script it can act on in seconds**, not three paragraphs of theory about the working alliance.

`chunk_kind` lets you rank actionable chunks (`decision_rule`, `verbatim_script`, `contraindication`, `procedure`) ahead of explanatory ones (`rationale`, `psychoeducation`) at event time, and do the reverse when the clinician later asks "why did you suggest that?" This one label probably buys you more perceived real-time quality than any additional clinical tag, because it fixes the "right topic, useless form" failure mode.

### 1.3 Clinical-semantic labels worth adding

<NOTE>: is `intervention_phase` something triggered
- **`intervention_phase`** (enum: `early`, `active`, `consolidation`, `relapse_prevention`, `phase_agnostic`). PE and CPT content is strongly phase-dependent; an early-phase psychoeducation chunk is wrong to surface mid-exposure. Cheap to apply, prevents phase-inappropriate retrieval. If your sessions carry a "session N of protocol" marker, this becomes a session-clock filter too.
- **`prerequisite_state`** (array, e.g., `stabilization_established`, `distress_tolerance_present`). Encodes "don't do trauma processing before X." This is the machine-readable backbone of contraindication logic (see §2).
- **`population_scope`** (array: `adult`, `adolescent`, `older_adult`, ...). Even if out of current scope, tagging it now costs little and prevents silent misapplication later.
- **`bfrb` and `dissociative_disorders` in `clinical_presentation`.** Your description text already calls these out, but they are **not in the enum**. Add them. `dissociative_disorders` in particular has a distinct mid-session presentation (part switching) that your event detector arguably should recognize — see §1.4.

### 1.4 Additional `session_event_tags` to consider

Your current set (`rupture`, `crisis_escalation`, `decompensation`, `disclosure_SI`, `none`) is a good spine but has gaps and one ambiguity.

# NOTE - removed dissociative disorders, removed part_switching.
Recommended additions:

- `disclosure_HI` — homicidal ideation / risk to others. Distinct duty-to-protect / Tarasoff pathway; must not be collapsed into `disclosure_SI`.
- `disclosure_abuse` — mandated-reporting trigger (child/elder/vulnerable adult). Different action path entirely.
- `dissociation` / `part_switching` — mid-session decompensation-adjacent but with a distinct response (grounding, not processing). Pairs with the `dissociative_disorders` presentation.
- `avoidance_in_session` — task refusal / exposure non-engagement. High-frequency, drives a specific repair, easy to miss.
- `substance_intoxication` — patient presenting intoxicated changes what's clinically permissible this session.
- `nonadherence` / `homework_incomplete` — softer, but a common analysis trigger.
- `motivational_ambivalence` — the canonical **MI cross-cutting trigger**; when this fires you want MI content retrieved *regardless of primary modality*.

Two structural notes on the event enum:

1. **`decompensation` and `crisis_escalation` overlap.** Decide whether these are severity levels of one axis or genuinely different events, and write that boundary into the ingestion prompt. If you don't, your ingestion LLM will tag inconsistently and your detector will be trained/prompted against a fuzzy target. Consider splitting into an `event_type` + `severity` pair rather than one flat enum (see §4, Alt C).
2. **`none` as a default array member is fine for ingestion but is a smell at detection time.** At detection, "no event" should be the *absence* of a fired tag, not a positively retrieved `none` chunk. Make sure `none`-tagged chunks are never retrievable targets — they're just ingestion bookkeeping.

### 1.5 A `directionality` / `valence` label (this answers your `recommendation_level` question)

See §2. Short version: yes, you want this, but not as a flat `mandatory / recommended / contraindicated` enum on the chunk.

---

## 2. `recommendation_level` and contraindications — the retrieval-logic question

Your instinct that a flat `contraindicated` enum feels wrong is correct. Here's the underlying reason and three viable designs.

### 2.1 Why flat `recommendation_level` breaks

`mandatory` / `recommended` / `contraindicated` is not a property of a chunk in isolation — it's a property of a **(chunk, context) pair**. "Exposure" is mandatory in PE-for-PTSD, contraindicated in acute suicidal crisis, and irrelevant in IPT-for-grief. A single scalar on the chunk can't express that. The moment you write `recommendation_level: contraindicated` you have to ask "contraindicated *for what?*" — which is exactly the `contraindicated_for_X` intuition you had.

So the label should be **relational**, and the retrieval question is: *what is X, and when is X known?*

### 2.2 The three retrieval regimes for safety/directionality content

| Content class | When relevant | How to handle |
|---|---|---|
| **Mandatory-always (unconditional safety floor)** | Every session, e.g. SI risk-assessment procedure | **Pre-load unconditionally.** Don't retrieve — inject into the analysis LLM's working context at session start. If it's mandatory for *all* sessions, it should never depend on a query firing. |
| **Contraindication-as-guardrail (tied to an event/state)** | Only when a specific state/event holds | **Retrieve at event time, triggered by the state, not the modality.** This is your `contraindicated_for_X`, but modeled as a *link to a state/event tag*, not a free-text X. |
| **Modality-standard-of-care (mandatory-within-modality)** | Whenever that modality is active | **Session-clock filter.** Pre-load with the modality working set. "Mandatory for CPT" is just "part of the CPT working set flagged high-priority." |

The key realization: **your three `recommendation_level` values don't live on the same clock.** `mandatory-always` → pre-load. `mandatory-within-modality` → session filter. `contraindicated` → event predicate. Forcing them into one enum is what created the awkwardness.

### 2.3 Recommended design: split into two orthogonal labels

Replace the single `recommendation_level` with:

```jsonc
"directionality": {
  "type": "string",
  "enum": ["indicated", "contraindicated", "cautionary", "neutral"],
  "description": "Does this chunk describe doing something, avoiding something, or a caution? Chunk-intrinsic — does NOT encode for-whom."
},
"applies_when": {
  "type": "array",
  "description": "The states/events/contexts under which this chunk's directionality is active. References the SAME controlled vocab as session_event_tags + clinical_presentation + a small state vocab (e.g. acute_suicidality, intoxication, insufficient_stabilization). Empty = applies whenever the modality is active.",
  "items": { "type": "string" },
  "default": []
}
```

Now:
- A CPT contraindication for active SI is `directionality: contraindicated`, `applies_when: ["acute_suicidality"]`, `therapeutic_modality: ["CPT"]`.
- Retrieval logic becomes uniform and clock-aware: **when event tag E fires, retrieve chunks where `E ∈ applies_when` — including contraindications — and rank `directionality: contraindicated` and `chunk_kind: contraindication` to the top.** No special-casing.
- "Mandatory-always" content is simply `applies_when: []` + a `pre_load: true` flag (or `granularity: protocol_overview` + high `source_authority`) and handled by the session-start injector, not the retriever.

This is strictly more expressive than `contraindicated_for_X` (X becomes a controlled vocabulary shared with your event/presentation enums, so it's queryable and consistent) and avoids a combinatorial explosion of `contraindicated_for_*` boolean columns.

### 2.4 One safety-specific rule

For contraindications, **retrieval recall matters more than precision, and a miss is asymmetrically costly.** Consider tagging contraindication chunks so they're retrievable by a *broader* net than normal content (e.g., a contraindication that applies to any trauma-processing modality is tagged with all of `{PE, CPT}` rather than requiring an exact match). Better to surface an over-broad safety caution the analysis LLM can discard than to miss it under latency pressure.

---

## 3. How each label interacts with the three LLMs

Think of every label as having an **author** (who writes it), a **consumer** (who reads it), and a **clock** (when it's used). This table is the contract.

| Label | Ingestion LLM (author) | Detection LLM (consumer) | Analysis LLM (consumer) | Clock |
|---|---|---|---|---|
| `therapeutic_modality` | Assigns per chunk from source context | — (detector is modality-agnostic; it watches events, not modality) | Session filter, pre-applied | Session |
| `clinical_presentation` | Assigns per chunk | — | Session filter, pre-applied | Session |
| `session_event_tags` | Assigns "this chunk *addresses* event E" | Emits "event E *is happening*" — **note: same vocab, opposite meaning** | Uses emitted E to query | Event |
| `directionality` + `applies_when` | Assigns | — | Ranks contraindications up when `applies_when` matches fired event | Event |
| `chunk_kind` | Assigns | — | Ranks actionable kinds up at event time; explanatory kinds up for post-hoc "why" | Event |
| `source_authority` / `evidence_tier` | Assigns | — | Precedence when chunks conflict; confidence calibration | Both |
| `intervention_phase` / `prerequisite_state` | Assigns | — | Filters phase-inappropriate content if session phase known | Session/Event |

### 3.1 The critical ingestion/detection vocabulary split

`session_event_tags` is used by **both** the ingestion LLM and the detection LLM, **but they mean different things**:

- **Ingestion:** "this textbook chunk is *about how to handle* ruptures" → the chunk is a retrieval *target*.
- **Detection:** "a rupture *is occurring right now*" → this is a retrieval *trigger*.

They must share the same controlled vocabulary (so the trigger can match the target), but you should **prompt them as different tasks** and ideally document them as two schemas over one enum. A frequent bug: teams write one prompt and get an ingestion LLM that tries to detect events in textbooks, or a detector that tags "aboutness." Keep the enum shared, keep the prompts and few-shot examples separate.

### 3.2 Detection LLM should stay thin

The detector's only job is to emit event tags (+ confidence + span) fast. It should **not** do modality reasoning, retrieval, or contraindication logic — those belong to the analysis LLM operating over the pre-narrowed working set. Every label except `session_event_tags` is invisible to the detector. This keeps the fast path fast.

### 3.3 Ingestion LLM: enforce the label contract at write time

Multi-label ingestion is where silent corpus rot happens (you've already lived the "silent RAG ingestion failures" version of this). Recommendations:

- **Validate every emitted tag against the enum**; reject/flag out-of-vocab (this alone catches a large class of failures).
- **Require a rationale field per non-obvious tag** during ingestion QA, then drop it from the production index. Cheap way to audit tagging quality on a sample.
- **Make `directionality` and `applies_when` co-required:** a `contraindicated` chunk with empty `applies_when` is almost always a tagging error (contraindicated *for whom/when?*) and should be flagged.
- **Track tag density.** A chunk tagged with 8 modalities is usually a mis-chunked protocol-overview, not a genuinely universal passage. Density outliers are your ingestion-QA queue.

---

## 4. Questions for the clinicians (ranked by structural impact)

These are ordered so the earliest questions are the ones that most change the *shape* of the schema, not just its values.

1. **Segregation boundaries — the single most structural question.** Your description hints at `CBT AND NOT DBT`. Which modality pairs are genuinely non-interchangeable (retrieving one during the other is an error), which are complementary (fine to co-retrieve), and which are strictly cross-cutting like MI? This determines whether modality is a hard filter, a soft ranking boost, or an overlay. Get them to draw the actual N×N compatibility matrix, not just list modalities. *(See Alt A below for what changes.)*
2. **What must be pre-loaded every session regardless of event?** This defines the `mandatory-always` set and pulls that content *out* of the retrieval path entirely. Directly determines your latency budget. Ask: "What should the system always have in front of it, even if nothing happens?"
3. **Event taxonomy boundaries and severity.** Is `decompensation` a distinct event from `crisis_escalation`, or a severity of one? Do they want `event_type` + `severity` separated? Where exactly is the rupture / crisis / decompensation line? Fuzzy answers here propagate into inconsistent ingestion tagging *and* an under-specified detector. *(See Alt C.)*
4. **Contraindication states vocabulary.** What are the concrete states that gate content (acute SI, intoxication, insufficient stabilization, active dissociation, ...)? This becomes the `applies_when` state vocab and is the backbone of §2.
5. **Recall/precision asymmetry per event.** For which events is a missed retrieval clinically unacceptable (favor recall, over-retrieve) vs. which are low-stakes (favor precision, keep it terse)? This sets per-event retrieval thresholds — a false-negative on `disclosure_SI` is categorically worse than on `homework_incomplete`.
6. **Duty-based events.** Do HI, abuse disclosure, and grave-disability need distinct pathways from SI? (Almost certainly yes — different legal/action logic.) Confirms the §1.4 additions.
7. **Source precedence.** When a treatment manual and a review chapter disagree, which wins? Populates `source_authority` ordering and the analysis LLM's conflict-resolution rule.
8. **Phase-dependence.** Which modalities have content that's actively *wrong* out of phase (PE, CPT, DBT skills sequence)? Determines whether `intervention_phase` is a must-have filter or a nice-to-have.
9. **Actionability at event time.** When an event fires, do they want a terse decision rule / script first, or the full rationale? Confirms `chunk_kind` ranking policy and shapes the analysis LLM's output format.

---

## 5. Illustrative alternatives (how clinician answers change performance)

Each shows a fork where the *answer to a §4 question* flips the architecture, with the performance consequence.

### Alt A — Modality as hard filter vs. soft boost (driven by Q1)

**If clinicians say modalities are strictly segregated** (`CBT AND NOT DBT` is a real rule):
- Modality is a **hard pre-filter partition**. Working set = exactly the active modality (∪ MI). Smaller index → **faster event-time queries, lower recall risk of cross-contamination**, but **zero ability to surface a genuinely useful DBT distress-tolerance skill during a CBT session** even when clinically apt.

**If clinicians say modalities are complementary:**
- Modality becomes a **soft ranking boost** over a shared index. **Broader, more flexible retrieval** (that DBT skill can surface), but **larger candidate set → higher latency and more cross-modality noise** the analysis LLM must filter.

*Performance consequence:* hard-filter optimizes latency and safety-of-fit at the cost of clinical flexibility; soft-boost does the reverse. You cannot pick correctly without Q1. A likely answer is **hybrid**: hard-partition a few genuinely incompatible pairs, soft-boost the rest, always-include MI — which is only implementable if you've captured the compatibility matrix, not a flat list.

### Alt B — Contraindications: flat enum vs. `directionality + applies_when` (driven by Q4, §2)

**Flat `recommendation_level: contraindicated`:**
- Simple to author. But at event time you can't tell *which* contraindications apply, so you either surface all contraindications (noise, latency) or none (danger). Ingestion also can't validate "contraindicated for what," so tagging quality degrades silently.

**`directionality` + `applies_when` referencing shared event/state vocab:**
- Event `acute_suicidality` fires → retrieve `applies_when ∋ acute_suicidality`, contraindications rank to top, uniform logic, auditable. Costs more careful ingestion (co-required fields) and a maintained state vocabulary.

*Performance consequence:* the flat version is faster to build and **actively unsafe or noisy** at runtime; the relational version front-loads ingestion effort to get **precise, low-latency, auditable contraindication surfacing**. For a system where a missed contraindication is the worst failure, the relational design is the one that survives clinical review.

### Alt C — Event enum: flat vs. `event_type × severity` (driven by Q3)

**Flat enum** (`rupture`, `crisis_escalation`, `decompensation`, ...):
- Detector emits one label. Simple. But `crisis_escalation` vs `decompensation` blur, the detector's decision boundary is ill-defined, and you can't tune retrieval by severity (a mild rupture and a session-ending rupture pull the same content).

**Two-axis** (`event_type: rupture|risk_disclosure|disengagement|...` + `severity: low|moderate|acute`):
- Detector emits type + severity. Retrieval and the analysis LLM can escalate: acute → over-retrieve + surface safety floor; low → terse single decision rule. Detector prompt is cleaner (two smaller decisions).

*Performance consequence:* flat is cheaper to detect but **caps how well retrieval can match clinical urgency and wastes latency budget uniformly**; two-axis lets you **spend latency where stakes are high and stay terse where they aren't**, at the cost of a slightly heavier detector and a more careful ingestion vocabulary. If clinicians see decompensation as "severe crisis" rather than a different phenomenon, two-axis is clearly right.

### Alt D — `chunk_kind` present vs. absent (driven by Q9)

**Without `chunk_kind`:**
- Event fires, retriever returns topically correct chunks that are 60% rationale/psychoeducation. Analysis LLM must read and discard prose under time pressure → **slower, and more likely to hand the clinician theory instead of an action**.

**With `chunk_kind`:**
- Rank `decision_rule` / `verbatim_script` / `contraindication` first at event time; hold `rationale` for the post-hoc "why." **Faster time-to-actionable-output and better-fit real-time UX**, at the cost of one more ingestion label.

*Performance consequence:* this is the label most directly tied to *perceived* real-time quality. Same corpus, same latency budget — but the difference between "here's what to say" and "here's a paragraph about the working alliance" mid-crisis is entirely `chunk_kind`.

### Alt E — Pre-load-heavy vs. retrieve-everything (driven by Q2)

**Retrieve everything on event** (including safety floor):
- Minimal pre-load, but every event pays retrieval latency for content that's identical every session, and a retrieval miss can drop the *mandatory* safety procedure. **Fast to build, fragile under latency and failure.**

**Pre-load the mandatory-always set at session start:**
- Safety floor and modality standard-of-care are in-context before anything fires; event-time retrieval only fetches the *conditional, event-specific* delta. **Smaller, faster event queries and no way to "miss" mandatory content**, at the cost of a session-setup step and more context budget spent up front.

*Performance consequence:* pre-loading trades a warm-start cost for a **shorter, safer critical path** — the right trade for near-real-time + safety-critical. But it's only definable once clinicians answer "what must always be present," which is why Q2 ranks so high.

---

## 6. Summary of concrete recommendations

- **Organize the whole schema around two clocks:** session-clock filters (modality, presentation, phase) pre-applied and warmed; event-clock predicates (event tags, `applies_when`) queried live into the narrowed set.
- **Add `chunk_kind`** — highest leverage for real-time actionability.
- **Replace flat `recommendation_level` with `directionality` + `applies_when`** over a shared event/state vocabulary; handle mandatory-always via pre-load, mandatory-within-modality via the session filter, contraindications via event-triggered retrieval.
- **Add provenance labels** (`source_authority`, `evidence_tier`, `source_id`) for conflict precedence and confidence calibration.
- **Fix the enum gaps:** add `bfrb` and `dissociative_disorders` to `clinical_presentation` (already in your prose, missing from the enum); expand `session_event_tags` (HI, abuse, dissociation, avoidance, intoxication, ambivalence) and resolve the `decompensation`/`crisis_escalation` boundary, likely via `event_type × severity`.
- **Treat `session_event_tags` as one vocabulary with two authoring tasks** (ingestion "aboutness" vs. detection "occurrence"); prompt them separately, validate against the enum at ingestion, never make `none` a retrievable target.
- **Keep the detector thin** — event tags + confidence + span only; all modality/contraindication reasoning lives in the analysis LLM over the pre-narrowed set.
- **Take the §4 questions to clinicians in order** — Q1 (segregation matrix), Q2 (mandatory-always set), Q3 (event boundaries/severity), and Q4 (contraindication states) each fork the architecture, per §5.
