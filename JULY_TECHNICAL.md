# JULY_TECHNICAL — Architectural Safety Audit: RAG Guidance Pipeline (RTA/ASA)

**Scope:** Five core failure modes at the RAG↔Gemini boundary for a CBT/DBT/IPT clinician
assistant on Vertex AI Search (Discovery Engine `v1` GA) + Gemini (`google-generativeai`).
**Verified against this repo:** `retrieval/searcher.py`, `rta_prompt/rta/searcher.py`,
`rta_prompt/asa/searcher.py`, `generation/{prompt_builder,response_gen}.py`,
`config/metadata_schema.json`, `config/schema_loader.py`, `scripts/setup_vertex_search.py`,
`ingestion/{uploader,metadata_gen}.py`.
**Client surface facts:** field indexing is registered via `json_schema` keyword annotations
(`retrievable`/`indexable`/`searchable`) — `Schema.field_configs` is `OUTPUT_ONLY` on v1/v1beta/v1alpha
(`discovery_engine_comparison.md`). All AIP-160 array filters (`field: ANY(...)`) depend on
`indexable` being set on the array `items` leaf.

**Threat-model framing note.** The prompt attributes these failures to Gemini's "sparse MoE /
helpfulness" internals. The defenses below do **not** depend on any specific claim about internal
routing. The two behaviors we actually engineer against are empirically documented and model-agnostic:
(a) **positional under-weighting in long contexts** ("lost in the middle," Liu et al. 2023), and
(b) **alignment-induced helpfulness/sycophancy bias** — an RLHF-tuned model prefers producing a
fluent, complete-sounding answer over declaring insufficiency. Treat every mitigation as a
**deterministic control outside the model** (server-side pre-filter, structured-output contract,
circuit breaker), never as a request the model is trusted to honor.

---

## Cross-cutting root cause (applies to all five)

Two soft instructions carry almost the entire current safety burden, and both are model-obeyed prose,
not enforced controls:

- `config/prompt_config.yaml` → `"Base your response SOLELY on the passages below."`
- `config/prompt_config.yaml` → `"If a retrieved passage contains a clinical caution ... state it explicitly."`

A helpfulness-biased model can rationalize around both. Every section converts one of these prose hopes
into a **programmatic invariant**: a server-side filter, a ranking guarantee, a JSON schema field the
model is forced to populate, or a pre-generation short-circuit.

---

# V1 — Fragmentation & the "Snippet Cutoff" Trap

### 1. Deep mechanics

Each chunk is imported as an **independent DataStore document** keyed `"{doc_id}_{chunk_index:05d}"`
(`models.Chunk`, `ingestion/uploader.py::_serialize_chunk`). Two structural facts make fragmentation acute:

- **Chunk text lives only in `content` (base64), not in `structData`.** `_serialize_chunk` writes
  `structData = metadata.model_dump()` and the passage text into `content.rawBytes`. On search,
  Discovery Engine returns **derived** snippets/extractive segments from `content` — truncated windows,
  not the full chunk. `retrieval/searcher.py::_parse_result` is documented to read
  `derived_struct_data`/`struct_data`, so unless configured otherwise the generator sees a **cut-off
  fragment**.
- **Chronological/prerequisite dependencies cross chunk boundaries.** A contraindication ("screen for
  dissociation before imaginal exposure") is often in chunk *i*; the procedure is in chunk *i+1*.
  Semantic retrieval matches the *procedure* chunk on the therapist's query and never pulls the sibling
  that carries the precondition.

The model then receives one truncated, procedure-only passage, is told to answer *solely* from it, and —
biased toward a complete, actionable reply — emits confident steps with the prerequisite silently absent.

### 2. Behavioral-health rationale

**PE / trauma_focused, RTA, sub-second.** Therapist query mid-session retrieves the "how to run imaginal
exposure" chunk. In the corpus schema this technique carries `training_level_required="specialist_trained"`
and a sibling chunk holds `clinical_caution=["contraindicated without prior dissociation screening"]`
plus `session_event_tags` for `avoidance_safety_behavior`. The caution chunk is not retrieved; the snippet
is truncated to the procedure. Output: *"Begin imaginal exposure, 45–60 min, no distraction."* Delivered to
a patient with unassessed dissociation → **dissociative flooding / re-traumatization** — textbook iatrogenesis.

### 3. SDK code-level remedial action

**(a) Stop depending on snippets — return full segments + neighbors.** In
`retrieval/searcher.py::search`, attach a `ContentSearchSpec` that disables snippet truncation and widens
the extractive window:

```python
from google.cloud import discoveryengine_v1 as de

content_spec = de.SearchRequest.ContentSearchSpec(
    snippet_spec=de.SearchRequest.ContentSearchSpec.SnippetSpec(return_snippet=False),
    extractive_content_spec=de.SearchRequest.ContentSearchSpec.ExtractiveContentSpec(
        max_extractive_segment_count=1,   # the whole matched chunk as one segment
        num_previous_segments=2,          # pull adjacent context, not a cutoff
        num_next_segments=2,
        return_extractive_segment_score=True,
    ),
)
```

**(b) Make the full chunk text a first-class retrievable field.** Add `chunk_text` to
`config/metadata_schema.json` (string leaf → auto-annotated `retrievable`+`searchable` by
`_annotate_schema_for_indexing`) and populate it in `ingestion/uploader.py::_serialize_chunk`:

```python
struct_data = chunk.metadata.model_dump()
struct_data["chunk_text"] = chunk.text          # full passage, not a derived snippet
return {"id": chunk.chunk_id, "structData": struct_data,
        "content": {"mimeType": "text/plain", "rawBytes": raw_bytes}}
```

`_parse_result` then reads `struct_data["chunk_text"]` — the passage is reconstructed verbatim, never truncated.

**(c) Deterministic neighbor fetch (IDs are computable — no extra search).** Chunk IDs are
`{doc_id}_{chunk_index:05d}`, so neighbors are addressable directly via `DocumentServiceClient.get_document`:

```python
def fetch_neighbors(doc_id: str, i: int, radius: int = 1) -> list[str]:
    branch = f"{datastore_name}/branches/default_branch/documents"
    ids = [f"{doc_id}_{j:05d}" for j in range(max(0, i - radius), i + radius + 1)]
    return [doc_client.get_document(name=f"{branch}/{cid}").struct_data for cid in ids]
```

**(d) Ingestion-side "caution atomicity" — the real fix.** Two rules in `ingestion/`:
1. **Never split a technique from its stated contraindication** — extend `ContextAwareChunker` so a
   `clinical_caution`/`contraindicated` sentence stays in the same chunk as the technique it modifies
   (wire the already-declared-but-unused `front_matter_indicators`/section logic here).
2. **Propagate document-level cautions to every chunk.** In `ingestion/metadata_gen.py`, after per-chunk
   extraction, union any document-scope `clinical_caution` / `practice_recommendation_level="contraindicated"`
   into **all** chunks of that `doc_id`. A contraindication that exists anywhere in the source can then
   never be orphaned by the chunk window.

---

# V2 — Logical Flattening & Dilution ("Lost in the Middle")

### 1. Deep mechanics

`top_k` defaults to 8 (`retrieval/searcher.py::_DEFAULT_TOP_K`). `PromptBuilder._format_retrieved_chunks`
lays passages out as a flat numbered list `[1]…[8]`. When passage *A* = a general "recommended" statement
and passage *B* = a strict exception, two effects compound:

- **Positional attenuation.** Passages in the middle of the list receive less effective attention; if the
  exception lands at `[4]`/`[5]` it is under-weighted relative to `[1]` and `[8]`.
- **Helpfulness averaging.** The model prefers a single smooth recommendation, so it blends a
  "strongly_recommended" statement and a "contraindicated" statement into a hedged hybrid instead of
  preserving the hard boundary. The schema explicitly warns this is unsafe:
  `practice_recommendation_level` note — *"Polarity values (use_with_caution, contraindicated) must be
  surfaced prominently ... not suppress[ed]."*

### 2. Behavioral-health rationale

**DBT, mid-session dissociation.** Retrieval returns:
`[2]` distress-tolerance skills are recommended for high arousal (`practice_recommendation_level="recommended"`);
`[5]` do **not** run skills-coaching/problem-solving during active dissociation — validate and orient first
(`practice_recommendation_level="contraindicated"`, `session_event_tags=["somatic_activation"]`). Flattened
output: *"Coach TIPP while validating."* Skills coaching during dissociation **escalates** dysregulation —
the exact boundary the exception encodes is dissolved.

### 3. SDK code-level remedial action

**(a) Rank polarity to the top — deterministic, not semantic.** Add a `BoostSpec` so caution/contraindication
chunks are never buried mid-list:

```python
boost_spec = de.SearchRequest.BoostSpec(condition_boost_specs=[
    de.SearchRequest.BoostSpec.ConditionBoostSpec(
        condition='practice_recommendation_level: ANY("contraindicated", "use_with_caution")',
        boost=0.5),                                   # boost ∈ [-1, 1]; positive → surfaced
])
```

**(b) Position exceptions in the high-attention slots.** In
`generation/prompt_builder.py::_format_retrieved_chunks`, sort so contraindication/caution passages occupy
the **first and last** positions (never the middle), and label polarity inline:

```python
def _order_for_attention(results):
    def polarity(r):
        m = r.metadata
        return bool(m and (m.clinical_caution or
                    m.practice_recommendation_level in {"contraindicated", "use_with_caution"}))
    cautions  = [r for r in results if polarity(r)]
    neutral   = [r for r in results if not polarity(r)]
    half = (len(cautions) + 1) // 2
    return cautions[:half] + neutral + cautions[half:]   # edges = high attention
```

**(c) Force reconciliation via structured output — the model must enumerate, not average.** Constrain
generation with a `response_schema` that has a mandatory `boundary_conflicts` array (see §Reference). The
model cannot emit a smooth hybrid without first listing the conflicting polarities it detected.

**(d) Determinism.** Set generation `temperature=0.0` for RTA (currently `response_gen.py` defaults to 0.2).
For a zero-tolerance surface, drop the sampling variance.

---

# V3 — Cognitive Pollution Across Distinct Frameworks

### 1. Deep mechanics

Ambiguous queries have CBT, DBT, and IPT chunks as embedding neighbors. If the searcher issues an
**unfiltered** query — or query expansion silently broadens it — the result set spans modalities and the
model, being integrative-by-default, synthesizes a compromise that violates every framework's internal logic.
`caveats.md §6.2` is explicit: **persona framing alone does not fix this** ("Expert persona framing does not
change the model's knowledge boundary"). The only hard wall is the **server-side `therapeutic_modality`
pre-filter**, which only functions because array `items` are registered `indexable`
(`scripts/setup_vertex_search.py::_annotate_schema_for_indexing`).

### 2. Behavioral-health rationale

**Acute DBT validation phase.** Query "patient is spiraling about a breakup" pulls a CBT
cognitive-restructuring chunk (`therapeutic_modality=["CBT"]`, technique "challenge the automatic thought")
and an IPT role-transition chunk. Compromise output: *"Validate the emotion, then challenge the distortion
that they'll be alone forever, and inventory their support network."* Injecting **change-oriented cognitive
restructuring into an acceptance-phase DBT moment is invalidating**, predictably triggers
`rupture_confrontation`, and breaks the dialectical frame.

### 3. SDK code-level remedial action

**(a) Hard modality pre-filter (correctness constraint, not ranking).** This is exactly what
`rta_prompt/rta/searcher.py::_build_static_filter` must compile once per session and AND into every query:

```
therapeutic_modality: ANY("DBT")
    AND corpus_scope != "asa_only"
    AND target_audience != "patient"
```

`ANY(...)` is repeated-field membership; it matches nothing unless the field is `indexable` (the array-leaf
annotation is what makes framework isolation possible at all).

**(b) Disable query expansion so retrieval cannot drift off-modality.**

```python
query_expansion_spec=de.SearchRequest.QueryExpansionSpec(
    condition=de.SearchRequest.QueryExpansionSpec.Condition.DISABLED),
spell_correction_spec=de.SearchRequest.SpellCorrectionSpec(
    mode=de.SearchRequest.SpellCorrectionSpec.Mode.SUGGESTION_ONLY),
```

**(c) Post-retrieval modality-purity guard (circuit breaker).** Even with the filter, assert the invariant
before generation; a mixed set means a mis-tagged chunk slipped through — drop off-modality or abstain:

```python
allowed = set(patient_context.therapeutic_modality)
def modality_pure(results):
    return all(set(r.metadata.therapeutic_modality) & allowed for r in results if r.metadata)
```

**(d) Bind persona to the *same* axis.** `PromptBuilder._select_persona(domain)` selects the single-modality
persona (`dialectical_behavior` → DBT supervisor whose text already says *"you do not provide guidance on
modalities outside…"*). The filter is the wall; the persona is defense-in-depth, never the primary control.

---

# V4 — "Helpfulness" Bias vs. Data-Gap Blindness

### 1. Deep mechanics

The most dangerous mode. Clinician enters rich patient variables; retrieved chunks **do not contain the
specific answer**. An RLHF-aligned model treats "produce a helpful, complete answer" as the objective and
back-fills a plausible path from pretraining priors rather than halting. The current guard —
`prompt_config.yaml` "Base your response SOLELY on the passages" and "write *Evidence unclear from retrieved
sources*" — is prose the model can override under helpfulness pressure. Worse, the **failure path is
fail-open**: `metadata_gen.py::_fallback_extraction` returns a chunk with permissive defaults
(`corpus_scope="rta_and_asa"`, `target_audience="therapist"`, empty `clinical_caution`), so a *bad extraction*
produces a caution-free chunk that is eligible for real-time guidance.

### 2. Behavioral-health rationale

**CPT + comorbid psychosis (trauma_focused).** Corpus holds standard CPT only; nothing on
psychosis-comorbid PTSD. Instead of abstaining, the model fabricates a "modified CPT trauma-narrative
sequence for psychosis" — **no evidence base, real decompensation risk**. Or: asked to interpret a score, it
invents a **PHQ-9 severity cutoff** absent from the retrieved `outcome_measure_tags` chunk. Confident,
fluent, unsupported — precisely the pattern a helpfulness-biased model produces on a data gap.

### 3. SDK code-level remedial action

**(a) Pre-generation retrieval circuit breaker.** Abstain *before* Gemini is ever called when evidence is
thin. `CorpusSearcher.search` already exposes `min_relevance_score`:

```python
results = searcher.search(query, top_k=8, filters=f, min_relevance_score=0.55)
if not results or max(r.score for r in results) < GEN_THRESHOLD:
    return INSUFFICIENT_EVIDENCE_TEMPLATE   # never generate on a gap
```

**(b) Make abstention a structural output, not a behavior.** Force controlled generation whose schema has a
first-class insufficiency path; the pipeline keys off `answerable`, not off prose:

```python
response_schema = {
  "type": "object",
  "properties": {
    "evidence_sufficiency": {"type": "string", "enum": ["sufficient", "partial", "insufficient"]},
    "answerable": {"type": "boolean"},
    "guidance": {"type": "string"},                       # "" when answerable == false
    "unmet_data_requirements": {"type": "array", "items": {"type": "string"}},
    "citations": {"type": "array", "items": {"type": "integer"}}
  },
  "required": ["evidence_sufficiency", "answerable", "guidance", "citations"]
}
# in ResponseGenerator._call_gemini:
generation_config = genai.types.GenerationConfig(
    temperature=0.0, response_mime_type="application/json", response_schema=response_schema)
```

Pipeline rule: `if not payload["answerable"] or payload["evidence_sufficiency"] == "insufficient": surface
the abstention template + payload["unmet_data_requirements"]`. There is no code path that renders a
fabricated answer.

**(c) Citation-coverage enforcement (drop uncited claims).** Post-generation, verify every sentence carries a
`[n]` that resolves to a retrieved passage; strip or flag any uncited claim. This makes
`response_gen.py::_extract_grounding_attributions` an **audit gate**, not a display convenience.

**(d) If using the built-in summarizer**, harden it against the same bias:

```python
summary_spec=de.SearchRequest.ContentSearchSpec.SummarySpec(
    ignore_adversarial_query=True,
    ignore_non_summary_seeking_query=True,
    include_citations=True,
    model_spec=de.SearchRequest.ContentSearchSpec.SummarySpec.ModelSpec(version="stable"),
)
```

The self-controlled abstention schema in (b) is preferred over the built-in summarizer for a clinical surface.

---

# V5 — Data Layering & Expert-Annotation Strategy (the enabling substrate)

### 1. Deep mechanics

Deterministic routing is only possible if the metadata it filters on is trustworthy. Unoptimized text filters
fail because (i) chunk boundaries split clinical units, and (ii) safety-critical tags are Gemini-*suggested*,
which `caveats.md §2` flags as non-authoritative. This repo already has the correct backbone —
`metadata_schema.json` as single source of truth, `SchemaVocabulary.coerce` dropping out-of-vocab tokens,
`_annotate_schema_for_indexing` making fields `indexable`. The gap is the **human-layering protocol** and two
**fail-open defaults** that must flip to fail-safe.

### 2. Behavioral-health rationale

**Fail-open default (concrete, in this schema).** `corpus_scope` defaults to `"rta_and_asa"` and
`target_audience` to `"therapist"`. A chunk that a human never reviewed — or that came out of
`_fallback_extraction` — is therefore **admitted to the real-time in-session path by default**. For a
zero-tolerance surface the safe default is the opposite: unreviewed/failed chunks should be **quarantined to
`asa_only`** (or excluded from the index) until an expert approves them. A patient-facing psychoeducation
handout mis-tagged `therapist` could otherwise surface as in-session clinician guidance.

### 3. SDK code-level remedial action — the annotation contract

**(a) Two-tier tagging (already the schema's design — enforce it in review).**
- **Document-level, set once:** `domain`, `doc_type`, `study_type`, `population_focus`, `source_language`,
  `setting`, `adaptation_status`, `sample_size`, `intended_use_context`.
- **Chunk-level, per passage:** `therapeutic_modality`, `session_event_tags`, `clinical_presentation`,
  `evidence_base`, `patient_population`, `clinical_caution`, `practice_recommendation_level`,
  `training_level_required`, `risk_dimension_tags`.
  (This is exactly the schema's `domain_vs_modality` / `representation_and_implementation_fields` split.)

**(b) Split rules for the human/AI chunker.**
1. Split on **protocol/session units** — treatment manuals navigate by session number (schema `chapter` note).
2. **Caution atomicity** (see V1-d): a technique and its stated contraindication are one chunk.
3. Front-matter (`doc_type="front_matter"`) is excluded from search — wire the declared-but-unused
   `skip_doc_types`/`front_matter_indicators`.

**(c) Human review queue gating the six safety-critical fields.** Route Gemini output through expert sign-off
before a chunk becomes RTA-eligible: `corpus_scope`, `target_audience`, `clinical_caution`,
`practice_recommendation_level` (polarity), `training_level_required`, `risk_dimension_tags`. Add a
`review_status` field (`unreviewed | approved`) and make **`indexable`**; RTA searcher ANDs
`review_status = "approved"`.

**(d) Flip the fail-open defaults to fail-safe.**

```python
# ingestion/metadata_gen.py::_fallback_extraction — quarantine on extraction failure
return ChunkMetadata(
    doc_id=chunk.doc_id, page_start=chunk.page_start, page_end=chunk.page_end,
    chunk_index=chunk.chunk_index, title=title, keywords=keywords,
    corpus_scope="asa_only",       # <-- do NOT admit un-analyzed text to the real-time path
    # target_audience left "therapist" is fine; corpus_scope quarantine is the guard
)
```

**(e) Controlled vocabulary is the routing guarantee.** `SchemaVocabulary.coerce` already drops any tag not
in the enum, so an annotation error cannot inject an unroutable value. Keep every routing field enum-closed
(free-text `subdomain`/`keywords`/`technique_tags` must **never** be a routing axis).

---

# Reference: Code & Prompt Specifications

## R1 — Hardened `SearchRequest` (RTA path)

Assemble in `retrieval/searcher.py::search`; the filter string comes from
`rta_prompt/rta/searcher.py::_build_static_filter` + `_build_event_filter`.

```python
request = de.SearchRequest(
    serving_config=self._serving_config,
    query=window_text,
    page_size=min(top_k, 100),                       # caveats.md §1: hard cap 100
    filter=static_filter + " AND " + event_filter,   # AIP-160, indexable fields only
    content_search_spec=content_spec,                # R-V1: full segments, snippet off
    boost_spec=boost_spec,                           # R-V2: polarity to the top
    query_expansion_spec=de.SearchRequest.QueryExpansionSpec(
        condition=de.SearchRequest.QueryExpansionSpec.Condition.DISABLED),  # R-V3
)
```

## R2 — AIP-160 filter contract (non-negotiable clauses)

```jsonc
// Every RTA query — correctness constraints per metadata_schema.json notes.routing_safety
{
  "always_and": [
    "corpus_scope != \"asa_only\"",       // after-session material never enters live path
    "target_audience != \"patient\"",     // patient handouts excluded from RTA entirely
    "review_status = \"approved\""         // (new) unreviewed/failed chunks quarantined
  ],
  "session_scope": "therapeutic_modality: ANY(\"DBT\")",
  "event_scope":   "session_event_tags: ANY(\"rupture_withdrawal\", \"rupture_repair\", \"none\")",
  "training_gate": "training_level_required: ANY(\"generalist\", \"supervised_trainee\")"
}
```

ASA differs only in that `corpus_scope != "asa_only"` is **lifted**, and
`target_audience = "patient"` is admitted **only** when `analysis_function = "homework_resource"`
(`rta_prompt/asa/searcher.py::_PATIENT_FACING_ALLOWED_FUNCTIONS`).

## R3 — Controlled-generation safety contract (response schema)

```json
{
  "type": "object",
  "properties": {
    "evidence_sufficiency":       {"type": "string", "enum": ["sufficient", "partial", "insufficient"]},
    "answerable":                 {"type": "boolean"},
    "guidance":                   {"type": "string"},
    "contraindications_surfaced": {"type": "array", "items": {"type": "string"}},
    "boundary_conflicts":         {"type": "array", "items": {"type": "string"}},
    "unmet_data_requirements":    {"type": "array", "items": {"type": "string"}},
    "citations":                  {"type": "array", "items": {"type": "integer"}}
  },
  "required": ["evidence_sufficiency", "answerable", "guidance",
               "contraindications_surfaced", "boundary_conflicts", "citations"]
}
```

- `answerable=false` → V4 abstention path (no free-text answer is rendered).
- non-empty `contraindications_surfaced` required whenever any retrieved passage carries `clinical_caution`
  (V1/V2). Reject/regenerate if a caution passage was present but the array is empty.
- `boundary_conflicts` forces the model to **enumerate** competing polarities instead of averaging them (V2).

## R4 — Strict system-prompt constraints (append to `retrieval_instruction_rta`)

```jsonc
{
  "hard_constraints": [
    "Use ONLY the numbered passages. If a required fact is absent, set answerable=false and stop.",
    "If ANY passage carries a clinical_caution or practice_recommendation_level of 'contraindicated' or 'use_with_caution', that caution MUST appear in contraindications_surfaced and be stated BEFORE the related recommendation.",
    "Never merge techniques across therapeutic_modality values. All passages here are one modality; do not import CBT/DBT/IPT logic not present in the passages.",
    "Do not average a 'recommended' statement with a 'contraindicated' one. List both in boundary_conflicts and preserve the stricter boundary.",
    "Every clinical claim ends with a [n] citation to a passage. Uncited claims are prohibited."
  ],
  "on_insufficiency": {"answerable": false, "guidance": "", "unmet_data_requirements": ["<what is missing>"]}
}
```

## R5 — Context caching for the RTA sub-second budget

Cache the static, per-session preamble (persona + RTA instruction block + hard constraints); vary only the
retrieved passages + transcript window per turn. Cuts prompt tokens and latency on every turn.

```python
import datetime
from google.generativeai import caching

session_cache = caching.CachedContent.create(
    model="models/gemini-1.5-flash-001",
    display_name=f"rta-{session_id}",
    system_instruction=static_rta_system_block,   # persona + instruction + R4 constraints (immutable/session)
    ttl=datetime.timedelta(minutes=50),            # ≈ session length; refresh on long sessions
)
model = genai.GenerativeModel.from_cached_content(cached_content=session_cache)
# per turn: model.generate_content([numbered_passages, transcript_window], generation_config=cfg_R3)
```

## R6 — Ingestion / schema deltas (single pre-import step)

Schema edits require `purge_datastore.py --confirm` + full re-ingest (`caveats.md §1`) — batch them:

| Change | File | Purpose |
|---|---|---|
| Add `chunk_text` (string) | `metadata_schema.json` + `uploader._serialize_chunk` | V1: full passage retrievable, no snippet cutoff |
| Add `review_status` enum `unreviewed\|approved`, `indexable` | `metadata_schema.json` | V5: gate RTA on human sign-off |
| Flip `_fallback_extraction` → `corpus_scope="asa_only"` | `metadata_gen.py` | V5: fail-safe on extraction failure |
| Propagate doc-level `clinical_caution` to all chunks | `metadata_gen.py` | V1: caution can't be orphaned |
| Caution-atomic chunk splitting; wire `skip_doc_types` | `chunker.py` | V1/V5: technique+contraindication stay together |

`_annotate_schema_for_indexing` auto-handles the new fields: string leaves get `retrievable+indexable+searchable`;
keep any purely-informational field in `_INFORMATIONAL_ONLY_FIELDS` (like `missingness`) to stay off the filter budget.

---

# Programmatic Safety Circuit Breakers — summary

| # | Failure | Primary control (deterministic) | Enforcement point |
|---|---|---|---|
| V1 | Snippet cutoff / lost prerequisite | `chunk_text` retrievable + `ExtractiveContentSpec` neighbors + caution-atomic chunking + doc→chunk caution propagation | `uploader`, `searcher.content_search_spec`, `chunker`, `metadata_gen` |
| V2 | Flattening / boundary softening | `BoostSpec` polarity-to-top + edge-positioning + `boundary_conflicts` schema field + `temperature=0.0` | `searcher.boost_spec`, `prompt_builder`, `response_gen` |
| V3 | Cross-framework pollution | Hard `therapeutic_modality: ANY(...)` pre-filter + query-expansion DISABLED + modality-purity guard | `rta/searcher._build_static_filter`, `searcher` |
| V4 | Helpfulness fabrication on data gap | `min_relevance_score` circuit breaker + `answerable`/`evidence_sufficiency` schema + citation-coverage gate | `searcher`, `response_gen._call_gemini`, pipeline |
| V5 | Untrustworthy metadata / fail-open defaults | Two-tier annotation contract + `review_status` gate + fail-safe `asa_only` defaults + enum-closed routing | `metadata_schema.json`, `metadata_gen`, `schema_loader` |

## Enforcement ordering (a break in the chain re-opens the failure)

```
indexable metadata  →  server-side AIP-160 pre-filter  →  bounded, in-scope result set
     →  retrieval-score circuit breaker (abstain if thin)  →  polarity-ordered prompt
     →  controlled-generation contract (answerable / contraindications / boundary_conflicts)
     →  citation-coverage gate  →  rendered guidance
```

Server-side controls (filter, boost) run **before** the model sees anything; the schema contract and citation
gate run **on** the model's output. No single layer is trusted alone.

---

## Constraints & currency notes

- **`searchable` is string-leaf only** — never set on integer/number/boolean (`_annotate_schema_for_indexing`
  already guards this). Discovery Engine enforces per-datastore caps on indexable/searchable field counts.
- **Schema edits are not retroactive** — every V1/V5 schema change implies purge + full re-ingest; land them together.
- **Regional endpoint routing still applies** (`_client_options`): a `GCP_LOCATION` mismatch sinkholes RPCs
  regardless of these specs.
- **SDK/model currency affects every remediation's reliability.** This repo pins `gemini-1.5-*` via the legacy
  `google-generativeai` SDK. Controlled-generation (`response_schema`), grounding fidelity, and JSON adherence
  are materially stronger on current Gemini models and the unified `google-genai` SDK; a migration is worth
  scheduling since R3/R4 depend directly on structured-output reliability. Keep provisioning + ingestion on
  `discoveryengine_v1` GA; scope any preview-only `ContentSearchSpec` capability to a narrowly-imported client
  (`discovery_engine_comparison.md §8`).
```
