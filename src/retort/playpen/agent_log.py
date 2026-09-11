"""Agent transcript access: bounded, gzip-aware, streaming.

``_agent_stdout.log`` is the agent's raw event stream and can be enormous —
one prime-agent brazil run wrote 193 MB (exp-mu-primeagent, 2026-09-02). Three
readers used to ``read_text()`` the whole file into a Python ``str``; one of
them sat on the hot path of every sandbox cell. Every reader here either
streams or bounds, and every one accepts the archive's gzipped form
(``_agent_stdout.log.gz``, the data-branch convention for logs over 1 MB), so
a fresh clone no longer needs ``gunzip -k`` before rescoring.

``compact_prime_log`` is the write-time fix for the volume itself: see its
docstring for the measurement that makes it safe.
"""

from __future__ import annotations

import gzip
import json
import os
import re
import zlib
from collections.abc import Iterator
from pathlib import Path
from typing import IO

AGENT_STDOUT = "_agent_stdout.log"
AGENT_STDERR = "_agent_stderr.log"

#: What a missing, unreadable, or half-written transcript raises. A ``.gz``
#: cut off mid-stream (an archive interrupted while copying, or a run killed
#: while its log was being compressed) raises ``EOFError`` — NOT an OSError —
#: and corrupt deflate data raises ``zlib.error``. Every reader treats all
#: three the same way: what could be read is returned, the rest is absent.
#: ``retort diagnose`` / ``rescore`` sweep whole archives and must not abort on
#: the first bad file.
READ_ERRORS: tuple[type[BaseException], ...] = (OSError, EOFError, zlib.error)

#: Bytes of transcript tail that live-context / diagnose readers look at.
DEFAULT_TAIL_BYTES = 400_000


def find_agent_log(run_dir: Path, name: str = AGENT_STDOUT) -> Path | None:
    """The transcript in ``run_dir`` — plain first, then ``.gz`` — or None."""
    for candidate in (run_dir / name, run_dir / f"{name}.gz"):
        if candidate.is_file():
            return candidate
    return None


def _open(path: Path) -> IO[bytes] | gzip.GzipFile:
    if path.suffix == ".gz":
        return gzip.open(path, "rb")
    return open(path, "rb")


def iter_lines(path: Path) -> Iterator[str]:
    """Yield decoded lines without holding the file in memory.

    Stops (rather than raising) at a truncated or corrupt ``.gz``: the lines
    before the damage are yielded, and a missing file yields nothing.
    """
    try:
        with _open(path) as fh:
            for raw in fh:
                yield raw.decode("utf-8", "replace")
    except READ_ERRORS:
        return


def read_text(path: Path) -> str:
    """The whole transcript, decoded. For parsers that need every event
    (the usage parsers); call ``compact_prime_log`` first where it applies so
    "whole" is tens, not hundreds, of megabytes. A truncated ``.gz`` yields
    the readable prefix."""
    buf = bytearray()
    try:
        with _open(path) as fh:
            # Line iteration, not read(n): GzipFile.read(n) raises EOFError on
            # a truncated member and DROPS the bytes it had already inflated,
            # so a chunked read of a damaged .gz would return nothing at all.
            for raw in fh:
                buf += raw
    except READ_ERRORS:
        pass
    return bytes(buf).decode("utf-8", "replace")


def read_tail(path: Path, max_bytes: int = DEFAULT_TAIL_BYTES) -> str:
    """The last ``max_bytes`` of the transcript, decoded.

    A plain file is seeked; a gzip member cannot be, so it is streamed through
    a rolling window that never exceeds ``2 * max_bytes``.
    """
    window = bytearray()
    try:
        if path.suffix != ".gz":
            with open(path, "rb") as fh:
                fh.seek(0, os.SEEK_END)
                fh.seek(max(0, fh.tell() - max_bytes))
                return fh.read().decode("utf-8", "replace")
        with gzip.open(path, "rb") as gz:
            for raw in gz:  # by line: see read_text on why not read(n)
                window += raw
                if len(window) > 2 * max_bytes:
                    del window[:-max_bytes]
    except READ_ERRORS:
        pass  # a truncated .gz: the tail of what was readable
    return bytes(window[-max_bytes:]).decode("utf-8", "replace")


def search(path: Path, pattern: re.Pattern[str]) -> re.Match[str] | None:
    """First match of ``pattern``, tested line by line.

    The callers' patterns (tool refusals, usage-limit signatures) are
    single-line by construction (``[^\\n]`` bounded), so per-line search is
    equivalent to searching the joined text and needs no buffer. A missing or
    truncated file searches what is readable (``iter_lines``) — never raises.
    """
    for line in iter_lines(path):
        match = pattern.search(line)
        if match is not None:
            return match
    return None


def contains_any(path: Path, *needles: str) -> bool:
    """Case-insensitive substring test for any of ``needles``, streaming.
    Same truncation behaviour as ``search``: never raises, tests what is
    readable."""
    lowered = [n.lower() for n in needles if n]
    if not lowered:
        return False
    for line in iter_lines(path):
        low = line.lower()
        if any(n in low for n in lowered):
            return True
    return False


_MESSAGE_UPDATE_HINT = b'"message_update"'


def compact_prime_log(path: Path | str) -> tuple[int, int]:
    """Drop ``message_update`` events from a prime-agent ``--mode json``
    transcript, in place. Returns ``(bytes_before, bytes_after)``.

    Each ``message_update`` is a full snapshot of the accumulating assistant
    message, re-emitted as it grows — 31,515 of them made up 172 MB of the
    193 MB exp-mu-primeagent brazil rep3 log. They carry nothing the run's
    record needs: measured on that file, every one of the 91 assistant
    ``message_end`` events carried ``usage`` (incl. ``cost.total``),
    ``stopReason``, ``model``, ``responseId`` and the final ``content`` — which
    is exactly what ``_parse_prime_usage`` reads. ``tool_execution_*`` and every
    other event are kept verbatim: they are the evidence that identified the
    zero-write failure. Non-JSON lines are kept. Idempotent; a file with no
    ``message_update`` lines is left untouched. Works on ``.log`` and ``.log.gz``
    (output keeps the input's form). Accepts a str because the in-container
    caller (entrypoint.sh) passes one — the first local echo cell (2026-09-05)
    hit ``'str' object has no attribute 'stat'`` here and silently skipped.
    """
    path = Path(path)
    try:
        before = path.stat().st_size
    except OSError:
        return 0, 0
    tmp = path.with_name(path.name + ".compact.tmp")
    dropped = 0
    opener = gzip.open if path.suffix == ".gz" else open
    with _open(path) as src, opener(tmp, "wb") as dst:
        for raw in src:
            if _MESSAGE_UPDATE_HINT in raw:
                try:
                    event = json.loads(raw)
                except ValueError:
                    event = None
                if isinstance(event, dict) and event.get("type") == "message_update":
                    dropped += 1
                    continue
            dst.write(raw)
    if dropped == 0:
        tmp.unlink(missing_ok=True)
        return before, before
    os.replace(tmp, path)
    return before, path.stat().st_size
