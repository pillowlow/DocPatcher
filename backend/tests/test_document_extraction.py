import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.core.settings import Settings
from app.models.block import Block, BlockPosition
from app.services.document_extraction import (
    ContentSheetRow,
    DocumentExtractionResult,
    extract_overview_and_content_sheet,
    format_blocks_numbered,
    run_openai_document_extraction,
    write_extraction_csv,
)
from app.services.llm.extraction_prompts import load_extraction_hints

def test_format_blocks_numbered_sorted_by_paragraph() -> None:
    blocks = [
        Block(
            block_id="D-B0001",
            doc_id="D",
            file_name="a.docx",
            text="second",
            position=BlockPosition(paragraph_index=1),
        ),
        Block(
            block_id="D-B0000",
            doc_id="D",
            file_name="a.docx",
            text="first",
            position=BlockPosition(paragraph_index=0),
        ),
    ]
    text, fname = format_blocks_numbered(blocks)
    assert fname == "a.docx"
    assert text.index("first") < text.index("second")


def test_write_extraction_csv(tmp_path: Path) -> None:
    p = tmp_path / "sheet.csv"
    rows = [
        ContentSheetRow(
            block_id="D-B0001",
            paragraph_index=1,
            verbatim_text='say "hello"',
            topic_or_heading='t',
        ),
        ContentSheetRow(
            block_id="D-B0000",
            paragraph_index=0,
            verbatim_text="a",
            topic_or_heading="",
        ),
    ]
    write_extraction_csv(p, rows)
    raw = p.read_text(encoding="utf-8").splitlines()
    assert raw[0] == "block_id,paragraph_index,topic_or_heading,verbatim_text"
    assert "D-B0000" in raw[1]


def test_run_openai_document_extraction_parses_response() -> None:
    payload = DocumentExtractionResult(
        overview_markdown="# Overview",
        content_sheet_rows=[
            ContentSheetRow(
                block_id="DOC001-B0000",
                paragraph_index=0,
                verbatim_text="Line one",
                topic_or_heading="intro",
            )
        ],
    )
    fake_resp = MagicMock()
    fake_resp.output_text = json.dumps(payload.model_dump())

    fake_client = MagicMock()
    fake_client.responses.create.return_value = fake_resp

    out = run_openai_document_extraction(
        fake_client,
        instructions="You output JSON matching the schema.",
        model_name="gpt-test",
        temperature=0.0,
        doc_id="DOC001",
        numbered_input="[DOC001-B0000] paragraph_index=0\n",
        file_name="f.docx",
    )
    assert out.overview_markdown.startswith("# Overview")
    assert len(out.content_sheet_rows) == 1
    fake_client.responses.create.assert_called_once()


def test_load_extraction_hints_reads_txt(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "full_document_extraction.txt").write_text("Hint line one.", encoding="utf-8")
    assert load_extraction_hints(tmp_path) == "Hint line one."


def test_load_extraction_hints_missing_file(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    with pytest.raises(FileNotFoundError, match=r"full_document_extraction"):
        load_extraction_hints(tmp_path)


def test_extract_overview_loads_hints_from_artifact_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "full_document_extraction.txt").write_text(
        "instructions from file",
        encoding="utf-8",
    )

    blocks = [
        Block(
            block_id="DOC001-B0000",
            doc_id="DOC001",
            file_name="f.docx",
            text="only",
            position=BlockPosition(paragraph_index=0),
        )
    ]
    payload = DocumentExtractionResult(
        overview_markdown="# OK",
        content_sheet_rows=[
            ContentSheetRow(
                block_id="DOC001-B0000",
                paragraph_index=0,
                verbatim_text="only",
                topic_or_heading="",
            )
        ],
    )
    fake_resp = MagicMock()
    fake_resp.output_text = json.dumps(payload.model_dump())

    captured: dict[str, object] = {}

    class FakeResponses:
        def create(self, **kwargs):  # type: ignore[no-untyped-def]
            captured["instructions"] = kwargs.get("instructions")
            return fake_resp

    class FakeClient:
        responses = FakeResponses()

    monkeypatch.setattr(
        "app.services.document_extraction.OpenAI",
        lambda api_key=None: FakeClient(),
    )

    settings = Settings()
    monkeypatch.setattr(settings, "openai_api_key", "dummy-key")

    extract_overview_and_content_sheet(
        blocks=blocks,
        settings=settings,
        artifact_root=tmp_path,
        doc_id="DOC001",
    )
    assert captured.get("instructions") == "instructions from file"
