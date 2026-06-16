"""
Corpus scanning and optional filesystem watching for the corpus/ directory.

Primary usage — one-time scan (no daemon):
    watcher = CorpusWatcher(corpus_dir, manifest_path, pipeline_fn)
    watcher.catchup_scan()   # single pass over corpus/; returns when done

This is the intended deployment pattern: run as a batch job, CI step, or
cron-scheduled container. No background threads, no signal handling, no watchdog
Observer required. ``scripts/batch_ingest.py`` uses this path.

Optional — continuous observer (local development only):
    watcher = CorpusWatcher(corpus_dir, manifest_path, pipeline_fn)
    watcher.start()   # blocks; call stop() from a signal handler to exit

Tracks processed files in a JSON manifest (basename → doc_id) so re-runs
process only new files. The manifest is written atomically on every update.

Production note: for deployments requiring sub-minute ingestion latency,
replace the scheduled scan with a GCS Eventarc trigger (Cloud Functions).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

class CorpusWatcher:
    """
    Orchestrates corpus scanning and coordinates per-document ingestion.

    Primary lifecycle (one-time scan):
        watcher = CorpusWatcher(corpus_dir, manifest_path, pipeline_fn)
        watcher.catchup_scan()   # processes all unprocessed PDFs, then returns

    Observer lifecycle (optional, for continuous local monitoring):
        watcher = CorpusWatcher(corpus_dir, manifest_path, pipeline_fn)
        watcher.start()   # blocks; call stop() from another thread to exit
    """

    def __init__(
        self,
        corpus_dir: Path,
        manifest_path: Path,
        pipeline_callback: Callable[[Path], None],
    ) -> None:
        """
        Args:
            corpus_dir: Directory to watch. Must exist before calling start().
            manifest_path: Path to the JSON manifest (created if absent).
            pipeline_callback: Called with the PDF path to run the full ingestion
                               pipeline (extract → chunk → metadata → upload → index).
        """
        self._corpus_dir = corpus_dir
        self._manifest_path = manifest_path
        self._pipeline_callback = pipeline_callback
        self._observer: Observer | None = None
        self._manifest: dict[str, str] = {}  # basename -> doc_id

    def start(self) -> None:
        """Load the manifest, run catch-up scan, start the observer, then block.

        Observer-based path for continuous local monitoring. Prefer catchup_scan()
        for batch jobs, CI, and scheduled runs. Call stop() from a signal handler
        or separate thread to exit cleanly.
        """
        raise NotImplementedError

    def stop(self) -> None:
        """Stop the watchdog observer and flush the manifest to disk."""
        raise NotImplementedError

    def catchup_scan(self) -> None:
        """Process any PDFs in corpus_dir not yet recorded in the manifest.

        Primary ingestion entry point. Scans corpus_dir once, runs the pipeline
        for each unprocessed file in alphabetical order, and returns. Manifest is
        updated after each successful file so partial runs are resumable.
        """
        raise NotImplementedError

    def process_pdf(self, path: Path) -> None:
        """Guard-check then invoke the ingestion pipeline for one PDF.

        Skips the file if already in the manifest. Marks it processed after the
        pipeline_callback returns without raising.

        Args:
            path: Absolute path to the PDF.
        """
        raise NotImplementedError

    def is_processed(self, path: Path) -> bool:
        """Return True if this file's basename exists in the in-memory manifest.

        Args:
            path: Path to the PDF file.

        Returns:
            True if already ingested.
        """
        raise NotImplementedError

    def mark_processed(self, path: Path, doc_id: str) -> None:
        """Record a file in the manifest and persist to disk.

        Args:
            path: Path to the PDF file.
            doc_id: Content-hash ID assigned by GCSUploader.compute_doc_id().
        """
        raise NotImplementedError

    def _load_manifest(self) -> None:
        """Read manifest JSON into self._manifest; create empty if missing."""
        raise NotImplementedError

    def _save_manifest(self) -> None:
        """Write self._manifest to disk atomically (temp file + rename)."""
        raise NotImplementedError
