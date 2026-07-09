# DISCREPANCIES

Finalized discrepancies from a static review of `config/`, `ingestion/`, and root `./*.md` (2026-07-08). Items marked *(doc updated)* were corrected in the relevant root `./*.md` during this pass; the rest are code/config-level and left for implementation.

## Implementation status vs docs
- `CLAUDE.md` and `BOOTSTRAP.md` claimed the entire source tree is stub-only; in fact all of `ingestion/*.py` (except `watcher.py`), `models.py`, `config/settings.py`, `scripts/*.py`, and most of `tests/` are implemented. Only `generation/`, `retrieval/`, `rta_prompt/`, and `ingestion/watcher.py` remain `NotImplementedError` stubs. *(doc updated)*

## Dead / duplicate file
- `ingestion/watcher.py` still exists as a `NotImplementedError` stub duplicating `CorpusScanner`, but `CHANGELOG.md` (2026-06-16) states it was "renamed to `scanner.py`" and `ingestion/__init__.py` imports only from `scanner`. `watcher.py` is dead and should be deleted.
- `ingestion/requirements.txt` (line 9) references `CorpusWatcher.catchup_scan()` — a class/method that no longer exists (now `CorpusScanner.scan()`).

## Metadata schema vs code (schema is authoritative psychotherapy schema; code is old biomedical)
- `ingestion/metadata_gen.py` `_VALID_DOMAINS` is biomedical (`cardiology`, `oncology`, …); schema `domain` enum is psychotherapy (`cognitive_behavioral`, `dialectical_behavior`, …).
- `ingestion/metadata_gen.py` `_VALID_DOC_TYPES` lists 6 old biomedical types; schema `doc_type` enum has 16 psychotherapy types (`treatment_manual`, `session_transcript`, …).
- `ingestion/metadata_gen.py` `_VALID_EVIDENCE_LEVELS` (A/B/C/D) targets the removed `evidence_level` field; schema replaced it with `practice_recommendation_level`.
- `_validate_and_coerce()` coerces the removed `entities` field and `evidence_level`, and does not handle any new required/array fields (`corpus_scope`, `therapeutic_modality`, `clinical_presentation`, `session_event_tags`, `analysis_function`, `patient_population`, `risk_dimension_tags`, `outcome_measure_tags`, etc.).
- `_build_extraction_prompt()` dumps raw schema `properties` generically — no inline enum lists, no RTA/ASA-specific field elicitation the schema notes call for.
- `models.py::ChunkMetadata` is still the old biomedical model (`domain` "cardiology/oncology", `doc_type` "textbook|clinical_guideline|research_paper|front_matter", plus `entities`, `evidence_level`) and is missing ~24 new schema fields; `metadata_schema.json` `notes.removed_fields` explicitly instructs updating both the model and `metadata_gen.py`.

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
