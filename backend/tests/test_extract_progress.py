from pathlib import Path

import pytest

from app.core.settings import Settings
from app.models.block import Block, BlockPosition
from app.models.workspace import ResolvedProjectPaths
from app.services.extract_progress import (
    ExtractProgressEvent,
    ExtractProgressKind,
    format_extract_progress_line,
    overall_percent,
)
from app.services.project_extract import run_extract_overview, run_extract_overview_all_input_docs


def test_overall_percent_batches_endpoints() -> None:
    begin = ExtractProgressEvent(ExtractProgressKind.BATCH_BEGIN, 0, 3)
    done = ExtractProgressEvent(ExtractProgressKind.BATCH_DONE, 3, 3)
    assert overall_percent(begin) == 0
    assert overall_percent(done) == 100


def test_overall_percent_increases_within_doc_slot() -> None:
    n = 2
    d0 = ExtractProgressEvent(ExtractProgressKind.DOC_BEGIN, 1, n, path=Path("a.docx"))
    p0 = ExtractProgressEvent(ExtractProgressKind.PARSE_DONE, 1, n, path=Path("a.docx"), block_count=5)
    l0 = ExtractProgressEvent(ExtractProgressKind.LLM_DONE, 1, n, path=Path("a.docx"), row_count=3)
    w0 = ExtractProgressEvent(ExtractProgressKind.DOC_DONE, 1, n, path=Path("a.docx"))
    d1 = ExtractProgressEvent(ExtractProgressKind.DOC_BEGIN, 2, n, path=Path("b.docx"))
    assert overall_percent(d0) <= overall_percent(p0) <= overall_percent(l0) <= overall_percent(w0)
    assert overall_percent(w0) < overall_percent(ExtractProgressEvent(ExtractProgressKind.DOC_DONE, 2, n))
    assert overall_percent(d1) >= overall_percent(w0)


def test_format_extract_progress_line_batch() -> None:
    line = format_extract_progress_line(
        ExtractProgressEvent(ExtractProgressKind.BATCH_BEGIN, 0, 4),
    )
    assert "batch" in line
    assert "4 document" in line


def test_format_extract_progress_line_doc_with_unicode_path() -> None:
    path = Path("工作.docx")
    line = format_extract_progress_line(
        ExtractProgressEvent(
            ExtractProgressKind.PARSE_DONE,
            2,
            5,
            path=path,
            doc_id="工作",
            block_count=10,
        ),
    )
    assert "工作.docx" in line
    assert "blocks=10" in line


@pytest.fixture()
def patched_extract_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.services.project_extract.parse_docx_to_blocks",
        lambda docx_path, doc_id: [
            Block(
                block_id="X-B0000",
                doc_id=doc_id,
                file_name=docx_path.name,
                text="x",
                position=BlockPosition(paragraph_index=0),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.project_extract.extract_overview_and_content_sheet",
        lambda **kwargs: {
            "doc_id": kwargs["doc_id"],
            "overview_path": "",
            "content_sheet_csv_path": "",
            "extraction_json_path": "",
            "rows": 2,
        },
    )


def test_run_extract_overview_emit_events(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, patched_extract_pipeline: None
) -> None:
    root = ResolvedProjectPaths(root=tmp_path)
    doc = tmp_path / "solo.docx"
    doc.write_bytes(b"x")

    events: list[ExtractProgressKind] = []

    def cb(e: ExtractProgressEvent) -> None:
        events.append(e.kind)

    settings = Settings(
        openai_api_key="sk-test",
        project_paths=root,
    )
    run_extract_overview(
        input_doc_path=doc,
        doc_id="solo",
        settings=settings,
        on_progress=cb,
        batch_doc_index=1,
        batch_doc_total=3,
    )
    expected = [
        ExtractProgressKind.DOC_BEGIN,
        ExtractProgressKind.PARSE_DONE,
        ExtractProgressKind.LLM_START,
        ExtractProgressKind.LLM_DONE,
        ExtractProgressKind.DOC_DONE,
    ]
    assert events == expected


def test_run_extract_overview_all_batch_bookends(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = ResolvedProjectPaths(root=tmp_path)
    ind = tmp_path / "input_docs"
    ind.mkdir(parents=True)
    (ind / "a.docx").write_bytes(b"a")
    (ind / "b.docx").write_bytes(b"b")

    monkeypatch.setattr(
        "app.services.project_extract.parse_docx_to_blocks",
        lambda docx_path, doc_id: [
            Block(
                block_id=f"{doc_id}-B0000",
                doc_id=doc_id,
                file_name=docx_path.name,
                text="t",
                position=BlockPosition(paragraph_index=0),
            )
        ],
    )
    monkeypatch.setattr(
        "app.services.project_extract.extract_overview_and_content_sheet",
        lambda **kwargs: {
            "doc_id": kwargs["doc_id"],
            "overview_path": "",
            "content_sheet_csv_path": "",
            "extraction_json_path": "",
            "rows": 1,
        },
    )

    kinds: list[ExtractProgressKind] = []

    def cb(e: ExtractProgressEvent) -> None:
        kinds.append(e.kind)

    settings = Settings(openai_api_key="sk-x", project_paths=root)
    run_extract_overview_all_input_docs(settings=settings, on_progress=cb)

    assert kinds[0] == ExtractProgressKind.BATCH_BEGIN
    assert kinds[-1] == ExtractProgressKind.BATCH_DONE
    assert kinds.count(ExtractProgressKind.DOC_DONE) == 2
