"""
Filesystem watcher for the corpus/ directory.

Monitors for new PDFs using watchdog and triggers the full ingestion pipeline.
Tracks processed files in a JSON manifest to survive restarts without re-ingesting.
On startup, performs a catch-up scan to handle files added while the watcher was down.

Production note: for cloud deployments replace this with a GCS Eventarc trigger
(Cloud Functions) — this local watcher is not fault-tolerant across host restarts.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Callable

from watchdog.events import FileCreatedEvent, FileModifiedEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class PDFEventHandler(FileSystemEventHandler):
    """Watchdog handler that filters for PDF files and invokes an ingestion callback."""

    def __init__(self, on_pdf: Callable[[Path], None]) -> None:
        """
        Args:
            on_pdf: Callback called with the absolute PDF path when a new file lands.
                    This is called on the watchdog observer thread — keep it fast or
                    hand off to a queue.
        """
        super().__init__()
        self._on_pdf = on_pdf

    def on_created(self, event: FileCreatedEvent) -> None:
        """Triggered when a file is created inside the watched directory tree.

        Ignores directories and non-PDF files.

        Args:
            event: Watchdog FileCreatedEvent with .src_path set to the new file.
        """
        raise NotImplementedError

    def on_modified(self, event: FileModifiedEvent) -> None:
        """Triggered when a file is modified inside the watched directory tree.

        Large PDFs copied via OS utilities fire multiple modification events.
        Debounce logic (e.g., check file size stability) should live here before
        forwarding to on_pdf.

        Args:
            event: Watchdog FileModifiedEvent.
        """
        raise NotImplementedError

    def _is_pdf(self, path: str) -> bool:
        """Return True if path ends with .pdf (case-insensitive).

        Args:
            path: Raw filesystem path string from the watchdog event.

        Returns:
            True if the file extension is .pdf.
        """
        raise NotImplementedError


class CorpusWatcher:
    """
    Orchestrates directory monitoring and coordinates per-document ingestion.

    Lifecycle:
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

        Call stop() from a signal handler or separate thread to exit cleanly.
        """
        raise NotImplementedError

    def stop(self) -> None:
        """Stop the watchdog observer and flush the manifest to disk."""
        raise NotImplementedError

    def catchup_scan(self) -> None:
        """Process any PDFs in corpus_dir not yet recorded in the manifest.

        Runs synchronously before the live observer starts. Each file is processed
        in alphabetical order so the manifest state is deterministic.
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
