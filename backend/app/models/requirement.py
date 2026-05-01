from pydantic import BaseModel, Field


class Requirement(BaseModel):
    requirement_id: str = Field(default="REQ001")
    text: str
