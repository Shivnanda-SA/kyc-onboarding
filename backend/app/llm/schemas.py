from __future__ import annotations

from pydantic import BaseModel, Field


class DocClassification(BaseModel):
    doc_type: str
    confidence: float = Field(ge=0.0, le=1.0)
    rationale: str


class FieldValue(BaseModel):
    value: str | None = None
    evidence: str | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class ExtractedFields(BaseModel):
    fields: dict[str, FieldValue]


class ExplainedGapItem(BaseModel):
    item: str
    why: str
    citations: list[str] = Field(default_factory=list)


class ExplainedGaps(BaseModel):
    items: list[ExplainedGapItem]


class OutreachEmail(BaseModel):
    subject: str
    body: str

