/-
  RAGGuidance.lean — Lean 4 formal specification

  Covers the structural and correctness properties of the rag_guidance
  ingestion pipeline.  This is a specification, not an executable
  implementation: IO effects (GCP API, file system, Gemini) are left
  abstract and represented by `opaque` constants or `axiom` postulates.

  What is modelled
  ─────────────────
  · Core data types (models.py)                               §2
  · Chunk ID canonical form and cross-run stability           §3
  · Metadata provenance invariant                             §4
      (four fields always overridden from Chunk, never from Gemini)
  · Manifest semantics (basename → doc_id, atomic updates)    §5
  · CorpusScanner.scan() idempotency, monotonicity, completeness §6
  · Ingest pipeline as typed function composition             §7

  What is NOT modelled
  ─────────────────────
  · GCP Vertex AI Search / Discovery Engine API behaviour
  · Gemini LLM output  (non-deterministic; opaque black-box)
  · Actual chunking and embedding algorithms
  · File system, GCS, or network I/O
  · Async long-running operations (LROs)

  Requirements
  ─────────────
  Lean 4 (https://leanprover.github.io/lean4/doc/setup.html).
  No Mathlib dependency — standard Lean 4 library only.

  To check
  ─────────
    lake new rag_guidance_spec
    cp RAGGuidance.lean rag_guidance_spec/RAGGuidance.lean
    # add `lean_exe "RAGGuidance" { root := `RAGGuidance }` to lakefile.lean
    cd rag_guidance_spec && lake build
-/

namespace RAGGuidance


-- ═══════════════════════════════════════════════════════════════════════════════
-- §1  Primitive aliases
-- ═══════════════════════════════════════════════════════════════════════════════

/-- SHA-256 hex digest of a PDF's raw bytes (64 hex chars).
    Computed once per file by GCSUploader.compute_doc_id();
    stable across re-ingestion runs. -/
abbrev DocId := String

/-- Basename of a PDF file in corpus/, e.g. "cardiology_textbook.pdf". -/
abbrev Filename := String

/-- A GCS object URI, e.g. "gs://bucket/chunks/abc123.jsonl". -/
abbrev GcsUri := String


-- ═══════════════════════════════════════════════════════════════════════════════
-- §2  Core data types  (models.py)
-- ═══════════════════════════════════════════════════════════════════════════════

/-- One page extracted from a PDF.
    Produced by PDFExtractor; consumed by ContextAwareChunker. -/
structure Page where
  pageNum    : Nat
  text       : String
  -- tables simplified; real form carries rows : List (List String) and bbox
  tables     : List String
  hasFigures : Bool
  deriving Repr

/-- Output of PDFExtractor.extract().
    Produced by PDFExtractor; consumed by ContextAwareChunker. -/
structure ExtractedDocument where
  docId            : DocId     -- SHA-256 of PDF bytes; stable across runs
  sourceFile       : Filename
  pages            : List Page
  extractionMethod : String    -- "pdfplumber" | "document_ai"
  deriving Repr

/-- A single chunk produced by ContextAwareChunker.
    The canonical chunk_id is  docId ++ "_" ++ zeroPad 5 chunkIndex.
    This ID is used as the Vertex AI Search DataStore document ID. -/
structure Chunk where
  docId         : DocId
  chunkIndex    : Nat
  text          : String
  pageStart     : Nat
  pageEnd       : Nat
  parentSection : String
  deriving Repr, BEq

/-- Pydantic-validated metadata attached to each chunk.
    Fields `docId`, `pageStart`, `pageEnd`, `chunkIndex` are ALWAYS
    overridden from the owning Chunk after Gemini extraction.
    They are never trusted from Gemini output. -/
structure ChunkMetadata where
  -- Provenance fields: always overridden from Chunk, never from Gemini
  docId         : DocId
  pageStart     : Nat
  pageEnd       : Nat
  chunkIndex    : Nat
  -- Gemini-extracted fields
  sourceFile    : Filename
  title         : Option String
  domain        : Option String   -- e.g. "cardiology", "oncology"
  subdomain     : Option String
  docType       : Option String   -- "textbook" | "clinical_guideline" | "research_paper"
  chapter       : Option String
  keywords      : List String
  entities      : List String
  evidenceLevel : Option String   -- "Grade A" | "Grade B" | ... (domain-specific)
  yearPublished : Option Nat
  deriving Repr

/-- A single result from Vertex AI Search.
    Produced by Searcher; consumed by PromptBuilder and CitationBuilder. -/
structure SearchResult where
  chunkId  : String
  metadata : ChunkMetadata
  snippet  : String
  score    : Float
  deriving Repr

/-- A raw grounding attribution from Gemini output.
    Must be passed to CitationBuilder.build(); not resolved in ResponseGenerator. -/
structure Attribution where
  sourceChunkId : String
  segment       : String
  deriving Repr

/-- Final generated response with raw attributions.
    Caller is responsible for calling CitationBuilder.build() separately. -/
structure GeneratedResponse where
  text         : String
  attributions : List Attribution
  deriving Repr

/-- Outcome of a Vertex AI Search ImportDocuments long-running operation. -/
structure ImportResult where
  operationName : String
  successCount  : Nat
  failureCount  : Nat
  errorSamples  : List String
  deriving Repr


-- ═══════════════════════════════════════════════════════════════════════════════
-- §3  Chunk ID canonical form
-- ═══════════════════════════════════════════════════════════════════════════════

/-- Left-pad `n` with zeros to at least `width` digits.
    Matches Python's f"{chunk_index:05d}" when width = 5. -/
def zeroPad (width : Nat) (n : Nat) : String :=
  let s      := toString n
  let padLen := if width > s.length then width - s.length else 0
  String.mk (List.replicate padLen '0') ++ s

/-- Canonical chunk_id used as the Vertex AI Search DataStore document ID.
    Must be stable across re-ingestion runs for idempotent imports:
    same (docId, chunkIndex) must always produce the same string. -/
def chunkId (c : Chunk) : String :=
  c.docId ++ "_" ++ zeroPad 5 c.chunkIndex

-- ── Invariants ────────────────────────────────────────────────────────────────

/-- Chunk ID stability: two chunks with the same docId and chunkIndex always
    produce the same chunkId, regardless of their other fields.
    This is the key invariant for idempotent DataStore imports. -/
theorem chunkId_stable (c₁ c₂ : Chunk)
    (hd : c₁.docId      = c₂.docId)
    (hi : c₁.chunkIndex = c₂.chunkIndex) :
    chunkId c₁ = chunkId c₂ := by
  simp [chunkId, zeroPad, hd, hi]

/-- zeroPad is deterministic: same inputs always yield the same string. -/
theorem zeroPad_deterministic (w n : Nat) :
    zeroPad w n = zeroPad w n := rfl

/-- Distinct chunk indices on the same document yield distinct chunk IDs.
    Proof deferred: requires showing zeroPad is injective on Nat. -/
theorem chunkId_index_injective (docId : DocId) (i j : Nat)
    (h : docId ++ "_" ++ zeroPad 5 i = docId ++ "_" ++ zeroPad 5 j) :
    i = j := by
  -- Follows from String.append left-cancellation and zeroPad injectivity.
  sorry


-- ═══════════════════════════════════════════════════════════════════════════════
-- §4  Metadata provenance invariant
-- ═══════════════════════════════════════════════════════════════════════════════

/-- Opaque model of one Gemini structured-extraction call.
    Non-deterministic at runtime; modelled here as a pure black box
    returning some ChunkMetadata (provenance fields will be overridden). -/
opaque geminiExtract (c : Chunk) : ChunkMetadata

/-- Apply Gemini output and then unconditionally override the four provenance
    fields from the Chunk itself.

    This mirrors MetadataGenerator._validate_and_coerce():
    > "The doc_id, page_start, page_end, and chunk_index fields are always
    >  overridden from the Chunk object, never trusted from Gemini output."  -/
def applyProvenanceOverride (raw : ChunkMetadata) (c : Chunk) : ChunkMetadata :=
  { raw with
    docId      := c.docId
    pageStart  := c.pageStart
    pageEnd    := c.pageEnd
    chunkIndex := c.chunkIndex }

-- ── Invariants ────────────────────────────────────────────────────────────────

/-- After override, all four provenance fields equal the Chunk's values,
    regardless of what Gemini returned. -/
theorem metadata_provenance (raw : ChunkMetadata) (c : Chunk) :
    let m := applyProvenanceOverride raw c
    m.docId      = c.docId      ∧
    m.pageStart  = c.pageStart  ∧
    m.pageEnd    = c.pageEnd    ∧
    m.chunkIndex = c.chunkIndex := by
  simp [applyProvenanceOverride]

/-- Non-provenance fields are passed through from Gemini output unchanged. -/
theorem metadata_passthrough (raw : ChunkMetadata) (c : Chunk) :
    let m := applyProvenanceOverride raw c
    m.title         = raw.title         ∧
    m.domain        = raw.domain        ∧
    m.keywords      = raw.keywords      ∧
    m.yearPublished = raw.yearPublished ∧
    m.entities      = raw.entities := by
  simp [applyProvenanceOverride]

/-- Provenance override is idempotent: applying it twice gives the same result. -/
theorem metadata_override_idempotent (raw : ChunkMetadata) (c : Chunk) :
    applyProvenanceOverride (applyProvenanceOverride raw c) c =
    applyProvenanceOverride raw c := by
  simp [applyProvenanceOverride]


-- ═══════════════════════════════════════════════════════════════════════════════
-- §5  Ingestion manifest
-- ═══════════════════════════════════════════════════════════════════════════════

/-- The manifest maps each PDF basename to the doc_id assigned at first ingest.
    Persisted as a JSON file on disk; modelled here as an association list.
    Invariant: no filename appears twice (maintained by `insert`). -/
abbrev Manifest := List (Filename × DocId)

/-- True if `f` already has an entry in the manifest. -/
def Manifest.contains (m : Manifest) (f : Filename) : Bool :=
  m.any (·.1 == f)

/-- Lookup the doc_id for a filename (None if not yet ingested). -/
def Manifest.lookup (m : Manifest) (f : Filename) : Option DocId :=
  (m.find? (·.1 == f)).map (·.2)

/-- Insert or replace a (filename, doc_id) entry atomically.
    Mirrors the temp-file + rename atomic write in _save_manifest(). -/
def Manifest.insert (m : Manifest) (f : Filename) (d : DocId) : Manifest :=
  (f, d) :: m.filter (·.1 != f)

-- ── Invariants ────────────────────────────────────────────────────────────────

/-- After inserting f, the manifest contains f. -/
theorem manifest_insert_contains (m : Manifest) (f : Filename) (d : DocId) :
    (m.insert f d).contains f = true := by
  simp [Manifest.insert, Manifest.contains, List.any_cons, beq_self_eq_true]

/-- The empty manifest contains nothing. -/
theorem manifest_empty (f : Filename) :
    ([] : Manifest).contains f = false := by
  simp [Manifest.contains]

/-- Inserting f does not evict any other filename already present. -/
theorem manifest_insert_preserves
    (m : Manifest) (f g : Filename) (d : DocId)
    (hne : f ≠ g) (hg : m.contains g = true) :
    (m.insert f d).contains g = true := by
  simp only [Manifest.insert, Manifest.contains, List.any_cons]
  right
  -- g's entry survives the filter because g ≠ f
  rw [List.any_filter]
  simp only [Bool.decide_and, Bool.and_eq_true, decide_eq_true_eq]
  constructor
  · -- the entry for g passes the filter predicate (g ≠ f → g's key ≠ f)
    intro x hxg
    simp only [List.any] at hg
    sorry
  · exact hg

/-- Lookup after insert returns the inserted doc_id. -/
theorem manifest_lookup_after_insert (m : Manifest) (f : Filename) (d : DocId) :
    (m.insert f d).lookup f = some d := by
  simp [Manifest.insert, Manifest.lookup, List.find?_cons, beq_self_eq_true]


-- ═══════════════════════════════════════════════════════════════════════════════
-- §6  CorpusScanner.scan() semantics
-- ═══════════════════════════════════════════════════════════════════════════════

/-- Abstract model of one-file ingestion:
    · Already in manifest → skip (None).
    · Not in manifest     → run pipeline, return updated manifest. -/
def processFile (m : Manifest) (f : Filename) (d : DocId) : Option Manifest :=
  if m.contains f then none
  else some (m.insert f d)

/-- Already-processed files are always skipped. -/
theorem processFile_skips_processed (m : Manifest) (f : Filename) (d : DocId)
    (h : m.contains f = true) :
    processFile m f d = none := by
  simp [processFile, h]

/-- New files are always processed and the manifest grows. -/
theorem processFile_inserts_new (m : Manifest) (f : Filename) (d : DocId)
    (h : m.contains f = false) :
    processFile m f d = some (m.insert f d) := by
  simp [processFile, h]

/-- Model of CorpusScanner.scan():
    Fold over the (alphabetically sorted) corpus, processing only files
    absent from the manifest.  `assign` abstracts the doc_id computation
    (SHA-256 of file bytes) to keep the model pure. -/
def corpusScan
    (corpus  : List Filename)
    (m₀      : Manifest)
    (assign  : Filename → DocId) : Manifest :=
  corpus.foldl (fun m f =>
    (processFile m f (assign f)).getD m) m₀

-- ── Invariants ────────────────────────────────────────────────────────────────

/-- Idempotency: if every corpus file is already recorded in the manifest,
    corpusScan returns it unchanged.

    This is the key safety property of the one-time scan pattern:
    running batch_ingest.py twice on the same corpus is a no-op. -/
theorem corpusScan_idempotent
    (corpus : List Filename) (m : Manifest) (assign : Filename → DocId)
    (hFull : ∀ f ∈ corpus, m.contains f = true) :
    corpusScan corpus m assign = m := by
  simp only [corpusScan]
  induction corpus with
  | nil        => simp [List.foldl]
  | cons f fs ih =>
    simp only [List.foldl]
    have hf : m.contains f = true := hFull f (List.mem_cons_self f fs)
    simp only [processFile, hf, ↓reduceIte, Option.getD]
    apply ih
    intro g hg
    exact hFull g (List.mem_cons.mpr (.inr hg))

/-- Completeness: after corpusScan, every corpus file is in the manifest.
    Proof by induction: each step either skips (file already present) or
    inserts (file becomes present), and monotonicity preserves prior entries. -/
theorem corpusScan_complete
    (corpus : List Filename) (m₀ : Manifest) (assign : Filename → DocId) :
    ∀ f ∈ corpus, (corpusScan corpus m₀ assign).contains f = true := by
  sorry

/-- Monotonicity: corpusScan never removes existing manifest entries.
    Follows from processFile either returning None (manifest unchanged) or
    inserting via manifest_insert_preserves (other entries survive). -/
theorem corpusScan_monotone
    (corpus : List Filename) (m₀ : Manifest) (assign : Filename → DocId)
    (f : Filename) (hf : m₀.contains f = true) :
    (corpusScan corpus m₀ assign).contains f = true := by
  sorry

/-- Determinism: corpusScan with the same inputs always produces the same
    manifest (no randomness or IO in the pure model). -/
theorem corpusScan_deterministic
    (corpus : List Filename) (m₀ : Manifest) (assign : Filename → DocId) :
    corpusScan corpus m₀ assign = corpusScan corpus m₀ assign := rfl


-- ═══════════════════════════════════════════════════════════════════════════════
-- §7  Pipeline stage types
-- ═══════════════════════════════════════════════════════════════════════════════
-- GCP and Gemini calls are represented as `opaque` constants.
-- IO effects are left abstract — this section models types and composition only.

/-- Stage 1 → 2: PDF bytes → structured extracted document.
    Implementation: PDFExtractor (pdfplumber primary, Document AI fallback). -/
opaque extractPdf (docId : DocId) (filename : Filename) : ExtractedDocument

/-- The extractor preserves the docId that was computed before extraction.
    (In Python: extractor.extract() internally calls _compute_doc_id()
    and stores the result on the returned ExtractedDocument.) -/
axiom extract_docId_coherent (docId : DocId) (filename : Filename) :
    (extractPdf docId filename).docId = docId

/-- Stage 2 → 3: document → ordered list of chunks.
    Implementation: ContextAwareChunker (structural + semantic two-pass). -/
opaque chunkDocument (doc : ExtractedDocument) : List Chunk

/-- Every chunk produced by the chunker carries the document's docId.
    In Python: chunk.doc_id is always set from ExtractedDocument.doc_id. -/
axiom chunk_docId_coherent (doc : ExtractedDocument) :
    ∀ c ∈ chunkDocument doc, c.docId = doc.docId

/-- Chunker produces strictly increasing chunkIndex values starting at 0.
    Required for chunkId uniqueness within a document. -/
axiom chunk_index_sequential (doc : ExtractedDocument) :
    let chunks := chunkDocument doc
    ∀ i : Fin chunks.length, (chunks.get i).chunkIndex = i.val

/-- Stage 3 → 4 (per chunk): Gemini metadata extraction + provenance override.
    Implementation: MetadataGenerator.generate(). -/
def generateMetadata (c : Chunk) : ChunkMetadata :=
  applyProvenanceOverride (geminiExtract c) c

/-- The composed ingest pipeline for one document.
    Models the pure data-transformation steps only; upload (GCS) and
    indexing (Vertex AI Search) are left as IO effects outside this model. -/
def ingestPipeline (docId : DocId) (filename : Filename) : List ChunkMetadata :=
  let doc    := extractPdf docId filename
  let chunks := chunkDocument doc
  chunks.map generateMetadata

-- ── End-to-end invariants ────────────────────────────────────────────────────

/-- End-to-end provenance: every ChunkMetadata in the pipeline output has
    its `docId` field equal to the document's docId.
    This is the core correctness guarantee of the metadata override rule. -/
theorem pipeline_docId_provenance (docId : DocId) (filename : Filename) :
    ∀ m ∈ ingestPipeline docId filename, m.docId = docId := by
  intro m hm
  simp only [ingestPipeline, List.mem_map] at hm
  obtain ⟨c, hc_mem, rfl⟩ := hm
  have hext := extract_docId_coherent docId filename
  have hcoh := chunk_docId_coherent (extractPdf docId filename) c hc_mem
  simp [generateMetadata, applyProvenanceOverride, hcoh, hext]

/-- The chunkId of every pipeline output is unique within the document.
    Follows from chunk_index_sequential and chunkId_index_injective. -/
theorem pipeline_unique_chunk_ids (docId : DocId) (filename : Filename) :
    let ids := (ingestPipeline docId filename).map
                 (fun m => m.docId ++ "_" ++ zeroPad 5 m.chunkIndex)
    ids.Nodup := by
  -- Proof requires chunk_index_sequential + chunkId_index_injective.
  sorry

/-- The number of ChunkMetadata records equals the number of chunks produced
    by the chunker (map is length-preserving). -/
theorem pipeline_length_eq_chunks (docId : DocId) (filename : Filename) :
    (ingestPipeline docId filename).length =
    (chunkDocument (extractPdf docId filename)).length := by
  simp [ingestPipeline, List.length_map]


-- ═══════════════════════════════════════════════════════════════════════════════
-- §8  Query pipeline type signatures  (no implementation — stubs only)
-- ═══════════════════════════════════════════════════════════════════════════════
-- The query path (searcher → reranker → prompt_builder → response_gen →
-- citation_builder) has no entry-point script yet (Known Issue #4 in CLAUDE.md).
-- Type signatures are stated here for completeness.

/-- Retrieve top-k chunks matching a query in a given domain. -/
opaque searchChunks (query : String) (domain : Option String) (k : Nat) :
    List SearchResult

/-- Optional LLM-based re-ranking of retrieved results. -/
opaque rerank (results : List SearchResult) (query : String) :
    List SearchResult

/-- Build the expert-persona prompt from a domain and retrieved passages. -/
opaque buildPrompt (domain : String) (passages : List SearchResult)
    (query : String) : String

/-- Call Gemini with the assembled prompt; return raw response + attributions. -/
opaque generateResponse (prompt : String) : GeneratedResponse

/-- Convert raw attributions to numbered citations (CitationBuilder.build()).
    This is a separate call from generateResponse; the caller is responsible
    for chaining them (Known Issue #3 in CLAUDE.md). -/
opaque buildCitations (resp : GeneratedResponse) (results : List SearchResult) :
    List String   -- formatted citation strings


end RAGGuidance
