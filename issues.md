# Problem List — Complex Elements for Human Review

Issues are ordered by priority: combination of implementation risk, human judgment required, and downstream impact if gotten wrong.

---

## P1 — Context-Aware Chunking Strategy

**Complexity: High | Risk: High | Effort estimate: 2–4 weeks**

### Why this is the hardest problem
Chunking is the single decision that most determines retrieval quality, yet there is no correct answer — optimal chunk size and boundary logic depend on document structure, query type, and the retrieval model. Getting it wrong degrades every downstream component.

### Specific challenges
- **Section boundary detection** in PDFs relies on visual cues (font size, boldness, whitespace) that are not reliably preserved in extracted text. A rule-based header detector will work on well-formatted textbooks and silently fail on journal articles or older scanned texts.
- **Semantic coherence vs. size budget**: A section that runs 4,000 tokens must be split, but naive token-splitting will break mid-sentence, mid-argument, or mid-table. A sentence-embedding similarity approach (split where cosine similarity drops) is more principled but requires tuning the similarity threshold per domain.
- **Tables, figures, and equations** either need to be embedded as a single chunk with a text description (requiring Gemini to summarize them), or skipped entirely. Skipping discards high-value reference data; bad summaries pollute the index.
- **Parent-document retrieval**: Some queries require more context than a single chunk provides. The architecture must decide whether to return the parent section alongside the matched chunk, which complicates the DataStore schema and retrieval logic.
- **Cross-document consistency**: The same section header "Chapter 3: Pharmacology" appears in dozens of textbooks with different meanings. The chunker must produce metadata that disambiguates these at query time.

### What requires human judgment
- Selection of chunking strategy per document class (textbook chapter vs. clinical guideline vs. research abstract).
- Definition of minimum acceptable chunk quality — a human needs to review samples and set the threshold for flagging chunks for re-processing.
- Decision on whether to include or skip figures/tables, and what level of Gemini description is "good enough."

### Suggested approach for review
Before full implementation, build a chunking evaluation harness: extract 5–10 representative PDFs, run 3 chunking strategies (fixed-token, structural, semantic), and score retrieval precision on 20 hand-written test queries. Do this before writing the indexer.

---

## P2 — Citation Accuracy and Traceability

**Complexity: High | Risk: High | Effort estimate: 1–3 weeks**

### Why this is critical
This is a clinical/scientific guidance tool. A response that cites "Smith et al., p. 47" but actually derived the claim from a different passage — or confabulated it — is worse than no citation. In a medical context, a wrong citation could constitute misinformation with direct patient-care consequences.

### Specific challenges
- **Vertex AI Search grounding metadata is coarse-grained.** When Gemini is used with Search grounding, the API returns `grounding_attributions` that map to retrieved segments, but the segment boundaries do not always align with individual factual claims in the generated text. A single sentence in the response may be attributed to a segment covering two pages.
- **Page-level citations require custom reconstruction.** The Discovery Engine search result contains the chunk document ID and possibly a snippet, but not page numbers. To produce `[Smith, p. 47]`-style citations, `citation_builder.py` must look up `page_start`/`page_end` from the chunk metadata stored in the DataStore or a separate metadata store, creating a dependency on metadata retrieval accuracy.
- **Multi-source synthesis is untraceable by design.** When Gemini synthesizes a response from 6 retrieved chunks, it does not produce a statement-level citation map. Attributing specific sentences to specific sources requires either: (a) instructing Gemini to cite inline (fragile, inconsistent), or (b) post-hoc attribution via semantic similarity between response sentences and chunk text (computationally expensive, imperfect).
- **Hallucinated content receives no citation.** If Gemini generates a claim not found in any retrieved chunk (despite instructions), that claim will simply appear without a citation — visually indistinguishable from a well-cited claim unless the UI explicitly marks un-cited spans.

### What requires human judgment
- Acceptable citation granularity (page-level vs. section-level vs. chunk-level) — set per use case.
- Whether to surface un-cited spans to the user with a warning, or suppress the response.
- Legal/clinical review of the citation disclaimer shown to users.

### Suggested approach for review
Implement a citation confidence score: for each claim in the response, compute cosine similarity between the claim sentence and the top retrieved chunk. Flag any claim below a threshold as "unverified." Run a red-team exercise with 10 deliberately unanswerable questions and verify the pipeline does not hallucinate citations.

---

## P3 — Metadata Schema Design and Gemini Extraction Reliability

**Complexity: Medium-High | Risk: Medium-High | Effort estimate: 1–2 weeks + ongoing tuning**

### Why this blocks everything else
The metadata schema is the contract between ingestion and retrieval. Fields defined poorly (too broad, too granular, inconsistently populated) make filtered search unreliable. Since Gemini generates these fields, any prompt weakness propagates to every document in the corpus.

### Specific challenges
- **Schema must be finalized before DataStore creation.** Vertex AI Search's unstructured DataStore schema is not easily modified post-ingestion; adding a new filterable field requires schema update + full re-import of all documents. Every schema change is expensive.
- **Controlled vocabulary vs. free-text fields**: `domain = "cardiology"` is filterable; `domain = "cardiac physiology"` from a different document is not equivalent. Gemini will produce variations unless given a strict enum list. But too-strict enums miss edge cases (what domain is "geriatric pharmacology"?).
- **Gemini structured output drift**: Even with a response schema specified, Gemini occasionally returns extra fields, nested structures, or violates cardinality (returns a string where an array is expected). Every ingestion run needs a validation layer that catches these and either coerces or flags.
- **Low-signal documents**: Introductory pages, tables of contents, bibliographies, and index sections produce metadata that is misleadingly similar to substantive content. These should be filtered out or tagged as `doc_type = "front_matter"` to be excluded from retrieval — but detecting them automatically is non-trivial.
- **`evidence_level` is domain-specific and contested.** GRADE A/B/C applies to clinical guidelines; it is meaningless for a textbook chapter on anatomy. The metadata schema needs to handle optional/conditional fields gracefully, and the Gemini prompt must not be asked to produce fields that don't apply.

### What requires human judgment
- Final selection of `domain` and `subdomain` controlled vocabulary — requires a domain expert to define the taxonomy before any ingestion runs.
- Validation thresholds: how many field violations in a batch before the import is halted for review vs. auto-corrected.
- Decision on front-matter filtering: a human should audit a sample of filtered-out chunks before finalizing the exclusion rules.

### Suggested approach for review
Run a metadata generation pilot on 10 diverse documents before finalizing the schema. Have a domain expert review 50 randomly sampled chunk metadata records and score accuracy per field. Use this to identify which fields are reliable enough to use in filter queries vs. which are informational-only.

---

## P4 — PDF Extraction Quality for Complex Layouts

**Complexity: Medium | Risk: Medium | Effort estimate: 1 week + corpus-specific fixes**

### Specific challenges
- Multi-column journal PDFs, scanned textbooks, PDFs with embedded figures spanning multiple pages, and right-to-left or non-Latin scripts all require special handling.
- Document AI adds cost and latency; a heuristic to decide when to fall back to OCR needs calibration.
- No extraction pipeline produces perfect output — budget for a manual review and correction workflow for high-priority source documents.

### What requires human judgment
- Which documents in the corpus are high-enough priority to warrant manual extraction QA.
- Decision on whether to use Document AI universally (higher quality, higher cost) or only on fallback.

---

## P5 — Operational Reliability and Re-ingestion Safety

**Complexity: Medium | Risk: Medium | Effort estimate: 1 week**

### Specific challenges
- No built-in deduplication in Vertex AI Search; re-running ingestion on the same document silently creates duplicate entries that inflate retrieval noise.
- The async nature of `ImportDocuments` means the pipeline can report "success" before documents are actually searchable; integration tests against a live DataStore must account for propagation delay.
- Schema changes require coordinated DataStore purge + re-ingestion — this process needs to be documented, scripted, and tested before the corpus grows large.

### What requires human judgment
- Acceptable re-ingestion window (how long can a document be unavailable during an update?).
- Whether to maintain a shadow DataStore for zero-downtime schema migrations.

---

## #ALTERNATE — One-Time Corpus Scan vs. Continuous Watcher

**Complexity: Low | Risk: Low | Effort estimate: < 1 day**

### The problem with the continuous watcher as a primary ingestion path
`CorpusWatcher` + `PDFEventHandler` require a persistent process with a live `watchdog` `Observer`. In cloud or containerised deployments, this is an operational liability: the process must stay up, handle SIGTERM gracefully, and survive restarts without re-processing the entire corpus. The manifest mitigates double-ingestion but does not make the watcher fault-tolerant — events fired while the process is down are silently lost unless a catch-up scan runs on next startup.

### The alternate
`CorpusWatcher.catchup_scan()` already implements the core logic: iterate `corpus/`, call `is_processed()` per file, run the pipeline for new files only, persist the manifest. Calling this once and exiting — without ever starting the `Observer` — is a fully functional ingestion path that:
- Requires no background threads or signal handling
- Runs to completion and exits cleanly (suitable for CI steps, cron jobs, Kubernetes `Job`s)
- Produces identical manifest state to the watcher path
- Avoids `watchdog` inotify descriptor limits on systems with large directory trees

### What requires human judgment
- Whether the acceptable ingestion latency for new documents is seconds (watcher) or minutes-to-hours (scheduled scan). This is a product decision, not a technical one.
- In production, the right default for most cloud deployments is almost certainly the scheduled scan triggered by a GCS Eventarc notification or a Cloud Scheduler job — not the local watcher.
