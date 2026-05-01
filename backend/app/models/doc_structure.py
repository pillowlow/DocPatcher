from __future__ import annotations

from pydantic import BaseModel, Field


class DocStructurePosition(BaseModel):
    section_index: int | None = None
    paragraph_index: int | None = None
    row_index: int | None = None
    col_index: int | None = None


class DocRunStyle(BaseModel):
    text: str
    font_name: str | None = None
    font_size_pt: float | None = None
    bold: bool | None = None
    italic: bool | None = None
    underline: bool | None = None
    font_color_rgb: str | None = None
    highlight_color: str | None = None


class DocParagraphStyle(BaseModel):
    style_name: str | None = None
    alignment: str | None = None
    space_before_pt: float | None = None
    space_after_pt: float | None = None
    line_spacing: float | None = None
    left_indent_pt: float | None = None
    right_indent_pt: float | None = None
    first_line_indent_pt: float | None = None


class DocCellStyle(BaseModel):
    vertical_alignment: str | None = None
    shading_fill: str | None = None
    table_style: str | None = None


class DocStructureBlock(BaseModel):
    structure_id: str
    source_part: str
    block_type: str
    order_index: int
    text: str
    is_placeholder: bool = False
    position: DocStructurePosition = Field(default_factory=DocStructurePosition)
    paragraph_style: DocParagraphStyle | None = None
    cell_style: DocCellStyle | None = None
    run_styles: list[DocRunStyle] = Field(default_factory=list)


class DocStructureXmlStats(BaseModel):
    xml_parts_total: int
    xml_parts_compressed_bytes: int
    xml_parts_uncompressed_bytes: int


class DocStructureDocument(BaseModel):
    doc_id: str
    file_name: str
    xml_stats: DocStructureXmlStats
    blocks: list[DocStructureBlock]
