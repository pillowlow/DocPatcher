from pathlib import Path

from docx import Document

from app.models.block import Block, BlockPosition


def parse_docx_to_blocks(docx_path: Path, doc_id: str) -> list[Block]:
    document = Document(docx_path)
    blocks: list[Block] = []

    for idx, paragraph in enumerate(document.paragraphs):
        text = paragraph.text.strip()
        if not text:
            continue
        block_id = f"{doc_id}-B{idx:04d}"
        blocks.append(
            Block(
                block_id=block_id,
                doc_id=doc_id,
                file_name=docx_path.name,
                text=text,
                position=BlockPosition(paragraph_index=idx),
            )
        )
    return blocks
