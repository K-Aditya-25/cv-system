from __future__ import annotations

import subprocess, sys, threading
from pathlib import Path

from .cv_output import compile_pdf, pdf_path_for_tex
from .errors import IntakeError

class TexCompileWatcher:
    def __init__(self, poll_seconds: float = 1.0) -> None:
        self.poll_seconds = poll_seconds
        self._path: Path | None = None
        self._last_mtime_ns: int | None = None
        self._paused = False
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=2)

    def set_path(self, path: Path | None) -> None:
        with self._lock:
            self._path = path
            self._last_mtime_ns = self._read_mtime_ns(path)

    def pause(self) -> None:
        with self._lock:
            self._paused = True

    def resume(self) -> None:
        with self._lock:
            self._paused = False

    def _snapshot(self) -> tuple[Path | None, int | None, bool]:
        with self._lock:
            return self._path, self._last_mtime_ns, self._paused

    def _set_last_mtime(self, mtime_ns: int | None) -> None:
        with self._lock:
            self._last_mtime_ns = mtime_ns

    def _read_mtime_ns(self, path: Path | None) -> int | None:
        if path is None:
            return None
        try:
            return path.stat().st_mtime_ns
        except FileNotFoundError:
            return None

    def _run(self) -> None:
        while not self._stop_event.wait(self.poll_seconds):
            path, last_mtime_ns, paused = self._snapshot()
            if paused or path is None:
                continue
            current_mtime_ns = self._read_mtime_ns(path)
            if current_mtime_ns is None or current_mtime_ns == last_mtime_ns:
                continue

            self._set_last_mtime(current_mtime_ns)
            print(f"\nDetected manual TeX edit; compiling PDF: {path}", flush=True)
            try:
                compile_pdf(path)
            except subprocess.CalledProcessError as exc:
                print(f"Manual TeX compile failed: {exc}", file=sys.stderr, flush=True)
            except IntakeError as exc:
                print(f"Manual TeX compile failed: {exc}", file=sys.stderr, flush=True)
            else:
                print(f"Manual TeX compile complete: {pdf_path_for_tex(path)}", flush=True)

