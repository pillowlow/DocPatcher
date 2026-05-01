"""Optional progress callbacks for extract / overview runs (CLI stderr, tests, future SSE)."""

from __future__ import annotations

import sys
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path
from typing import TextIO


class ExtractProgressKind(StrEnum):
    BATCH_BEGIN = "batch_begin"
    DOC_BEGIN = "doc_begin"
    XML_SCAN_START = "xml_scan_start"
    XML_PART_DONE = "xml_part_done"
    PARSE_DONE = "parse_done"
    LLM_START = "llm_start"
    LLM_DONE = "llm_done"
    DOC_DONE = "doc_done"
    BATCH_DONE = "batch_done"


class ExtractProgressEvent:
    __slots__ = (
        "kind",
        "doc_index",
        "doc_total",
        "path",
        "doc_id",
        "block_count",
        "row_count",
        "xml_parts_total",
        "xml_parts_done",
        "xml_parts_compressed_bytes",
    )

    def __init__(
        self,
        kind: ExtractProgressKind,
        doc_index: int,
        doc_total: int,
        *,
        path: Path | None = None,
        doc_id: str | None = None,
        block_count: int | None = None,
        row_count: int | None = None,
        xml_parts_total: int | None = None,
        xml_parts_done: int | None = None,
        xml_parts_compressed_bytes: int | None = None,
    ) -> None:
        self.kind = kind
        self.doc_index = doc_index
        self.doc_total = doc_total
        self.path = path
        self.doc_id = doc_id
        self.block_count = block_count
        self.row_count = row_count
        self.xml_parts_total = xml_parts_total
        self.xml_parts_done = xml_parts_done
        self.xml_parts_compressed_bytes = xml_parts_compressed_bytes


ProgressCallback = Callable[[ExtractProgressEvent], None]


def overall_percent(event: ExtractProgressEvent) -> int:
    """Rough overall completion for the whole batch (0–100)."""
    kind = event.kind
    i, n = event.doc_index, event.doc_total
    if n <= 0:
        return 100
    if kind == ExtractProgressKind.BATCH_BEGIN:
        return 0
    if kind == ExtractProgressKind.BATCH_DONE:
        return 100
    base = i - 1
    frac_by_kind: dict[ExtractProgressKind, float] = {
        ExtractProgressKind.DOC_BEGIN: 0.0,
        ExtractProgressKind.XML_SCAN_START: 0.03,
        ExtractProgressKind.XML_PART_DONE: 0.18,
        ExtractProgressKind.PARSE_DONE: 0.22,
        ExtractProgressKind.LLM_START: 0.24,
        ExtractProgressKind.LLM_DONE: 0.95,
        ExtractProgressKind.DOC_DONE: 1.0,
    }
    frac = frac_by_kind.get(kind, 0.0)
    return min(100, round(100 * (base + frac) / n))


def format_extract_progress_line(event: ExtractProgressEvent) -> str:
    pct = overall_percent(event)
    kind = event.kind

    if kind == ExtractProgressKind.BATCH_BEGIN:
        return f"[batch] {pct}% | start | {event.doc_total} document(s)"

    if kind == ExtractProgressKind.BATCH_DONE:
        return f"[batch] {pct}% | done | {event.doc_total} document(s) processed"

    if kind == ExtractProgressKind.XML_SCAN_START:
        parts = event.xml_parts_total or 0
        kb = round((event.xml_parts_compressed_bytes or 0) / 1024, 1)
        return f"[{event.doc_index}/{event.doc_total}] {pct}% | xml-scan | parts={parts} | compressed_kb={kb}"

    if kind == ExtractProgressKind.XML_PART_DONE:
        done = event.xml_parts_done or 0
        total = event.xml_parts_total or 0
        return (
            f"[{event.doc_index}/{event.doc_total}] {pct}% | xml-part | "
            f"{done}/{total} | {event.path.name if event.path else '?'}"
        )

    label = {
        ExtractProgressKind.DOC_BEGIN: "doc",
        ExtractProgressKind.XML_SCAN_START: "xml-scan",
        ExtractProgressKind.XML_PART_DONE: "xml-part",
        ExtractProgressKind.PARSE_DONE: "parse",
        ExtractProgressKind.LLM_START: "llm",
        ExtractProgressKind.LLM_DONE: "llm",
        ExtractProgressKind.DOC_DONE: "write",
    }[kind]

    name = event.path.name if event.path else "?"
    idx = event.doc_index
    total = event.doc_total
    parts = [f"[{idx}/{total}]", f"{pct}%", label]

    if event.doc_id:
        parts.append(f"id={event.doc_id}")
    if event.block_count is not None:
        parts.append(f"blocks={event.block_count}")
    if event.row_count is not None:
        parts.append(f"rows={event.row_count}")

    tail = [p for p in parts[3:] if p]
    mid = " | ".join(parts[:3])
    if tail:
        return f"{mid} | " + " | ".join(tail) + f" | {name}"
    return f"{mid} | {name}"


def make_cli_stderr_progress(file: TextIO | None = None) -> ProgressCallback:
    fh: TextIO = file if file is not None else sys.stderr

    def _cb(event: ExtractProgressEvent) -> None:
        fh.write(format_extract_progress_line(event) + "\n")
        fh.flush()

    return _cb


def emit_batch_begin(on_progress: ProgressCallback | None, doc_total: int) -> None:
    if on_progress:
        on_progress(ExtractProgressEvent(ExtractProgressKind.BATCH_BEGIN, 0, doc_total))


def emit_batch_done(on_progress: ProgressCallback | None, doc_total: int) -> None:
    if on_progress:
        on_progress(ExtractProgressEvent(ExtractProgressKind.BATCH_DONE, doc_total, doc_total))


def noop_progress(_: ExtractProgressEvent) -> None:
    """Typed no-op for default ``on_progress`` when wiring optional hooks."""

    return None
