# config/ — Clinician Guide (External-Facing)

**Who this is for:** clinicians reviewing how the guidance system labels and organizes source material. No software background needed.
**What this directory does, in one line:** it holds the *vocabulary* — the fixed list of clinical labels the system attaches to every passage of every document, so it can find the right guidance at the right moment.
**How to give feedback:** add your notes at the **top** of this file, under *Feedback log*. Write freely — a developer will translate it into a precise specification. Flag anything about **therapies (modalities)** or **safety cautions/flags** clearly; those get extra validation.
**Last reconciled:** 2026-07-20.

---

## Feedback log (newest first)

<!-- Add new feedback here. Newest entry on top. Include the date. Nothing below the marker
     has been processed yet by a developer or agent. -->

*(no clinician feedback recorded yet — this section is ready for your notes)*

`<!-- ▲ unprocessed above this line ▲ -->`

---

## 1. What we are asking you to review

The system reads clinical books, treatment manuals, and guidelines, breaks them into small passages, and tags each passage with labels so it can retrieve the right one during or after a session. **The labels are only as good as the clinical judgment behind them.** We need you to confirm the label vocabulary is clinically correct and complete.

Two label groups get **strict validation** because getting them wrong is a patient-safety issue:

- **Therapeutic modalities** — which therapy a passage belongs to (CBT, DBT, IPT, PE, CPT, ACT, MI, etc.).
- **Clinical flags** — safety-relevant labels: whether a passage says to *do*, *avoid*, or *use caution* with a technique; the conditions under which that applies; explicit cautions/contraindications; and ongoing risk-monitoring dimensions (e.g. chronic suicidality, self-harm).

## 2. The open questions we need answered

These are the decisions only clinicians can make. They are the same questions detailed in the schema analysis, restated plainly. Please answer inline in the Feedback log.

- **#TODO — Q2 (highest priority): "Patient states" that change what's safe.** We need the definitive list of patient states that should change what the system recommends, *regardless of diagnosis or what just happened in session*. Our starting list: acute suicidality, intoxication, insufficient stabilization, active dissociation, acute psychosis, medical instability, cognitive impairment, active self-harm. **Is this list right? Missing anything? For each, which techniques become off-limits?**
- **#TODO — Q1: When may one therapy's material appear during another's session?** For each pair of therapies, is borrowing from B during an A session (a) appropriate, (b) acceptable but lower priority, or (c) an error to prevent? Concretely: DBT distress-tolerance skills during a CBT-depression session — help or error? ACT defusion during CPT? Should Motivational Interviewing always be available?
- **#TODO — Q3: Dissociation without a dissociation "library."** The system can *detect* dissociation mid-session, but we removed dissociative-disorders as a treatment category. When dissociation happens, what should it surface, and from which body of content?
- **#TODO — Q4: Do we need severity levels?** Right now "crisis escalation" is a single label. Do we need to distinguish "patient is escalating" from "patient is in acute crisis" — and would your response actually differ?
- **#TODO — Q7: What does the system reliably know at the start of a session?** Working diagnosis? Therapy type? Session number in the protocol? Active risk flags? This determines which labels are useful.
- **#TODO — Q6/Q9: Precedence and caution breadth.** When a treatment manual and a textbook disagree, which wins? And if a caution is documented for one trauma therapy, should it also surface during a related one?

## 3. What "validated" means for the high-stakes labels

- Every therapy and flag value you approve becomes a **fixed, closed list** — the system may only use those exact terms. This prevents silent drift where the same idea gets tagged three different ways and guidance quietly goes missing.
- A **caution/contraindication is never allowed to be dropped** for being "less relevant." If it applies, it surfaces.
- A caution must always say **what it applies to** ("avoid exposure work *when acutely suicidal*"), never a bare "avoid." A caution with no conditions is treated as an error and held back for review.

## 4. How your feedback becomes system behavior

Your narrative note → a developer writes a precise, testable spec (a "Minimum Implementable Unit") → an automated developer implements it → this document is updated to show what changed and what still needs your input. You never need to write anything technical. You will see your open items move from **#TODO** to **#DONE** here with a short plain-language note.

## 5. Points for review (kept current by the developer/agent)

- **#TODO** Confirm the modality list is complete for CBT/DBT/IPT-trained clinicians (current: CBT, CPT, BA, PE, ERP, ACT, MBCT, UP, Schema, DBT, IPT, MI).
- **#TODO** Confirm the clinical-presentation list (depression, anxiety types, OCD, trauma, interpersonal, substance use, suicidality, insomnia, grief).
- **#TODO** Approve the "patient states" list (Q2 above) — this is the single most blocking item.
- **#NOTE** Motivational Interviewing is currently treated as always-available across therapies; please confirm that matches practice.

---

## Staleness note (how this doc stays honest)

If anything here no longer matches how the system behaves, it will be marked `#STALE` and corrected against the authoritative schema. This document was last checked against the current schema on the date at the top. If you notice something that contradicts your clinical understanding, that itself is useful feedback — please flag it.
