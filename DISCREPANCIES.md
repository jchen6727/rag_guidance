# DISCREPANCIES

Finalized discrepancies from a static review of `config/`, `ingestion/`, and root `./*.md` (2026-07-08). Items marked *(doc updated)* were corrected in the relevant root `./*.md` during this pass; the rest are code/config-level and left for implementation.

## Implementation status vs docs
- `CLAUDE.md` and `BOOTSTRAP.md` claimed the entire source tree is stub-only; in fact all of `ingestion/*.py` (except `watcher.py`), `models.py`, `config/settings.py`, `scripts/*.py`, and most of `tests/` are implemented. Only `generation/`, `retrieval/`, `rta_prompt/`, and `ingestion/watcher.py` remain `NotImplementedError` stubs. *(doc updated)*

## Dead / duplicate file
- `ingestion/watcher.py` still exists as a `NotImplementedError` stub duplicating `CorpusScanner`, but `CHANGELOG.md` (2026-06-16) states it was "renamed to `scanner.py`" and `ingestion/__init__.py` imports only from `scanner`. `watcher.py` is dead and should be deleted. #DONE
- `ingestion/requirements.txt` (line 9) references `CorpusWatcher.catchup_scan()` — a class/method that no longer exists (now `CorpusScanner.scan()`). #DONE

## Metadata schema vs code (schema is authoritative psychotherapy schema; code is old biomedical)

Resolved by introducing `config/schema_loader.py` (`SchemaVocabulary`) — a structured loader that derives the controlled vocabulary (enums, array membership, nullability, defaults) from `config/metadata_schema.json` at runtime, so `ingestion/metadata_gen.py` and `scripts/setup_vertex_search.py` no longer hard-code (and drift from) the schema. See CHANGELOG.md (2026-07-09).

- `ingestion/metadata_gen.py` `_VALID_DOMAINS` is biomedical (`cardiology`, `oncology`, …); schema `domain` enum is psychotherapy (`cognitive_behavioral`, `dialectical_behavior`, …). #DONE — constant removed; domain validity now read from `SchemaVocabulary.enum_values("domain")`.
- `ingestion/metadata_gen.py` `_VALID_DOC_TYPES` lists 6 old biomedical types; schema `doc_type` enum has 16 psychotherapy types (`treatment_manual`, `session_transcript`, …). #DONE — constant removed; schema-derived.
- `ingestion/metadata_gen.py` `_VALID_EVIDENCE_LEVELS` (A/B/C/D) targets the removed `evidence_level` field; schema replaced it with `practice_recommendation_level`. #DONE — constant removed; `practice_recommendation_level` coerced from the schema enum.
- `_validate_and_coerce()` coerces the removed `entities` field and `evidence_level`, and does not handle any new required/array fields (`corpus_scope`, `therapeutic_modality`, `clinical_presentation`, `session_event_tags`, `analysis_function`, `patient_population`, `risk_dimension_tags`, `outcome_measure_tags`, etc.). #DONE — now delegates to `SchemaVocabulary.coerce()`, which handles every schema field generically (enum membership, array normalization, integer parsing) and drops keys absent from the schema (`entities`, `evidence_level`).
- `_build_extraction_prompt()` dumps raw schema `properties` generically — no inline enum lists, no RTA/ASA-specific field elicitation the schema notes call for. #DONE — prompt now includes a schema-derived enum legend plus extraction guidance drawn from schema `notes` (domain-vs-modality, missingness inference, patient-facing exclusion).
- `models.py::ChunkMetadata` is still the old biomedical model (`domain` "cardiology/oncology", `doc_type` "textbook|clinical_guideline|research_paper|front_matter", plus `entities`, `evidence_level`) and is missing ~24 new schema fields; `metadata_schema.json` `notes.removed_fields` explicitly instructs updating both the model and `metadata_gen.py`. #DONE — `ChunkMetadata` rewritten to mirror all 37 schema fields with schema-aligned defaults; `entities` and `evidence_level` removed.

### Issues encountered during implementation (2026-07-09)
- **Array fields not registered as filterable.** `#DONE (2026-07-10)` — `register_schema()` now calls `_annotate_schema_for_indexing()`, which injects Vertex AI Search indexing keywords (`retrievable`/`indexable`/`searchable`) into the `json_schema` document, with array fields annotated on their `items` leaf. All 16 array metadata fields are now `indexable` (filterable); `missingness` stays retrievable-only per `notes.vertex_ai_search`. The old `continue`-past-array-fields loop and the dead `discoveryengine.FieldConfig(...)` block are gone.

  Why the fix is *not* `discoveryengine.FieldConfig` / a v1alpha move (investigated 2026-07-10): field-level indexing must be expressed as annotations *inside* the `json_schema` string, **not** via a `FieldConfig` object. `FieldConfig` and `Schema.field_configs` are absent from `discoveryengine_v1`/`discoveryengine_v1beta` entirely; they *do* exist in `discoveryengine_v1alpha`, but there `Schema.field_configs` is `OUTPUT_ONLY` (a read-back of server-derived config, not a write input), and `FieldConfig(filterable=…)` isn't even a valid constructor (the field is `indexable_option`, and `filterable`/`recs_filterable_option` is a Recommendations knob, not a Search one). So v1alpha would not have worked. Because ingestion is a single pre-import batch (schema registered once; metadata changes require `purge_datastore.py --confirm` + full re-ingest), the GA `json_schema` annotation path expresses the entire filterable/retrievable/searchable config in the one up-front step this architecture needs — nothing in v1alpha would add capability here. See CHANGELOG 2026-07-10 and `discovery_engine_comparison.md`.
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
- `CHANGELOG.md` (root, 2026-06-08) pipeline diagram and the 2026-06-16 entry still refer to the pre-rename `watcher` node; historical entries left as-is (the actionable issue is the leftover `watcher.py` file above).
- `README.md` (root) was a single generic tagline with no psychotherapy/RTA/ASA context or status. *(doc updated)*
