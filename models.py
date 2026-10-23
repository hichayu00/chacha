"""Day6, Day8에서 학습한 Pydantic 입력 검증."""

from pydantic import BaseModel, ConfigDict, Field


class EntryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=20)
    content: str = Field(min_length=1, max_length=1000)


class EntryOut(EntryCreate):
    id: int
    created_at: str
