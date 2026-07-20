# ingestion/ — Clinician Guide (External-Facing)

**Who this is for:** clinicians. No software background needed.
**What this directory does, in one line:** it takes each PDF (books, manuals, guidelines), splits it into small passages, and attaches the clinical labels defined in `config/` to every passage — so the right guidance can be found later.
**Your role here:** spot-check that passages are split sensibly and labeled correctly. The *vocabulary* decisions live in `config/clinical_document.md`; this doc is about whether the tagging is being *applied* well.
**Last reconciled:** 2026-07-20.

---

## Feedback log (newest first)

<!-- Add tagging/quality observations here, newest on top, dated. -->

*(no clinician feedback recorded yet)*

`<!-- ▲ unprocessed above this line ▲ -->`

---

## 1. What happens to a document

1. The text is read out of the PDF (page by page).
2. It is split into short passages, trying to keep each passage about one idea and to break at natural section/chapter boundaries.
3. Each passage is automatically labeled with the clinical vocabulary from `config/` (therapy type, presentation, in-session events, cautions, etc.).
4. Labeled passages are stored so the guidance system can retrieve them.

## 2. Where clinical judgment matters in this step

- **Cautions must survive.** If a passage says a technique is contraindicated or needs a precondition, that caution must be captured and kept attached — never summarized away. This is a patient-safety requirement.
- **Front matter should be dropped.** Title pages, tables of contents, and indexes carry no clinical guidance and should not pollute results. *(Note: this filtering is only partly wired today — see the developer notes; a clinician spot-check helps catch junk passages.)*
- **Right therapy, right passage.** A passage about DBT skills should be labeled DBT, even if it appears inside a general CBT textbook. Mislabeling here quietly sends the wrong guidance.

## 3. What we may ask you to spot-check

Once the first documents are processed, we may show you a small sample of passages with their labels and ask:

- **#TODO** Is this passage split at a sensible boundary (not mid-thought)?
- **#TODO** Are the therapy and presentation labels correct?
- **#TODO** Was any stated caution/contraindication captured?
- **#TODO** Is this passage actually clinical content, or is it front matter that slipped through?

You don't need to review everything — a small sample per source is enough to catch systematic problems early. Tagging errors are usually invisible in totals and only show up as bad retrieval weeks later, so early spot-checks are valuable.

## 4. Points for review (kept current by the developer/agent)

- **#NOTE** No documents have been processed yet; there is nothing to spot-check today.
- **#TODO** After the first processing run, a sample of passages + labels will be prepared here for your review.

---

## Staleness note

If a described behavior no longer matches what the system does, it will be marked `#STALE` and corrected. Last checked on the date above. If a labeling pattern looks clinically wrong to you, flag it in the Feedback log — that is exactly the signal we need.
