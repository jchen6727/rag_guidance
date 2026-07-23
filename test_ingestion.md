# test_ingestion.md — Ingest a PDF and Review Its Chunks & Tags

**Who this is for:** anyone comfortable typing commands into a terminal. No coding needed — every step is copy-paste.
**What you'll do:** take a PDF, see how it gets split into "chunks" and labeled with clinical "tags", then (optionally) load it into the cloud search index and review what landed there.
**Example file used throughout:** `corpus/APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf`

> **The safest way to start** is **Level 1** below — it runs entirely on your own computer, costs nothing, and touches no cloud account. Do that first. Only move to Levels 2–3 when you're ready.

---

## The three levels (pick where to start)

| Level | What it does | What you need | Cost |
|---|---|---|---|
| **1. Preview chunks (offline)** | Splits the PDF into chunks and writes a report. **No tags.** | Just this project installed | Free |
| **2. Preview chunks + tags** | Same, plus the AI clinical labels on each chunk | A Gemini API key | ~cents |
| **3. Full ingest + cloud review** | Loads chunks into the cloud search index; review them there | A Google Cloud project | cloud usage |

You can stop after any level. Level 1 already answers "are the chunks sensible?"; Level 2 adds "are the tags right?"; Level 3 is the real thing.

---

## One-time setup

Open a terminal in the project folder (the one containing this file), then:

```bash
# 1. Install the Python dependencies (only needed once).
pip install -r requirements.txt
pip install torch --index-url https://download.pytorch.org/whl/cpu   # CPU-only, avoids a big download

# 2. Create your settings file from the template (only needed once).
cp .env.example .env
```

You now have a `.env` file. You'll fill parts of it in as you go (Levels 2 and 3 tell you which lines). For **Level 1 you don't need to edit `.env` at all.**

> **Tip:** every command below starts with `PYTHONPATH=.` — that just tells Python where the project is. Always include it. If a command seems stuck the first time, it may be downloading a small language model (~80 MB) used for splitting — that's normal and only happens once.

---

## Level 1 — Preview a PDF's chunks (offline, free)

This reads the PDF, splits it into chunks, and writes a report you can open. It does **not** use the internet or any account.

```bash
PYTHONPATH=. python scripts/inspect_chunks.py corpus/APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf --no-metadata
```

**What success looks like:** it prints a summary like:

```
Inspected 1 PDF(s). Review files in: ingestion_review/
  APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf
    doc_id : ef0c4d1d912afbc7...
    pages  : 216   chunks: 921   (no tags)
    open   : ingestion_review/APA_Boswell_Constantino_Deliberate_Practice_CBT.ef0c4d1d.review.md
```

**Now open the report.** On macOS:

```bash
open ingestion_review/APA_Boswell_Constantino_Deliberate_Practice_CBT.ef0c4d1d.review.md
```

(or just open the `ingestion_review/` folder and double-click the `.review.md` file.)

Each chunk appears as a card showing its page range, the section heading above it, and a preview of the text. **What to check:** are the chunks split at sensible places (not mid-thought)? You'll notice the first few chunks are front matter (title page, copyright) — that's expected; see the note at the end about front matter.

There is also a `.chunks.jsonl` file next to the report — that's the same data in a format for computers; you can ignore it.

---

## Level 2 — Add the clinical tags

Same preview, but now each chunk is also labeled by the AI (therapy type, clinical presentation, cautions, etc.). This calls Google's Gemini model, so it needs a key.

**Get a key once** (free tier available): go to **https://aistudio.google.com/apikey**, create an API key, and paste it into your `.env` file on this line:

<NOTE: deprecating aistudio? gemini? prefer routing through vertex?>
# =====================================================================
# TODO: MIGRATION REQUIRED (Assigned to Claude)
# =====================================================================
# DEBT: This script currently uses the old, developer-facing Google AI 
# Studio API backend (://googleapis.com) for a quick, 
# immediate deployment via an API Key.
#
# NEXT STEPS FOR CLAUDE:
# 1. Migrate the code base from the deprecated `google-generativeai` 
#    library to the modern unified `google-genai` SDK.
# 2. Add `vertexai=True` to the client initialization parameters.
# 3. Swap the `GEMINI_API_KEY` authentication for Google Cloud IAM / 
#    Application Default Credentials (ADC) service account access.
# 4. Update deployment infrastructure to target Vertex AI 
#    (://googleapis.com) inside the enterprise VPC.
# =====================================================================
<END>
```
GEMINI_API_KEY=paste-your-key-here
```

Then run the preview **without** `--no-metadata`. To keep the first test cheap and quick, tag only the first 15 chunks with `--limit`:

```bash
PYTHONPATH=. python scripts/inspect_chunks.py corpus/APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf --limit 15
```

Open the new `.review.md`. Now each chunk card shows its **tags**, and near the top there's a **"Tag frequencies"** summary (how often each label appears across all chunks).

**What to check:**
- Are the **therapy** and **presentation** tags right for each passage?
- Under **safety flags**, was any stated **caution / contraindication** captured?
- If you see `used fallback` in the summary, some chunks failed to tag — scroll up in the terminal for a plain-English explanation (usually a key or quota problem), or re-run with `--verbose`.

When you're happy, drop `--limit` to tag the whole document (this costs more and takes longer):

```bash
PYTHONPATH=. python scripts/inspect_chunks.py corpus/APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf
```

> A clinician reviewing tag quality should read the `.review.md` file. They don't need the terminal.

---

## Level 3 — Full ingest into the cloud, then review it there

This uploads the PDF and its chunks to Google Cloud and loads them into the Vertex AI Search index. You need a **Google Cloud project** with billing enabled.

### 3a. Log in and fill in `.env`

```bash
# Log in (opens a browser). Do both:
gcloud auth login
gcloud auth application-default login
```

Edit `.env` and fill in these lines with your project's values (ask whoever set up the cloud project if unsure):

```
GCP_PROJECT_ID=your-project-id
GCS_BUCKET_NAME=your-bucket-name
GCP_LOCATION=us
VERTEX_SEARCH_DATASTORE_ID=your-datastore-id
VERTEX_SEARCH_ENGINE_ID=your-engine-id
```

<NOTE: either add some handling (preferred) or ensure this stays in documentation >
Load the `.env` from the terminal:

```
set -a
source .env  # or: export $(grep -v '^#' .env | xargs)
set +a
```
<END>

### 3b. Check everything is ready

```bash
scripts/preflight_check.sh
```

<NOTE: preflight_check.sh does not handle gemini (or generative ai) check>
additionally, should be migrated to vertex instead of generative ai as google-generativeai is deprecated for google-genai
<END>

This checks your login, project, billing, required APIs, and permissions, and **prints the exact command to fix anything that's missing.** Fix any red items before continuing.

### 3c. Create the search index (once per project)

```bash
PYTHONPATH=. python scripts/setup_vertex_search.py --dry-run    # preview — no changes
PYTHONPATH=. python scripts/setup_vertex_search.py              # actually create it
```

> **Important order:** this step registers the tag "schema" and **must run before** the first ingest, or tags get silently dropped.

### 3d. Ingest the single PDF

Always do a dry run first (it splits and tags but uploads nothing):

```bash
PYTHONPATH=. python scripts/batch_ingest.py --file corpus/APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf --dry-run
```

If that looks healthy, do the real ingest:

<NOTE: check that the --dry-run (if it generates tags) preserves them so we do not need additional API calls (cost) from --dry-run to actual run>
<END>


```bash
PYTHONPATH=. python scripts/batch_ingest.py --file corpus/APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf
```

**What success looks like:** a summary table ending with `import : N ok / 0 failed`. If you see failures, the log above the table explains each one in plain English. Add `--verbose` to any command to see the full detail.

### 3e. Review what actually got indexed

**Option A — from the terminal:**

```bash
# Show the first 20 indexed chunks with their tags:
PYTHONPATH=. python scripts/review_datastore.py

# Only the chunks from this PDF (use the doc_id shown during ingest — first 8 chars are enough):
PYTHONPATH=. python scripts/review_datastore.py --doc-id ef0c4d1d

# Save a report file and show more:
PYTHONPATH=. python scripts/review_datastore.py --limit 100 --out indexed_review.md
```

**Option B — in the web console (cloud.google.com):** go to **AI Applications** (formerly Agent Builder) → **Data Stores** → your data store → the **Documents** tab. Each row is a chunk; click one to see its stored fields (the tags) and content.

Both show the same thing: the chunks and their tags, straight from the index.

---

## Ingesting more than one PDF

- **Preview several at once:**
  ```bash
  PYTHONPATH=. python scripts/inspect_chunks.py corpus/fileA.pdf corpus/fileB.pdf --limit 15
  # or every PDF in the corpus folder:
  PYTHONPATH=. python scripts/inspect_chunks.py --all --no-metadata
  ```
- **Ingest every new PDF** in `corpus/` (skips ones already done):
  ```bash
  PYTHONPATH=. python scripts/batch_ingest.py --dry-run     # preview all
  PYTHONPATH=. python scripts/batch_ingest.py               # ingest all new
  ```
  A file is remembered in `.ingestion_manifest.json` once ingested, so re-running only picks up new files.

---

## Redoing or cleaning up

- **Re-ingest a file you already did** (e.g. after fixing something): add `--force`:
  ```bash
  PYTHONPATH=. python scripts/batch_ingest.py --file corpus/APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf --force
  ```
- **Empty the whole index** (careful — this deletes indexed chunks; requires `--confirm`):
  ```bash
  PYTHONPATH=. python scripts/purge_datastore.py --confirm --dry-run   # preview what would be deleted
  PYTHONPATH=. python scripts/purge_datastore.py --confirm             # actually delete
  ```
- The local preview files in `ingestion_review/` are just reports — delete the folder anytime.

---

## Troubleshooting (common messages → what to do)

The scripts translate Google's errors into plain English with a `→` suggestion. The most common ones:

| You see… | It means | Do this |
|---|---|---|
| `No Google credentials were found` | Not logged in | `gcloud auth application-default login` |
| `lacks an IAM permission` | Logged in, but missing access | Run `scripts/preflight_check.sh` — it prints the fix |
| `The resource does not exist` (DataStore) | Index not created, or wrong region/ID | Run `scripts/setup_vertex_search.py`; check `GCP_LOCATION` and `VERTEX_SEARCH_DATASTORE_ID` in `.env` |
| `quota or rate limit` | Too many calls too fast | Wait a minute; use `--limit`; or request a quota increase |
| `required Google API is not enabled` / `billing` | API off or billing disabled | Run `scripts/preflight_check.sh` |
| `Gemini could not authenticate` | Missing/blank `GEMINI_API_KEY` | Add your key to `.env` (see Level 2) |
| Lots of `used fallback` chunks | Tagging kept failing | Scroll up for the real reason; re-run with `--verbose` |

**`--verbose` is your friend.** Add it to any script to see exactly what was sent to Google and what came back:

```bash
PYTHONPATH=. python scripts/batch_ingest.py --file corpus/APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf --dry-run --verbose
```

---

## A note on "front matter"

The example book's first chunks are its title page, copyright page, and table of contents. Right now these are **not** automatically filtered out, so they'll appear in previews and (if you ingest) in the index. That's a known limitation being tracked by the developers (`ingestion/dev_document.md`, tag `#TODO(front-matter)`). For a test run it's harmless — just be aware the earliest few chunks per book aren't real clinical content.

---

## Command cheat-sheet

```bash
# Level 1 — preview chunks, offline, free
PYTHONPATH=. python scripts/inspect_chunks.py corpus/APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf --no-metadata

# Level 2 — preview chunks + tags (needs GEMINI_API_KEY in .env)
PYTHONPATH=. python scripts/inspect_chunks.py corpus/APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf --limit 15

# Level 3 — full cloud ingest + review
scripts/preflight_check.sh
PYTHONPATH=. python scripts/setup_vertex_search.py
PYTHONPATH=. python scripts/batch_ingest.py --file corpus/APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf --dry-run
PYTHONPATH=. python scripts/batch_ingest.py --file corpus/APA_Boswell_Constantino_Deliberate_Practice_CBT.pdf
PYTHONPATH=. python scripts/review_datastore.py --doc-id ef0c4d1d

# Add --verbose to any command to debug. Add --help to see all options.
```
