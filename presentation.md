# Why Metadata Is the Product: Discovery Engine + Automated Ingestion

*A walkthrough of why correct metadata tagging is load-bearing for this RAG guidance system,
and what happens to clinical guidance when a chunk is tagged wrong.*

Companion to `discovery_engine_comparison.md` (how indexing is registered and how the
front-end queries it) and `DISCREPANCIES.md`.

---

## 1. The thesis

> Discovery Engine does not retrieve documents. It retrieves **metadata matches**.
> The PDF text is only the payload. The **tags** decide whether a passage is eligible to
> ground an answer.

For a psychotherapy guidance system with a real-time (RTA) mode, that makes the metadata layer
the safety boundary. A perfectly extracted, perfectly chunked passage with the **wrong tags**
is worse than a missing one: it will be retrieved for the wrong session, in the wrong modality,
at the wrong moment — silently, with no error.

---

## 2. How tags actually get applied — the automated ingestion path

Tagging is not manual. It is produced per chunk by an automated pipeline
(`scripts/batch_ingest.py` → `CorpusScanner.scan()`):

```
corpus/ PDF ─► extractor ─► chunker ─► metadata_gen ─► uploader (GCS) ─► indexer (Vertex AI Search)
                                          │
                                          ▼
                              Gemini, once per chunk, tags against
                              config/metadata_schema.json (37 fields)
                              → validated/coerced by SchemaVocabulary
                              → ChunkMetadata
```

- **`metadata_gen.py` calls Gemini once per chunk** and coerces the result against the schema
  (`config/schema_loader.py::SchemaVocabulary`): enum validity, single→list array
  normalization, integer parsing, defaults, and dropping keys not in the schema.
- **Structural fields are never trusted from the model.** `doc_id`, `page_start`, `page_end`,
  and `chunk_index` are **always overridden from the `Chunk`** object. Those are safe.
- **Everything semantic is model-inferred:** `domain`, `therapeutic_modality`,
  `clinical_presentation`, `session_event_tags`, `risk_dimension_tags`, `corpus_scope`,
  `target_audience`, `doc_type`, … — the exact fields the searcher pre-filters on.
- **On any Gemini failure, `_fallback_extraction()` runs** so ingestion never hard-fails —
  which means a failed chunk still gets indexed, just with minimal/empty tags.

**Takeaway:** the tags that decide retrieval are produced by an LLM at ingestion time. Their
correctness is a pipeline property, not a given.

---

## 3. Discovery Engine only sees what was registered *and* tagged

Two independent conditions must both hold for a passage to be retrievable-with-scope:

1. **The field must be registered `indexable`** in the schema (the `json_schema` annotation fix
   — `discovery_engine_comparison.md` §2b). If not, the filter clause matches nothing for
   everyone. *(This was the array-field bug; now fixed.)*
2. **The chunk must carry the correct value** for that field. If the tag is wrong, the filter
   admits/excludes the wrong chunk — for that chunk only.

Condition 1 is a one-time provisioning correctness issue. Condition 2 is a **per-chunk**
correctness issue that repeats 10,000× across a corpus. This document is about condition 2.

---

## 4. The load-bearing tags (what "correct" has to mean)

These are the fields the RTA/ASA searcher pre-filters on. Getting them right *is* the product:

| Field | Level | Role in retrieval |
|---|---|---|
| `domain` | document | Selects the **persona** in `PromptBuilder` (voice + scope of the answer) |
| `therapeutic_modality` | chunk | Modality scope, e.g. `ANY("CBT")` — keeps guidance in the clinician's trained modality |
| `clinical_presentation` | chunk | Presentation scope, e.g. `ANY("depression")` |
| `session_event_tags` | chunk | Event routing, e.g. `ANY("rupture_repair")` from the monitor |
| `risk_dimension_tags` | chunk | Safety routing, e.g. `ANY("suicide_ideation_chronic")` |
| `corpus_scope` | document | **Hard RTA pre-filter**: `asa_only` must never enter in-session answers |
| `target_audience` | document | **Hard exclusion**: `patient` excluded from all paths except `homework_resource` |
| `doc_type` | document | Coarse source-type filtering / weighting |
| `missingness` | document | Surfaced (retrievable) so the answer can name representation gaps; not filtered |

---

## 5. What happens when a chunk is tagged **incorrectly**

Every failure below is **silent** — no exception, no log, no user-visible error. The chunk is
happily indexed; it just answers to the wrong queries. Grouped by failure shape:

### 5a. Wrong value → retrieved for the wrong context

| Mis-tag | Consequence |
|---|---|
| Psychodynamic technique tagged `therapeutic_modality: ["CBT"]` | Surfaced during a CBT session → clinician receives **out-of-competence** guidance presented as in-scope |
| `clinical_presentation: ["depression"]` on an OCD passage | OCD content grounds a depression-scoped answer → clinically inappropriate recommendation |
| `session_event_tags` mislabels a rupture as `alliance_building` | During an actual rupture, repair guidance is **not** retrieved; the monitor event routes to the wrong material |
| `corpus_scope` set to `rta_and_asa` on after-session-only material | Reflective/retrospective content is injected into **real-time** guidance — wrong depth/latency mid-session |
| `target_audience` set to `therapist` on a patient handout | Patient-facing language surfaces as clinician guidance (or leaks the other way) |
| `domain` wrong (e.g. `interpersonal` instead of `cognitive_behavioral`) | `PromptBuilder` selects the **wrong persona** → tone and scope mismatch even if passages are fine |

### 5b. Missing / defaulted value → silently drops out of filters

Because ingestion never hard-fails and the schema supplies defaults, a chunk Gemini couldn't
tag doesn't error — it gets **sentinel defaults** that quietly remove it from scoped retrieval:

| Situation | Result |
|---|---|
| Gemini omits `therapeutic_modality` → coerced to `[]` | Chunk is **invisible** to every modality-scoped RTA query, forever (until re-ingest) |
| Unknown `domain` → coerced to `other` | Never matches a specific-domain persona; routes to the generic fallback |
| Unknown `doc_type` → coerced to `""` | `""` is not a valid enum member → `doc_type`-filtered queries skip it |
| `_fallback_extraction()` fires (Gemini down) | Chunk indexed with near-empty semantic tags → present in the store, absent from every scoped result set |

### 5c. Wrong safety tag → the dangerous case

| Mis-tag | Consequence |
|---|---|
| `risk_dimension_tags` omitted on a suicide-risk passage | During a `crisis_escalation` event, the safety-critical guidance is **not** retrieved |
| `target_audience: patient` mistakenly on crisis-protocol content | Excluded from RTA entirely (patient exclusion) → the clinician gets nothing when it matters most |

**The pattern:** incorrect metadata does not degrade gracefully. It produces confidently wrong
or conspicuously absent guidance, and it does so without any signal that anything went wrong.

---

## 6. Why the blast radius is large: single-batch ingestion + immutable schema

- Ingestion is a **single batch event**: schema registered once, one `ImportDocuments`, no
  per-document upsert.
- Fixing a mis-tag is not a patch — the schema/DataStore is effectively immutable, so
  correcting tags means `purge_datastore.py --confirm` → clear GCS/DataStore → **full
  re-ingestion** of the entire corpus with corrected JSON tags.
- So a systematic tagging error (e.g. a prompt regression in `metadata_gen.py`) is **baked into
  the corpus** until someone notices the retrieval is wrong and pays for a full rebuild.

This is exactly why the up-front controls matter: schema-driven coercion, a strict enum
vocabulary in the extraction prompt, and validation before import.

---

## 7. What already protects us (and the residual gap)

**Protections in place:**

- Structural fields (`doc_id`, page numbers, `chunk_index`) are **overridden from the chunk**,
  never trusted from Gemini — so document identity and citation pages can't be mis-tagged.
- `SchemaVocabulary.coerce()` enforces the enum vocabulary, normalizes arrays, and drops
  unknown keys, so out-of-vocabulary hallucinations can't reach the DataStore as new fields.
- The extraction prompt emits the schema's enum legend and the RTA/ASA guidance
  (`domain`-vs-`modality`, missingness inference, patient-facing exclusion) to steer Gemini.
- Field indexing is now registered correctly (arrays included), so a *correct* tag is actually
  usable as a filter (`discovery_engine_comparison.md` §2b).

**Residual gap:** none of the above verifies that a *valid* tag is the *right* tag. Coercion
guarantees `therapeutic_modality: ["DBT"]` is a legal value; it cannot tell that the passage was
actually about CBT. That judgment is Gemini's, per chunk, and is the system's principal
correctness risk. Candidate mitigations: spot-audit sampling of tags per document, confidence
thresholds that route low-confidence chunks to review, and validation that document-level fields
(`domain`, `corpus_scope`, `target_audience`) are consistent across a document's chunks.

---

## 8. Takeaways

1. **Retrieval correctness == metadata correctness.** Discovery Engine filters on tags; the text
   is just what gets returned.
2. **Two conditions, both required:** the field must be registered `indexable` (provisioning),
   and the chunk must carry the right value (ingestion). We fixed the first; the second is
   ongoing.
3. **Incorrect tags fail silently** and, in a clinical RTA setting, unsafely — wrong-modality,
   wrong-presentation, wrong-moment, or missing safety guidance, with no error surfaced.
4. **Single-batch + immutable schema** means mistakes are expensive to undo — correctness has to
   be earned at ingestion, not patched later.
