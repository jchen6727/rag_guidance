# DISCREPANCIES

Finalized discrepancies from a static review of `config/`, `ingestion/`, and root `./*.md` (2026-07-08). Items marked *(doc updated)* were corrected in the relevant root `./*.md` during this pass; the rest are code/config-level and left for implementation.

> **Reconciliation pass (2026-07-12).** All items previously marked `#DONE` were re-verified against the codebase and **removed from this file** (dead `watcher.py`, `requirements.txt` `catchup_scan`, the biomedical→schema `metadata_gen`/`models.py` migration, and array-field filterable registration — all confirmed complete). Open items and design notes are retained below. A newly discovered, higher-severity contradiction — `schema_notes.md` instructs array indexing flags at the property level, which is **inverted** relative to Google's live docs and would silently break the RTA array filters — is documented in `architecture_bootstrap.md` §0 and `metadata_summary.md` §1, and is resolved in code by `scripts/setup_vertex_search.py::_create_discoveryengine_schema()` (which also collapses nullable union types). See those files and `CHANGELOG.md` (2026-07-12).

## Implementation status vs docs
- `CLAUDE.md` and `BOOTSTRAP.md` claimed the entire source tree is stub-only; in fact all of `ingestion/*.py`, `models.py`, `config/settings.py`, `scripts/*.py`, and most of `tests/` are implemented. Only `generation/`, `retrieval/`, and `rta_prompt/` remain `NotImplementedError` stubs (`ingestion/watcher.py` was deleted, not stubbed). *(doc updated)*

## Metadata schema vs code (schema is authoritative psychotherapy schema; code is old biomedical)

Resolved by introducing `config/schema_loader.py` (`SchemaVocabulary`) — a structured loader that derives the controlled vocabulary (enums, array membership, nullability, defaults) from `config/metadata_schema.json` at runtime, so `ingestion/metadata_gen.py` and `scripts/setup_vertex_search.py` no longer hard-code (and drift from) the schema. See CHANGELOG.md (2026-07-09). The individual biomedical→psychotherapy migration bullets for `metadata_gen.py` (`_VALID_DOMAINS`/`_VALID_DOC_TYPES`/`_VALID_EVIDENCE_LEVELS` removal, `_validate_and_coerce`/`_build_extraction_prompt` rework) and `models.py::ChunkMetadata` were all `#DONE`, re-verified 2026-07-12, and removed from this file.

### Issues encountered during implementation (2026-07-09)

> Array-field filterable registration was `#DONE (2026-07-10)` and is removed. The mechanism (indexing keywords embedded in the `json_schema`, not `FieldConfig`) is documented in `discovery_engine_comparison.md`; it now lives in `_create_discoveryengine_schema()`. **Caveat (2026-07-12):** the *placement* of those keywords for array fields is where `schema_notes.md` and Google's live docs conflict — see `architecture_bootstrap.md` §0.

- **`ChunkMetadata` intentionally relaxes schema `required`.** The schema marks `domain`, `doc_type`, `source_file` (and others) required, but the Pydantic model gives them defaults so `_fallback_extraction()` never hard-fails when Gemini is unavailable. Schema-`required` semantics are therefore enforced by coercion/fallback conventions, not by the model. **By design; documented.**
- **`doc_type` empty-string sentinel is not a valid enum member.** Unknown `doc_type` values coerce to `""` (legacy behavior preserved to avoid DataStore filter-expression errors), but `""` is absent from the schema `doc_type` enum. **Open** — decide whether to add a `front_matter`/`other` sentinel or keep `""`.
- **`domain` coercion default (`other`) differs from the persona fallback (`psychotherapy_general`).** The schema `domain` description names `psychotherapy_general` as the PromptBuilder persona fallback; coercion of an invalid `domain` stores `other`. Both route to the default persona, so behavior is correct, but the two "fallback" values are not the same token. **Minor; documented.**
- **`retrieval/searcher.py::_parse_metadata` (stub) must round-trip the new fields.** When the query path is implemented, it must reconstruct `ChunkMetadata` (incl. the 15 array fields) from the flat `structData` dict. **Deferred — query path still stubbed.**
- **Test fixture updated.** `tests/test_metadata_gen.py` previously built the generator from an empty placeholder schema (`{"properties": {}, "required": []}`); with schema-driven coercion this no longer exercises anything, so the fixture now loads the real `config/metadata_schema.json` and the sample Gemini response uses psychotherapy values (`entities` removed). New coverage added in `tests/test_schema_loader.py`.

## Chunking config
- `ChunkerConfig.skip_doc_types` and `front_matter_indicators` are defined and loaded from `chunk_config.yaml`, but `ContextAwareChunker` never consumes them; `chunk_config.yaml` comment claims "the structural splitter uses these to auto-tag sections" — it does not.
- `CLAUDE.md` Known Issue #1 ("`ChunkerConfig` is not loaded from YAML") is resolved: `ChunkerConfig.from_yaml()` is implemented. *(doc updated)*
- `ingestion/README.md` ChunkerConfig table says `header_patterns` is "3 regexes" (there are 4), omits `embedding_batch_size`/`max_section_pages`/`front_matter_indicators`, and still lists the resolved "from_yaml needed" known issue.

## Prompt config
- `CLAUDE.md` Known Issue #2 (`{n_passages}` undocumented) is resolved: it is in the variable legend and used in both `retrieval_instruction_rta`/`retrieval_instruction_asa`. *(doc updated)*
- `CLAUDE.md` described `prompt_config.yaml` as "expert persona templates for 9 medical/scientific domains"; it is actually psychotherapy personas (`default` + 10 domain personas) with a split RTA/ASA retrieval instruction. *(doc updated)*

## Uploader serialization
- `ingestion/README.md` `_serialize_chunk` sample shows `"content": {"mimeType":"text/plain","uri":""}` plus a `"jsonData"` field; actual `uploader.py` emits `"content": {"mimeType":"text/plain","rawBytes": <base64 text>}` with no `jsonData`/`uri`.

## structure.md (root)
- Overview described generic "technical/clinical/scientific PDFs"; metadata table used biomedical fields incl. removed `entities`/`evidence_level`; prompt architecture showed the old single `retrieval_instruction` and a generic `{domain} specialist` persona; directory layout omitted `rta_prompt/` and listed `watchdog`; retrieval filter example used `domain = "cardiology"`. *(doc updated)*

## Cross-file / minor
- `BOOTSTRAP.md` "Mandatory reading order" said `config/ISSUES.md` has "15 open issues"; it actually has 23 (I-01–I-23), and `metadata_schema.json` notes reference I-16–I-22. *(doc updated)*
- `caveats.md` §2 recommends a human-review queue for the `evidence_level` field, which was removed from the schema (now `practice_recommendation_level`).
- `CHANGELOG.md` (root, 2026-06-08) pipeline diagram and the 2026-06-16 entry still refer to the pre-rename `watcher` node; historical entries left as-is (the previously-actionable leftover `watcher.py` file has since been deleted).
- `README.md` (root) was a single generic tagline with no psychotherapy/RTA/ASA context or status. *(doc updated)*
