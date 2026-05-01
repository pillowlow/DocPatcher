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
    format_paragraph_block_listing,
    run_openai_document_extraction,
    write_extraction_csv,
)
from app.services.llm.example_project_sources import (
    load_agent_system_prompt,
    load_task_instruction,
)
from app.services.llm.openai_responses_composition import (
    compose_input_document_section,
    compose_openai_responses_user_input,
)


def test_format_paragraph_block_listing_sorted_by_paragraph() -> None:
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
    text, fname = format_paragraph_block_listing(blocks)
    assert fname == "a.docx"
    assert text.index("first") < text.index("second")


def test_compose_openai_responses_user_input_sections() -> None:
    merged = compose_openai_responses_user_input(
        task_instruction="Do the task.",
        document_section="DOCUMENT_METADATA:\n...\n",
    )
    assert "## Task instruction" in merged
    assert "Do the task." in merged
    assert "## Input document (parsed from DOCX)" in merged
    assert "DOCUMENT_METADATA" in merged


def test_compose_input_document_section() -> None:
    body = compose_input_document_section(
        doc_id="X",
        source_file_name="f.docx",
        paragraph_block_listing="[X-B0000]",
    )
    assert "doc_id: X" in body
    assert "source_file_name: f.docx" in body
    assert "PARAGRAPH_BLOCKS" in body
    assert "[X-B0000]" in body


def test_write_extraction_csv(tmp_path: Path) -> None:
    p = tmp_path / "sheet.csv"
    rows = [
        ContentSheetRow(
            block_id="D-B0001",
            paragraph_index=1,
            verbatim_text='say "hello"',
            topic_or_heading="t",
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
        agent_system_prompt="You are an admin assistant.",
        user_input="## Task instruction\n...\n",
        model_name="gpt-test",
        temperature=0.0,
    )
    assert out.overview_markdown.startswith("# Overview")
    assert len(out.content_sheet_rows) == 1
    fake_client.responses.create.assert_called_once()
    call_kw = fake_client.responses.create.call_args.kwargs
    assert call_kw["instructions"] == "You are an admin assistant."
    assert "## Task instruction" in call_kw["input"]


def test_load_task_instruction_reads_txt(tmp_path: Path) -> None:
    inst = tmp_path / "instructions"
    inst.mkdir()
    (inst / "full_document_extraction.txt").write_text("Task line.", encoding="utf-8")
    assert load_task_instruction(tmp_path) == "Task line."


def test_load_agent_system_prompt_reads_md(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "agent_system.md").write_text("# Agent\nHello.", encoding="utf-8")
    assert load_agent_system_prompt(tmp_path).startswith("# Agent")


def test_load_task_instruction_missing_file(tmp_path: Path) -> None:
    inst = tmp_path / "instructions"
    inst.mkdir()
    with pytest.raises(FileNotFoundError, match=r"full_document_extraction"):
        load_task_instruction(tmp_path)


def test_extract_overview_loads_three_sources_into_api_call(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    inst = tmp_path / "instructions"
    inst.mkdir()
    (inst / "full_document_extraction.txt").write_text(
        "TASK FROM FILE",
        encoding="utf-8",
    )
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / "agent_system.md").write_text(
        "AGENT SYSTEM FROM FILE",
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
            captured["input"] = kwargs.get("input")
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
    assert captured.get("instructions") == "AGENT SYSTEM FROM FILE"
    user_turn = str(captured.get("input") or "")
    assert "TASK FROM FILE" in user_turn
    assert "## Input document (parsed from DOCX)" in user_turn
    assert "PARAGRAPH_BLOCKS" in user_turn
    assert "only" in user_turn
