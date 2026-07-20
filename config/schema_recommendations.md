# Schema Recommendations: Corpus Tagging & Retrieval for Real-Time Therapeutic Analysis (RTA)

> **Revision 2 — reviewed against `rta_v1.json` (2026-07-13).**
> Sections 0–5 are the original analysis, now annotated inline with **#DONE**, **#PARTIAL**, **#TODO**, and **#DROPPED** reflecting what `rta_v1.json` implements.
> **New in this revision:** §7 (gap analysis of `rta_v1.json`, including one blocking defect), §8 (answers to the open NOTE/TODO questions in `changelog.md`), §9 (directed clinician questions, revised).
> Companion doc: `summary.md` — implementation guidance for programming agents.

---

## Status legend

| Marker | Meaning |
|---|---|
| **#DONE** | Implemented in `rta_v1.json` as recommended. |
| **#PARTIAL** | Implemented, but with a gap that needs closing (see §7). |
| **#TODO** | Not yet implemented; still recommended. |
| **#DROPPED** | Deliberately out of scope. Rationale recorded so it isn't relitigated. |

## 0. Framing: two clocks, two indices

Before adding labels, separate the two problems your architecture actually has, because they impose different constraints and want different index structures.

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

**Status against `rta_v1.json`:**

- `source_id` — **#PARTIAL.** `doc_id` (SHA-256 of PDF bytes) is a *stable* identifier but not a *human-readable* one. It's sufficient for dedup/re-ingestion, insufficient for a clinician reading a citation. Add a `source_id` slug alongside, or accept that citation-back requires a `doc_id → title` lookup table. Low cost either way.
- `source_authority` — **#PARTIAL / renamed.** `doc_type` (`treatment_manual` / `textbook` / `clinical_guideline` / `other`) is doing this job and is a reasonable proxy: manual > guideline > textbook is a defensible precedence order. But it is *not documented as a precedence order anywhere*, so the analysis LLM has no basis to prefer one over another. **#TODO:** state the precedence explicitly in the field description (see §7.3).
- `evidence_tier` — **#DROPPED.** `evidence_base` was removed in the RTA scope pruning pass. Defensible: RTA operates on manuals and guidelines, not primary literature, so tier discrimination has little to bite on. Revisit only if the corpus expands to RCT/meta-analytic sources. Note `year_published` partially covers "prefer current guidance."
- `chunk_kind` — **#TODO. Still the single highest-value missing field.** See §1.2 and §7.2; this remains the top open recommendation.
- `granularity` — **#TODO (lower priority).** Partly subsumed by `chapter` (session-numbered manuals) but not queryable as a retrieval control.

### 1.2 `chunk_kind` — why this is the highest-leverage addition — **#TODO (top open item)**

Your current schema tells you *what a chunk is about* (modality, presentation, event) but not *what kind of thing it is*. At event time, the analysis LLM almost never wants "a passage about ruptures" — it wants **a decision rule or a verbatim repair script it can act on in seconds**, not three paragraphs of theory about the working alliance.

`chunk_kind` lets you rank actionable chunks (`decision_rule`, `verbatim_script`, `contraindication`, `procedure`) ahead of explanatory ones (`rationale`, `psychoeducation`) at event time, and do the reverse when the clinician later asks "why did you suggest that?" This one label probably buys you more perceived real-time quality than any additional clinical tag, because it fixes the "right topic, useless form" failure mode.

> **Status: #TODO — not present in `rta_v1.json`.**
> `technique_tags` is the nearest thing in the current schema, but it answers *"which technique is named here"* not *"is this passage actionable."* A chunk tagged `technique_tags: ["imaginal exposure"]` could equally be a step-by-step script or three paragraphs on why exposure works — and at event time those are not interchangeable.
>
> This is the one recommendation from Revision 1 that was neither implemented nor consciously rejected in the changelog, so it appears to have fallen through rather than been decided against. It is worth an explicit accept/reject decision. Cost is one enum field at ingestion; benefit is the difference between the analysis LLM returning *"here is what to say"* versus *"here is a paragraph about the working alliance"* mid-crisis.

### 1.3 Clinical-semantic labels worth adding — **#DONE / #PARTIAL**

- **`intervention_phase`** — **#DONE**, implemented as `session_phase` (`early_treatment` / `mid_treatment` / `late_treatment` / `termination` / `crisis` / `any`). Good design choices: `any` as default (fails open rather than over-filtering) and `crisis` as an explicit phase-agnostic escape hatch. See §8.2 for the open question of whether this is a preload or an event filter. One defect: the description references `pre_intake_consultation`, which is **not in the enum** (see §7.1).
- **`prerequisite_state`** — **#DONE by substitution.** Superseded by `applies_when`, which is strictly more general: `applies_when: ["insufficient_stabilization"]` expresses the same constraint while sharing one vocabulary with events and presentations. Correct call — do not add `prerequisite_state` separately. But this makes defining the state vocabulary a **hard blocker**, since `applies_when` is currently an unconstrained string array (§7.2).
- **`population_scope`** — **#DONE**, implemented as `patient_population` (15 values, default `["not_specified"]`). Broader than recommended, which is fine. Note the description still calls it a *"ranking moderator when filtering `evidence_base`"* — a field that no longer exists (§7.3).
- **`bfrb` / `dissociative_disorders` in `clinical_presentation`** — **#DROPPED by clinician decision**, per your note. Rationale recorded so it isn't relitigated. **One consequence to be aware of:** `dissociation` remains in `session_event_tags`, so the system can now *detect* dissociation mid-session but has no *presentation* category to route it to, and `clinical_presentation` has no `dissociative_disorders` bucket to retrieve into. This is coherent only if dissociation is treated purely as a transient event within trauma work (grounding response, no dedicated corpus). Worth confirming with clinicians rather than assuming — see §9, Q3.

### 1.4 Additional `session_event_tags` to consider — **#DONE (mostly)**

Your current set (`rupture`, `crisis_escalation`, `decompensation`, `disclosure_SI`, `none`) is a good spine but has gaps and one ambiguity.

Recommended additions:

- `disclosure_HI` — **#DONE.**
- `disclosure_abuse` — **#DONE.**
- `dissociation` — **#DONE.** (`part_switching` not added; consistent with dropping `dissociative_disorders`.)
- `avoidance_in_session` — **#DONE.**
- `substance_intoxication` — **#TODO — not added.** This is the one recommended event tag that is missing, and it's the one with the strongest *state* character: intoxication changes what is clinically permissible for the whole session, not just the moment. Note `SUD` exists in `clinical_presentation` and `substance_relapse_monitoring` in `risk_dimension_tags`, so the corpus can cover substance use — but there is no way to signal *"the patient is intoxicated right now."* Recommend adding it either as an event tag or (better) as a state in the `applies_when` vocabulary. See §9, Q2.
- `nonadherence` — **#DONE.**
- `motivational_ambivalence` — **#DONE.** See §8.1 for the MI preload-vs-retrieve question this raises.

**Also resolved: `decompensation` removed.** The changelog notes `crisis_escalation` and `decompensation` were "fuzzy and likely to be highly dual-tagged," and `decompensation` was cut. This is a reasonable resolution of the §1.4/Alt C ambiguity — one fewer boundary for the ingestion LLM to get wrong. Two consequences worth noting:

1. `psychotic_decompensation` survives in `risk_dimension_tags`, so slow-burn decompensation is now handled on the **monitoring** axis rather than the **event** axis. That is arguably the more correct split (decompensation is usually a trajectory, not a moment) — but it should be *stated* in the field descriptions, or ingestion will guess.
2. **Severity is now entirely unrepresented.** With `decompensation` gone, `crisis_escalation` is the sole acute-severity tag and carries no gradation. Alt C's `event_type × severity` proposal is therefore **#TODO, not resolved** — collapsing the enum removed the *ambiguity* but not the *missing axis*. See §9, Q4.

Two structural notes on the event enum:

1. **`decompensation` and `crisis_escalation` overlap.** Decide whether these are severity levels of one axis or genuinely different events, and write that boundary into the ingestion prompt. If you don't, your ingestion LLM will tag inconsistently and your detector will be trained/prompted against a fuzzy target. Consider splitting into an `event_type` + `severity` pair rather than one flat enum (see §4, Alt C).
2. **`none` as a default array member is fine for ingestion but is a smell at detection time.** At detection, "no event" should be the *absence* of a fired tag, not a positively retrieved `none` chunk. Make sure `none`-tagged chunks are never retrievable targets — they're just ingestion bookkeeping.

### 1.5 A `directionality` / `valence` label (this answers your `recommendation_level` question) — **#DONE**

See §2. Short version: yes, you want this, but not as a flat `mandatory / recommended / contraindicated` enum on the chunk.

**Implemented in `rta_v1.json`** as `directionality` + `applies_when`, replacing `practice_recommendation_level`. The pairing semantics are not yet enforced anywhere — see §7.2 and §8.3.

---

## 2. `recommendation_level` and contraindications — the retrieval-logic question — **#DONE (design) / #TODO (enforcement)**

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

### 2.4 One safety-specific rule — **#TODO**

For contraindications, **retrieval recall matters more than precision, and a miss is asymmetrically costly.** Consider tagging contraindication chunks so they're retrievable by a *broader* net than normal content (e.g., a contraindication that applies to any trauma-processing modality is tagged with all of `{PE, CPT}` rather than requiring an exact match). Better to surface an over-broad safety caution the analysis LLM can discard than to miss it under latency pressure.

> **Status: #TODO.** `rta_v1.json` has the right *fields* (`directionality`, `clinical_caution`) and the `clinical_caution` description states the principle well — *"a technique recommended without its documented contraindication is dangerous."* But a field description is not an enforcement mechanism. Nothing in the schema or notes specifies the broad-net tagging rule, and nothing guarantees the searcher won't drop a `contraindicated` chunk on a relevance threshold. This must be implemented in the searcher as a hard rule, not left to ranking. See `summary.md` §4.

---

## 3. How each label interacts with the three LLMs — **#PARTIAL**

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

**Revised table reflecting `rta_v1.json` field names.** Added rows cover fields introduced since Revision 1:

| Field | Ingestion LLM | Detection LLM | Analysis LLM | Clock |
|---|---|---|---|---|
| `doc_id`, `source_file`, `page_*`, `chunk_index` | Deterministic (not LLM) | — | Citation-back to clinician | — |
| `domain` | Doc-level, assigned once | — | Persona selection at session start | Session |
| `doc_type` | Doc-level | — | Precedence on conflict (**needs explicit ordering, §7.3**) | Both |
| `therapeutic_modality` | Chunk-level | — | Session pre-filter | Session |
| `clinical_presentation` | Chunk-level | — | Session pre-filter | Session |
| `session_event_tags` | "chunk is *about* E" | "E *is happening*" | Query predicate | Event |
| `session_phase` | Chunk-level | — | Session filter if session N known; `crisis` overrides | Session |
| `directionality` + `applies_when` | **Co-required pair** | — | Contraindication ranking on fired event | Event |
| `technique_tags` | Extracted names | — | Technique-specific lookup | Event |
| `clinical_caution` | Free-text extraction | — | **Must surface, never suppress** | Event |
| `risk_dimension_tags` | Chunk-level | — | **Passive background pass every session** — third clock, see below | Session (continuous) |
| `patient_population` | Chunk-level | — | Ranking moderator | Session |
| `clinical_measure_tags` | Normalized abbreviations | — | Instrument-specific guidance | Event |
| `missingness` | Inferred absence | — | Surfaced alongside content when non-empty | Both |
| `keywords`, `subdomain` | Extracted | — | Semantic recall support; not filterable | — |

### 3.0 `risk_dimension_tags` introduces a third clock

Revision 1 framed everything as session-clock or event-clock. `risk_dimension_tags` doesn't fit either: its description specifies a **passive background retrieval pass on every session, not only when `crisis_escalation` fires.** That is a third mode — continuous, low-priority, always-on.

Your changelog note reads: *"seems like risk_dimension_tags become more of a presentation problem — likely to already be retrieved per early chunk."* **This is correct and worth acting on.** If the working set is already narrowed by `clinical_presentation: ["suicidality"]` at session start, chronic-SI monitoring content is *already in context* — a separate background pass would re-retrieve what's already loaded, spending latency for nothing.

The distinction that makes the field earn its place: `clinical_presentation` says *what is being treated*; `risk_dimension_tags` says *what must be monitored regardless of what is being treated*. Those diverge for exactly the case that matters — a patient in IPT-for-grief with a chronic-SI history has `clinical_presentation: ["grief", "interpersonal"]` and would never retrieve SI-monitoring content through the presentation filter alone.

**Recommended resolution:** treat `risk_dimension_tags` as a **preload driven by the patient's risk profile**, not a background retrieval pass. At session start, inject monitoring content for that patient's active risk dimensions into the working set. This collapses the third clock back into the session clock, eliminates the recurring background query, and removes the failure mode where a background pass is skipped under load. See §9, Q5.

### 3.1 The critical ingestion/detection vocabulary split

`session_event_tags` is used by **both** the ingestion LLM and the detection LLM, **but they mean different things**:

- **Ingestion:** "this textbook chunk is *about how to handle* ruptures" → the chunk is a retrieval *target*.
- **Detection:** "a rupture *is occurring right now*" → this is a retrieval *trigger*.

They must share the same controlled vocabulary (so the trigger can match the target), but you should **prompt them as different tasks** and ideally document them as two schemas over one enum. A frequent bug: teams write one prompt and get an ingestion LLM that tries to detect events in textbooks, or a detector that tags "aboutness." Keep the enum shared, keep the prompts and few-shot examples separate.

### 3.2 Detection LLM should stay thin — **#TODO (architectural discipline, not a schema field)**

The detector's only job is to emit event tags (+ confidence + span) fast. It should **not** do modality reasoning, retrieval, or contraindication logic — those belong to the analysis LLM operating over the pre-narrowed working set. Every label except `session_event_tags` is invisible to the detector. This keeps the fast path fast.

### 3.3 Ingestion LLM: enforce the label contract at write time — **#TODO**

Multi-label ingestion is where silent corpus rot happens (you've already lived the "silent RAG ingestion failures" version of this). Recommendations:

- **Validate every emitted tag against the enum**; reject/flag out-of-vocab (this alone catches a large class of failures).
- **Require a rationale field per non-obvious tag** during ingestion QA, then drop it from the production index. Cheap way to audit tagging quality on a sample.
- **Make `directionality` and `applies_when` co-required:** a `contraindicated` chunk with empty `applies_when` is almost always a tagging error (contraindicated *for whom/when?*) and should be flagged.
- **Track tag density.** A chunk tagged with 8 modalities is usually a mis-chunked protocol-overview, not a genuinely universal passage. Density outliers are your ingestion-QA queue.

> **Status: #TODO — none of this is implemented.** `rta_v1.json` sets `additionalProperties: false`, which blocks *unknown fields* but does **not** validate enum membership of array items at write time, nor enforce the `directionality`/`applies_when` pairing, nor constrain `applies_when` to any vocabulary at all. Your changelog asks directly: *"how should we design the ingestion and retrieval scripts to know that these two are PAIRED?"* — answered in §8.3, with implementation in `summary.md` §3.

---

## 4. Questions for the clinicians (ranked by structural impact) — **superseded by §9**

> Retained for traceability. Q1 (segregation matrix), Q2 (mandatory-always set), Q3 (event boundaries), and Q4 (contraindication states) remain **open**; Q6 (duty-based events) is **#DONE**. Revised and re-prioritized list in §9.

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

## 5. Illustrative alternatives (how clinician answers change performance) — **still live**

> All five forks remain open. Alt B is now **decided** (relational design implemented); Alt A, C, D, E remain unresolved and are driven by the §9 questions.

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

## 6. Summary of Revision 1 recommendations — status roll-up

| Recommendation | Status | Note |
|---|---|---|
| Two-clock architecture (session vs. event) | **#PARTIAL** | Schema supports it; no evidence the searcher implements pre-filtering vs. query-time separation. A third (continuous) clock appeared via `risk_dimension_tags` — see §3.0. |
| Add `chunk_kind` | **#TODO** | **Top open item.** Neither implemented nor rejected. |
| Replace `recommendation_level` with `directionality` + `applies_when` | **#DONE** | Pairing not enforced (§7.2). |
| Provenance labels (`source_authority`, `evidence_tier`, `source_id`) | **#PARTIAL / #DROPPED** | `doc_type` + `year_published` proxy; precedence undocumented. |
| Add `bfrb`, `dissociative_disorders` to presentations | **#DROPPED** | Clinician decision. Residual `dissociation` event tag — see §9 Q3. |
| Expand `session_event_tags` | **#DONE** | Except `substance_intoxication`. |
| Resolve `decompensation` / `crisis_escalation` | **#DONE** | Resolved by deletion; severity axis still missing (§9 Q4). |
| `event_type × severity` split | **#TODO** | Alt C unresolved. |
| Shared vocab, two authoring tasks | **#TODO** | Documented in `domain_vs_modality` note for one field pair only. |
| Keep detector thin | **#TODO** | Architectural; not verifiable from schema. |
| Ingestion validation at write time | **#TODO** | See §7.2. |

---

## 7. Gap analysis of `rta_v1.json`

Ordered by severity. §7.1 is blocking.

### 7.1 BLOCKING — the file is not valid JSON

There is a **trailing comma** after the `missingness` property block (line 251), immediately before the closing brace of `properties`:

```jsonc
    "missingness": {
      ...
      "default": []
    },        <-- trailing comma
  },
  "additionalProperties": false,
```

`json.load()` fails with `Expecting property name enclosed in double quotes: line 252 column 3`. Any script that reads this schema — ingestion, DataStore registration, validation — will crash on load. Strict JSON permits no trailing commas.

**Fix:** delete the comma. Then add a CI check that parses every schema file on commit; this class of defect should never reach review. (`summary.md` §6.)

### 7.2 CRITICAL — `applies_when` has no controlled vocabulary

`applies_when` is declared as:

```json
"items": { "type": "string" }
```

Its description says it references *"the SAME controlled vocab as `session_event_tags` + `clinical_presentation` + a small state vocab (e.g. `acute_suicidality`, `intoxication`, `insufficient_stabilization`)"* — but **that vocabulary exists nowhere in the schema.** The state terms appear only as prose examples inside a description string.

Consequences, all of which are silent failures:

1. **Ingestion will drift.** The LLM will emit `acute_SI`, `active_suicidality`, `suicidal_crisis`, `acute_suicidality` across chunks. All validate. None match each other.
2. **Retrieval will silently under-return.** The searcher queries `applies_when CONTAINS "acute_suicidality"`; chunks tagged `active_suicidality` never match. **For contraindications, this is a patient-safety failure that produces no error** — the query succeeds and returns fewer results.
3. **The `directionality`/`applies_when` pairing is unenforceable** without a closed vocabulary to validate against.

This is the highest-severity design gap, because it degrades exactly the safety-critical path §2.4 was written to protect.

**Fix:** define an explicit `state_vocab` and constrain `applies_when` to the union of three closed enums. Concretely — add a `$defs` block and reference it:

```jsonc
"$defs": {
  "state_vocab": {
    "enum": [
      "acute_suicidality", "intoxication", "insufficient_stabilization",
      "active_dissociation", "acute_psychosis", "medical_instability",
      "cognitive_impairment", "active_self_harm"
    ]
  }
}
```

then set `applies_when.items` to `oneOf` the three enums (events ∪ presentations ∪ states). Validation becomes mechanical, and the state list becomes a **direct clinician question** (§9, Q2) rather than an implicit assumption.

### 7.3 Stale references — descriptions and notes cite fields that no longer exist

The pruning pass removed fields but left the prose referring to them. Every one of these is a live instruction to the ingestion LLM if descriptions are used for prompting (which the schema's own notes say they are).

| Location | Dangling reference | Impact |
|---|---|---|
| `patient_population.description` | *"when filtering `evidence_base` IN [rct_primary, ...]"* | Instructs the LLM to condition on a removed field. |
| `session_phase.description` | `pre_intake_consultation` described but **not in enum** | LLM told a value exists that it cannot emit. |
| `notes.routing_safety` | `corpus_scope`, `asa_only`, `target_audience`, `homework_resource`, `analysis_function` | Entire note describes removed routing. Actively misleading. |
| `notes.vertex_ai_search` | `analysis_function`, `outcome_measure_tags`, `population_focus`, `setting`, `presentation_coverage`, `intended_use_context`, `source_language` | Registration checklist lists 7 nonexistent fields. |
| `notes.representation_and_implementation_fields` | 9 fields, **all removed** | Note is entirely obsolete. |
| `notes.recommended_change_items` | `bfrb`, `dissociative_disorders`, `autism_spectrum`, `health_anxiety`, `shame_activation`, `practice_recommendation_level`, `use_with_caution`, + ~15 more | Describes values not in any enum. |
| `clinical_measure_tags.description` | `analysis_function=outcome_monitoring` | Routing target no longer exists. |
| `session_event_tags.description` | ends mid-sentence: *"Primary real-time retrieval trigger for the RTA pipeline. Motivational"* | Truncated. Likely a dropped MI clarification. |

The schema's own `priority_for_reviewer` note flags this (*"these notes are likely out of date"*) — this section is the itemized version. **Recommendation: delete `notes.routing_safety`, `notes.representation_and_implementation_fields`, and `notes.recommended_change_items` outright** (changelog is the correct home for change history), rewrite `notes.vertex_ai_search` against the actual 24 fields, and fix the three field descriptions.

### 7.4 `doc_type` precedence is undefined

`doc_type` is the de facto `source_authority` but no ordering is stated. When a `treatment_manual` and a `textbook` conflict, the analysis LLM has no principled basis to choose. **Fix:** state the precedence in the description (suggested: `treatment_manual` > `clinical_guideline` > `textbook` > `other`, with `year_published` as tiebreaker) and confirm with clinicians (§9, Q6).

### 7.5 `domain` / `therapeutic_modality` overlap is asserted but not constrained

The `domain_vs_modality` note correctly distinguishes doc-level from chunk-level. But nothing prevents `domain: "interpersonal_therapy"` + `therapeutic_modality: ["CBT"]` on the same chunk. That combination may be legitimate (an IPT text discussing CBT contrast) or an ingestion error, and there is no way to tell them apart. Consider a soft validation warning on domain/modality mismatch, routed to the QA queue rather than blocking ingestion.

Note also `emdr_therapy` is in the `domain` enum but has **no corresponding `therapeutic_modality` value** — EMDR was excluded from the CBT/DBT/IPT competence scope. Either remove `emdr_therapy` from `domain` or document why a domain exists with no retrievable modality.

### 7.6 Minor

- **`clinical_caution` (free text) vs. `directionality: contraindicated` overlap.** Two mechanisms encode contraindications: one structured, one free-text. A chunk could carry `clinical_caution` text while `directionality: "indicated"`. Document which is authoritative for retrieval (recommend: `directionality` + `applies_when` drives *retrieval*; `clinical_caution` is *display* text surfaced alongside).
- **`directionality` has no default and is not in `required`.** So it may be absent. Either add `"default": "neutral"` or add it to `required`. Currently underspecified.
- **`missingness` for RTA.** Your changelog asks whether an ingestion LLM can reliably infer absence. Honest answer: **not reliably.** Inferring what a text *doesn't say* is a much harder task than extraction, and LLMs confabulate here. It's also unclear what RTA does with it at speed. Recommend deferring — see §8.4.
- **`clinical_measure_tags` has 27 values including `Columbia` and `C-SSRS`**, which are the same instrument. Normalize to one.
- **`chapter` is high-value and under-used.** For session-numbered manuals it is nearly a free `session_phase` signal; consider deriving `session_phase` from it during ingestion where parseable.

---

## 8. Answers to the open NOTE/TODO items in `changelog.md`

### 8.1 Should MI be a preloaded modality or retrieved on `motivational_ambivalence`?

**Recommendation: both, and they are not in conflict — because they serve different clocks.**

The question presents a false choice. MI is currently in `therapeutic_modality` *and* has a `motivational_ambivalence` event tag, and that dual representation is correct:

- **Preload a thin MI layer (session clock).** MI's core stance — reflective listening, rolling with resistance, avoiding the righting reflex — is *always* applicable and never contraindicated. A small always-on set costs little context and is available at zero latency.
- **Retrieve specific MI technique content on the event (event clock).** Sustain-talk handling, decisional balance, change-talk elicitation are only useful when ambivalence actually surfaces. Retrieving these speculatively wastes working-set budget.

Your changelog leans toward *"likely not its own therapeutic modality but detection is sufficient."* I'd push back mildly: **removing MI from `therapeutic_modality` would make the always-applicable stance content unretrievable by modality filter**, forcing it into `psychotherapy_general` where it competes with alliance and crisis content. Keeping MI as a modality that is *always* included in the working set (`CBT ∪ MI`, `IPT ∪ MI`, ...) is cheaper and more precise than either alternative.

**Concrete rule:** MI is a modality that never gets filtered out. It is unioned into every working set regardless of `domain`. `motivational_ambivalence` then *boosts* MI content that is already loaded, rather than triggering a cold fetch — which is also the lower-latency design.

### 8.2 Is `session_phase` only PE/CPT? Is it a preload to session N?

**It's a preload, and it is not PE/CPT-only — but it is only *useful* where protocols are sequenced.**

Two distinct questions:

1. **Which modalities are phase-sensitive?** Strongly: PE, CPT, ERP, DBT (skills sequence), UP. Weakly: CBT, BA, MBCT. Barely: MI, Schema. So it isn't PE/CPT-only, but the value is concentrated in manualized, session-numbered protocols.
2. **Preload or event filter?** **Preload.** If the session carries "session N of protocol," `session_phase` is known before the session starts and belongs on the session clock as a pre-filter — never a live query.

**The critical exception, already handled well:** `crisis` is in the enum as phase-agnostic. When an event fires, the phase filter must be **relaxed, not applied** — crisis content must surface regardless of the session's nominal phase. This is the right design; make sure the searcher implements phase as a *soft* filter that events can override, not a hard pre-filter. A hard filter here would suppress crisis content during a late-treatment session, which is exactly backwards.

**Practical note:** if session N isn't reliably available in session context, `session_phase` degrades to dead weight (everything defaults to `any`). Confirm data availability before investing in ingestion accuracy for this field (§9, Q7).

### 8.3 How should ingestion/retrieval know `directionality` and `applies_when` are PAIRED?

The pairing cannot be expressed in draft-07 as a co-requirement in the way you want, but it can be *enforced* at three layers. Use all three — schema alone is insufficient.

**Layer 1 — Schema-level conditional.** Draft-07 supports `if/then`, so encode the rule that a non-neutral directionality requires a scope:

```jsonc
"if": {
  "properties": { "directionality": { "enum": ["contraindicated", "cautionary"] } },
  "required": ["directionality"]
},
"then": {
  "properties": { "applies_when": { "minItems": 1 } }
}
```

This makes *"contraindicated for nothing"* structurally invalid — the error state §3.3 flagged.

**Layer 2 — Ingestion prompt + post-validation.** Present the two fields to the ingestion LLM as **one question, not two**: *"Does this passage say to do something, avoid something, or proceed with caution — and under exactly what conditions?"* Asking separately invites the model to fill one and default the other. Then validate every `applies_when` value against the closed vocabulary from §7.2 and reject out-of-vocab.

**Layer 3 — Retrieval contract.** The searcher treats them as one predicate. Never filter on `directionality` alone:

```
retrieve WHERE (applies_when ∩ fired_events_and_states ≠ ∅ OR applies_when = [])
rank    boost WHERE directionality = "contraindicated"
```

**Interaction with the other three vocabularies** — the answer to *"how should these interact with `session_event_tags`, `clinical_presentation`, `state_vocab`?"*:

`applies_when` draws from all three, and each element type is matched against a different part of session context:

| `applies_when` value type | Matched against | Clock |
|---|---|---|
| `session_event_tags` value (e.g. `disclosure_SI`) | Detector output this turn | Event |
| `clinical_presentation` value (e.g. `SUD`) | Working diagnosis, known at start | Session |
| `state_vocab` value (e.g. `intoxication`) | Session state flags | Either — set at start *or* updated mid-session |

A chunk with `applies_when: ["trauma", "acute_suicidality"]` is active when the patient's presentation includes trauma **and/or** acute SI is flagged. **Decide and document whether multiple values are OR or AND** — this is genuinely ambiguous in the current description and changes retrieval behavior materially. Recommend **OR** (broader net, consistent with the §2.4 safety-recall principle), with AND expressible later via a nested form if clinicians need it.

### 8.4 Can an ingestion LLM reliably handle `missingness`?

**Not reliably, no.** Absence-inference is qualitatively harder than extraction: the model must reason over what a source *should* have reported and didn't, which invites confabulation and is nearly impossible to validate at scale. Expect low precision and inconsistent recall.

More decisive for your architecture: **`missingness` has no clear RTA consumer.** It was designed for evidence-appraisal workflows (surfacing sample gaps alongside RCT findings) — that use case left with `evidence_base` and `study_type`. Surfacing *"this source doesn't report fidelity monitoring"* mid-crisis is noise.

**Recommendation: drop `missingness` from `rta_v1.json`.** If representation gaps matter later, revisit as a document-level field with human annotation, not chunk-level LLM inference.

### 8.5 Should prompting/routing be generated from the schema JSON?

**Yes — generate the ingestion prompt's enum lists from the schema; keep the reasoning guidance hand-written.**

The failure mode you're guarding against is real: hand-maintained prompts drift from the schema, then ingestion emits values the retriever can't filter on. Generating the *value lists* mechanically eliminates that class of drift, and is cheap (a build step that reads the JSON and emits the enum blocks).

But do **not** auto-generate the whole prompt. Enum lists are mechanical; disambiguation guidance is not — *"when is a rupture also a crisis"* is clinical judgment that has to be written by a human and refined against QA failures. **Split the prompt into a generated section (vocabularies, from schema) and a maintained section (definitions, edge cases, few-shot examples).** Implementation in `summary.md` §3.

This also directly addresses your changelog note that *"in each description, likely need something to clarify any ambiguous cases in automated ingestion."* The right home for that clarification is the maintained prompt section, **not** the schema descriptions — descriptions should stay short and definitional, since they're also read by humans and by the DataStore registration.

---

## 9. Directed questions for clinicians (revised)

Revision 1's questions were broad and architectural. These are narrower, answerable, and each maps to a specific schema decision now pending. Ordered by how much the answer changes the build.

### Q1 — Modality co-retrieval matrix *(blocks Alt A; still the highest-impact question)*

> For each pair of modalities, is retrieving content from B during a session running A: **(a)** appropriate, **(b)** acceptable but lower priority, or **(c)** an error we should prevent?

Ask them to complete the actual matrix, not describe it in prose. Specific probes worth forcing:
- DBT distress-tolerance skills during a CBT-depression session — appropriate or error?
- ACT defusion during CPT?
- Any BA content during any CBT session — is BA effectively a CBT subset?
- MI — confirm it should always be available (assumed in §8.1).

**Determines:** hard filter vs. soft boost vs. hybrid (Alt A). Cannot be deferred; it's the top-level retrieval architecture.

### Q2 — The `applies_when` state vocabulary *(blocks §7.2 — highest-severity gap)*

> What are the patient states that should **change what the system recommends**, independent of diagnosis and independent of what just happened in session?

Seed list to react to: `acute_suicidality`, `intoxication`, `insufficient_stabilization`, `active_dissociation`, `acute_psychosis`, `medical_instability`, `cognitive_impairment`, `active_self_harm`.

Follow-ups:
- Which are set at session start vs. detected mid-session? (Determines clock.)
- **Is `intoxication` a state, an event, or both?** (§1.4 open item.)
- For each state, which modalities/techniques become contraindicated?

**Determines:** the closed vocabulary that makes contraindication retrieval work at all. **This is the single most blocking clinical input.**

### Q3 — Dissociation without a dissociative-disorders corpus

> `dissociation` was kept as a detectable event, but `dissociative_disorders` was removed as a presentation. When dissociation occurs mid-session, what should the system surface — and from which body of content?

**Determines:** whether `dissociation` stays in the event enum. If there's no corpus to route to, a detectable-but-unserviceable event is worse than no tag: it fires, retrieves nothing useful, and costs latency. Either restore a minimal grounding-content path or drop the tag.

### Q4 — Severity gradation *(Alt C, reopened)*

> Removing `decompensation` resolved a tagging ambiguity but left `crisis_escalation` as the only acute tag, with no severity gradation. Does the system need to distinguish *"patient is escalating"* from *"patient is in acute crisis"* — and would the recommended response actually differ?

**Determines:** whether to add `severity` as a second axis (Alt C). If responses don't differ, the flat enum is correct and Alt C closes permanently.

### Q5 — Risk monitoring: preload or background pass? *(§3.0)*

> For a patient with chronic SI in treatment for grief, should SI-monitoring content be loaded at session start, or retrieved only when something triggers it?

Follow-up: is `risk_dimension_tags` a property of the *patient* (from the treatment plan) or of the *session*?

**Determines:** whether `risk_dimension_tags` drives a preload (recommended) or a recurring background query, and whether the third clock in §3.0 collapses into the session clock.

### Q6 — Source precedence *(§7.4)*

> When a treatment manual and a textbook give conflicting guidance, which wins? Does a newer textbook ever outrank an older manual?

**Determines:** `doc_type` precedence ordering and whether `year_published` is a tiebreaker or an independent factor.

### Q7 — Session-context data availability *(gates §8.2)*

> At session start, what does the system reliably know: working diagnosis, modality, session number in protocol, active risk flags, current state flags?

**Determines:** whether `session_phase`, `patient_population`, and `risk_dimension_tags` can function as session-clock pre-filters at all. **Ask this early** — if session number isn't available, `session_phase` ingestion accuracy is wasted effort.

### Q8 — Actionability format *(Alt D / `chunk_kind`)*

> When an event fires mid-session, what should appear first: a one-line decision rule, a verbatim phrase to say, or a short rationale?

**Determines:** whether `chunk_kind` is worth adding (§1.2) and how the analysis LLM ranks and formats output. Cheap question, disproportionate effect on perceived quality.

### Q9 — Contraindication scope breadth *(§2.4)*

> If a contraindication is documented for PE, should it also surface during CPT (both trauma-processing)? Prefer over-surfacing cautions or keeping them precise?

**Determines:** broad-net tagging rule for contraindications, and the searcher's floor on `directionality: contraindicated`.

### Q10 — Preload budget *(Alt E)*

> What must be in front of the system every single session, before anything happens?

**Determines:** the mandatory-always set and the latency budget split between session start and event time.
