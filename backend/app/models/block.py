from pydantic import BaseModel


class BlockPosition(BaseModel):
    paragraph_index: int


class Block(BaseModel):
    block_id: str
    doc_id: str
    file_name: str
    block_type: str = "paragraph"
    section_title: str | None = None
    text: str
    position: BlockPosition
