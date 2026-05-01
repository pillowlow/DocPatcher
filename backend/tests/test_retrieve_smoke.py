from app.models.block import Block, BlockPosition
from app.models.requirement import Requirement
from app.services.retriever import retrieve_candidates


def test_retrieve_candidates_smoke() -> None:
    blocks = [
        Block(
            block_id="DOC001-B0001",
            doc_id="DOC001",
            file_name="x.docx",
            text="Update the security requirements section.",
            position=BlockPosition(paragraph_index=1),
        ),
        Block(
            block_id="DOC001-B0002",
            doc_id="DOC001",
            file_name="x.docx",
            text="This paragraph is unrelated.",
            position=BlockPosition(paragraph_index=2),
        ),
    ]
    requirement = Requirement(
        requirement_id="REQ001", text="Add details to security requirements."
    )

    result = retrieve_candidates(requirement, blocks, top_k=1)
    assert result.requirement_id == "REQ001"
    assert len(result.candidates) == 1
    assert result.candidates[0].block_id == "DOC001-B0001"
