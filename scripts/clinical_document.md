# scripts/ — Clinician Guide (External-Facing, pointer)

**Last reconciled:** 2026-07-20.

This directory is **operational infrastructure** — the commands that provision cloud resources, load documents, and (rarely) wipe them. **There are no clinical decisions to make here.**

If you were directed to this file for a clinical review, the item you want is almost certainly in one of these instead:

- **Vocabulary / label decisions** → `config/clinical_document.md`
- **How documents are split and tagged (spot-checks)** → `ingestion/clinical_document.md`

No feedback log is maintained here. Please add clinical feedback in the two documents above.

---

*Rationale (per `ORCHESTRATOR.md §2.3`): to avoid over-exposing internal system details, clinician-facing docs are not maintained for purely operational directories. This pointer exists only so no reviewer is left without a next step.*
