# Bootstrap Report — Corpus Rebuild Agent Briefing

This document is written for the next agent (or engineer) picking up this work. It provides orientation, specifies which files to read, identifies what requires clinician/SME sign-off before proceeding, and marks which config files are blocked vs. unblocked. Read this document first, then read the files listed under "Files to Read Before Acting."

---

## What Has Been Done

A full audit of the prior corpus and a new corpus design have been produced. The three key outputs are:

| Document | Location | Purpose |
|---|---|---|
| Comparative analysis of old vs. new corpus | `corpus/COMPARATIVE_ANALYSIS.md` | Documents every structural change, pros/cons, and budget |
| Stakeholder decision report | `corpus/REPORT.md` | 11 decisions with EASY/MEDIUM/HARD ratings for clinician/business review |
| RTA curation guide | `corpus/CORPUS_NOTES_RTA.md` | Authoritative document spec for real-time in-session corpus |
| ASA curation guide | `corpus/CORPUS_NOTES_ASA.md` | Authoritative document spec for after-session analysis corpus |

The old corpus had no intelligent metadata schema — only `document_type` and `therapy_type` fields in manually curated JSONL files, with purely semantic retrieval. The current project's `config/metadata_schema.json` is an unused biomedical template. **Neither has been applied to a production ingestion run for the new corpus.** The new schema is specified in `CORPUS_NOTES_RTA.md` and `CORPUS_NOTES_ASA.md` but has not yet been written to any config file.

---

## Primary Task for This Agent

**Generate reader-friendly `.docx` versions of the corpus notes and decision documents for SME/clinician review.**

The corpus notes contain highly specific clinical taxonomy decisions (which session event types to include, which modalities to tag, how to represent contraindications) that require a licensed clinician or clinical supervisor to review before the schema is finalized. The `.docx` format is required because the reviewers are clinicians, not engineers.

Documents to convert (in priority order):

1. `corpus/REPORT.md` — the primary decision document for non-technical stakeholders
2. `corpus/COMPARATIVE_ANALYSIS.md` — full analysis; useful for a clinical director or PI
3. `corpus/CORPUS_NOTES_RTA.md` — detailed RTA curation guide; for a clinical SME reviewing session event taxonomy and modality scope
4. `corpus/CORPUS_NOTES_ASA.md` — detailed ASA curation guide; for the same SME reviewing post-session evidence integration

### Generating .docx files

Use `pandoc`. Check if it is installed first:

```bash
pandoc --version
```

If not installed:
```bash
brew install pandoc          # macOS
# or: pip install pandoc     # if using pip-distributed pandoc
```

Convert each file:
```bash
pandoc corpus/REPORT.md -o corpus/REPORT.docx
pandoc corpus/COMPARATIVE_ANALYSIS.md -o corpus/COMPARATIVE_ANALYSIS.docx
pandoc corpus/CORPUS_NOTES_RTA.md -o corpus/CORPUS_NOTES_RTA.docx
pandoc corpus/CORPUS_NOTES_ASA.md -o corpus/CORPUS_NOTES_ASA.docx
```

To apply a reference style document for professional formatting (if a `.docx` template exists):
```bash
pandoc corpus/REPORT.md --reference-doc=reference.docx -o corpus/REPORT.docx
```

Verify each output opens correctly and that tables render as Word tables, not raw pipe syntax. If tables are malformed, add `--columns=200` to prevent line-wrapping in table cells.

---

## Critical Elements Requiring SME / Clinician Sign-Off

The corpus notes contain sections marked `# RECOMMENDED CHANGE` / `# END RECOMMENDED CHANGE`. These are open clinical decisions where the author has proposed a change but has explicitly flagged that expert review is required before the change is committed to the schema or corpus. **Do not implement any RECOMMENDED CHANGE item without explicit clinician approval.**

The table below lists each open decision, the file and section where it lives, and the nature of the sign-off required.

### Schema Decisions (Clinician must approve enum values before `metadata_schema.json` is modified)

| Decision | File | Section | What clinician must decide |
|---|---|---|---|
| Add `use_with_caution` and `contraindicated` to `practice_recommendation_level` | `CORPUS_NOTES_RTA.md` | Fields to Modify → `evidence_level` | Are these the right negative polarity values? Are there edge cases between the two? |
| Add `SE`, `SP`, `UP` to `therapeutic_modality` enum | `CORPUS_NOTES_RTA.md` | New Fields → `therapeutic_modality` | Confirm these are operationally distinct enough to warrant separate retrieval tags |
| Add `dissociative_disorders`, `health_anxiety`, `hoarding`, `bfrb`, `autism_spectrum`, `perinatal` to `clinical_presentation` | `CORPUS_NOTES_RTA.md` | New Fields → `clinical_presentation` | Confirm these are priority presentations for the target clinical population |
| Add 8 new `session_event_tags`: `shame_activation`, `somatic_activation`, `therapist_self_disclosure`, `avoidance_safety_behavior`, `minority_stress_disclosure`, `cultural_mismatch`, `premature_termination_signal`, `grief_loss_activation` | `CORPUS_NOTES_RTA.md` | New Fields → `session_event_tags` | Confirm all 8 are high-frequency enough to justify their own retrieval tag; confirm definitions are clinically accurate |
| Add `pre_intake_consultation` to `session_phase` | `CORPUS_NOTES_RTA.md` | New Fields → `session_phase` | Confirm this phase is in scope for TherAssist |
| Add `clinical_caution`, `training_level_required`, `risk_dimension_tags` as new fields | `CORPUS_NOTES_RTA.md` | New Fields → Three new fields block | Confirm `training_level_required` thresholds are calibrated correctly for the target therapist population; confirm `risk_dimension_tags` values cover monitored risk dimensions |
| Add `termination_planning` to `analysis_function` enum | `CORPUS_NOTES_ASA.md` | New Fields → `analysis_function` | Confirm termination is a named ASA function for this system |
| Add `open_ended` to `time_horizon` enum | `CORPUS_NOTES_ASA.md` | New Fields → `time_horizon` | Confirm open-ended therapy is in scope for the longitudinal management pipeline |

### Corpus Scope Decisions (Clinician must approve before sourcing or ingesting documents)

| Decision | File | Section | What clinician must decide |
|---|---|---|---|
| Promote LGBTQ+-affirmative and culturally responsive texts from ASA-only to RTA Tier 2 | `CORPUS_NOTES_RTA.md` | Tier 2 → RECOMMENDED CHANGE | Should minority stress disclosures and cultural misattunements trigger real-time guidance? |
| Include moderator sub-tables from meta-analysis Results sections (revised from blanket exclusion) | `CORPUS_NOTES_RTA.md` | Tier 3 → RECOMMENDED CHANGE | Clinician must confirm that moderator tables are actionable for real-time use |
| Add EMDR, somatic, and IFS source texts to RTA Tier 1 | `CORPUS_NOTES_RTA.md` | Tier 1 → RECOMMENDED CHANGE | Confirm these modalities are in scope for Phase 1 |
| Add youth-specific texts (DBT-A, TF-CBT, OCD children, Beck CBT children) to RTA Tier 1 | `CORPUS_NOTES_RTA.md` | Tier 1 → RECOMMENDED CHANGE | Confirm youth presentations are in scope for Phase 1 |
| Add DSM-5 Cultural Formulation Interview materials to ASA corpus | `CORPUS_NOTES_ASA.md` | Tier 2 → RECOMMENDED CHANGE | Confirm CFI is relevant to the case formulation update function |
| Include RCTs and meta-analyses in ASA corpus | `CORPUS_NOTES_ASA.md` | Tier 1 section | Clinical-legal decision: does surfacing specific RCT findings to therapists create liability? |

### Architecture Decisions (Engineering lead + clinician must agree before implementation)

| Decision | File | Section | What must be decided |
|---|---|---|---|
| Passive risk monitoring retrieval pass on every session (independent of `crisis_escalation` trigger) | `CORPUS_NOTES_RTA.md` | Implementation Notes #7 | Is background risk retrieval in scope? What priority level relative to acute guidance? |
| ASA chronic risk tracking separate from `risk_documentation` analysis function | `CORPUS_NOTES_ASA.md` | Implementation Notes #8 | Same question applied to ASA pipeline |
| Build full ASA multi-hop pipeline now or defer to Phase 2 | `corpus/REPORT.md` | Decision #9 | Scope and timeline call; see REPORT.md for full framing |

---

## Files to Read Before Acting

Read these files in order before making any code or config changes.

### 1. Project instructions
```
CLAUDE.md                                  # Root — project status, commands, architecture, known issues
ingestion/INGESTION_TUTORIAL.md            # Ingestion pipeline walkthrough
```

### 2. Corpus design documents
```
corpus/REPORT.md                           # Stakeholder decisions (read first for orientation)
corpus/COMPARATIVE_ANALYSIS.md            # Full old-vs-new analysis
corpus/CORPUS_NOTES_RTA.md                # RTA corpus spec and schema proposal
corpus/CORPUS_NOTES_ASA.md                # ASA corpus spec and schema extensions
corpus/REVIEW_CORPUS.md                   # Audit of the prior corpus being replaced
```

### 3. Config files (read; do not modify until cleared — see section below)
```
config/metadata_schema.json               # BLOCKED — biomedical template; must be replaced
config/prompt_config.yaml                 # UNBLOCKED — biomedical personas; rebuild is safe now
config/chunk_config.yaml                  # PARTIALLY BLOCKED — see notes below
config/settings.py                        # Read for env var reference; no changes required
```

### 4. Ingestion source files (read; do not modify until schema finalized)
```
models.py                                 # ChunkMetadata Pydantic model — must match new schema
ingestion/metadata_gen.py                 # Gemini extraction prompt — BLOCKED until schema final
ingestion/chunker.py                      # ChunkerConfig — Known Issue #1 (from_yaml not implemented)
ingestion/indexer.py                      # Vertex AI Search import — BLOCKED until schema final
ingestion/scanner.py                      # CorpusScanner — no changes required at this stage
```

### 5. Scripts (read; do not run except as noted)
```
scripts/setup_vertex_search.py            # BLOCKED — do not run until schema is finalized
scripts/purge_datastore.py               # BLOCKED — destructive; requires explicit human --confirm
scripts/batch_ingest.py                  # BLOCKED — do not run until schema is finalized
```

---

## Config Directory Status

### `config/metadata_schema.json` — BLOCKED

**Current state:** General biomedical template. Domains are `cardiology`, `oncology`, `pharmacology`, etc. Evidence levels are GRADE A/B/C/D. The `entities` field is defined as "drugs, conditions, genes, procedures." None of this maps to psychotherapy.

**What is needed:** Complete replacement with the psychotherapy schema defined in `CORPUS_NOTES_RTA.md` (Recommended Full Schema section) extended with the ASA additions from `CORPUS_NOTES_ASA.md` (Full ASA-Extended Schema section).

**Why blocked:** The schema JSON cannot be finalized until all RECOMMENDED CHANGE enum decisions above have SME sign-off. Schema registration in Vertex AI Search is immutable without a full purge and re-ingestion — a premature schema commit forces a second purge cycle. Cost of getting this wrong: ~$200–$400 GCP compute + 4–8 engineering hours for an additional ingestion run.

**Unblock condition:** Clinician approves the enum additions listed in "Schema Decisions" above. Then update `config/metadata_schema.json`, run `scripts/setup_vertex_search.py`, and proceed with ingestion.

### `config/prompt_config.yaml` — UNBLOCKED

**Current state:** 8 biomedical personas (cardiology, oncology, pharmacology, neurology, internal_medicine, anatomy, physiology, biochemistry) plus a generic `default`. All psychotherapy queries currently fall through to `default`.

**What is needed:** Replace all biomedical personas with psychotherapy domain personas. Minimum set:
- `psychotherapy_general` (fallback)
- `cognitive_behavioral`
- `trauma_focused`
- `psychodynamic`
- `dialectical_behavior`
- `crisis_intervention`
- `therapeutic_alliance`

Each persona should instruct the LLM to respond as an experienced clinician-supervisor in that domain, referencing session-level clinical events rather than research outcomes. The `retrieval_instruction` template variable `{n_passages}` is currently undocumented (Known Issue #2 in `CLAUDE.md`) — add it to the variable legend at the top of the file.

**Unblock condition:** None. This can proceed immediately. No SME sign-off required; this is a prompt engineering task.

**Cost:** 4–8 engineering hours.

### `config/chunk_config.yaml` — PARTIALLY BLOCKED

**Current state:** The chunking parameters themselves (max_tokens: 512, overlap: 64, semantic_similarity_threshold: 0.75) are reasonable defaults for dense clinical text. The `embedding_model` is `all-MiniLM-L6-v2` — a general-purpose sentence transformer adequate for initial testing but not optimized for clinical or psychotherapy text.

**What is needed:**
- `ChunkerConfig.from_yaml()` must be implemented before this file has any effect (Known Issue #1 in `CLAUDE.md`). The class currently uses Python hardcoded defaults and ignores this YAML entirely.
- The `embedding_model` value may need to change to `pritamdeka/S-PubMedBert-MS-MARCO` (already noted in the YAML as a higher-quality clinical alternative) or a psychotherapy-specific model, pending SME input on text domain similarity to biomedical vs. general clinical text.
- The `header_patterns` list uses academic paper section headers (`Abstract`, `Methods`, `Results`). These are appropriate for RCTs in the ASA corpus but may miss therapy manual structure (e.g., "Session 4:", "Phase II:", "Therapist Guidance:"). This should be reviewed and extended.

**Unblock condition for `from_yaml()` implementation:** None — this is a Known Issue fix that can proceed. **Unblock condition for `embedding_model` and `header_patterns` changes:** SME guidance on corpus text characteristics.

---

## Cost of Implementation Reference

From `corpus/COMPARATIVE_ANALYSIS.md` Section 4, reproduced here for convenience:

| Phase | Scope | Estimated cost |
|---|---|---|
| Phase 1 — RTA only, priority modalities | Schema rebuild, prompt rebuild, manual acquisition (~30 texts), ingestion | $5,000–$10,000 |
| Phase 2 — Full modality coverage + cultural texts | Remaining manual acquisition (~10 texts), re-ingestion | $2,000–$4,000 |
| Phase 3 — ASA pipeline | Multi-hop retrieval architecture, ASA corpus acquisition (~25 texts), ASA prompt design | $6,000–$12,000 |
| **Total across all phases** | | **$10,400–$24,900** |

Cost breakdown by category:
- Corpus acquisition (all phases): $3,000–$6,500
- GCP compute (schema re-registration + indexing + Gemini extraction): $210–$410
- Engineering labor at $100–150/hr blended: $7,200–$18,000

The re-ingestion is required regardless of the scope of these changes, because the prior corpus had no chunk-level metadata and the current project schema is a biomedical placeholder. There is no path to functional retrieval filtering without a full purge and re-ingestion.

---

## What This Agent Should NOT Do Without Explicit Approval

The following actions are destructive or irreversible without a purge cycle. Do not perform them until SME schema decisions are finalized and a human has explicitly approved:

1. **Modify `config/metadata_schema.json`** — changes the Vertex AI Search schema contract; cannot be partially rolled back
2. **Run `scripts/purge_datastore.py`** — deletes all indexed documents; requires `--confirm` flag and human intent
3. **Run `scripts/setup_vertex_search.py`** — registers the schema; running with the current biomedical schema would lock in the wrong field definitions
4. **Run `scripts/batch_ingest.py`** (especially with `--force`) — ingests documents against whatever schema is currently registered
5. **Modify `models.py` `ChunkMetadata`** — the Pydantic model must match the registered DataStore schema exactly; mismatches cause silent metadata drop on import
6. **Modify `ingestion/metadata_gen.py` extraction prompts** — prompt changes must be derived from the finalized schema; premature changes produce metadata that does not validate

## What This Agent CAN Do Without Approval

1. Generate `.docx` output files from markdown documents using `pandoc`
2. Rebuild `config/prompt_config.yaml` with psychotherapy personas
3. Implement `ChunkerConfig.from_yaml()` in `ingestion/chunker.py` (Known Issue #1)
4. Fix `{n_passages}` documentation in `config/prompt_config.yaml` (Known Issue #2)
5. Fix `CitationBuilder` import decision in `generation/response_gen.py` (Known Issue #3) — note: this requires reading the current `generation/__init__.py` to determine whether generation or caller owns citation
6. Extend `config/chunk_config.yaml` header patterns to cover therapy manual structure (section headed "Session N:", phase headers, etc.) — low-risk config addition
7. Read and report on any file in the repository
