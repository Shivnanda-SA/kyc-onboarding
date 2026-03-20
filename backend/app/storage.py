from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import text
from sqlmodel import Field, SQLModel, create_engine

from .settings import settings


class CaseStatus(str, Enum):
    created = "created"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class Case(SQLModel, table=True):
    id: str = Field(primary_key=True)
    jurisdiction: str
    entity_type: str
    products_json: str
    risk_tier: str
    client_name: str | None = None

    status: str = Field(default=CaseStatus.created.value)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Document(SQLModel, table=True):
    id: str = Field(primary_key=True)
    case_id: str = Field(index=True)
    filename: str
    stored_path: str
    content_type: str | None = None
    size_bytes: int

    detected_doc_type: str | None = None
    detected_doc_confidence: float | None = None
    detected_doc_rationale: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExtractionRun(SQLModel, table=True):
    id: str = Field(primary_key=True)
    case_id: str = Field(index=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: datetime | None = None
    status: str = Field(default="running")
    error: str | None = None


class ExtractedField(SQLModel, table=True):
    id: str = Field(primary_key=True)
    case_id: str = Field(index=True)
    document_id: str = Field(index=True)
    doc_type: str
    field_name: str = Field(index=True)
    value: str | None = None
    evidence: str | None = None
    confidence: float | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GapItem(SQLModel, table=True):
    id: str = Field(primary_key=True)
    case_id: str = Field(index=True)
    kind: str  # missing_doc | missing_field | inconsistency
    item_key: str
    severity: str = Field(default="medium")
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChecklistItem(SQLModel, table=True):
    id: str = Field(primary_key=True)
    case_id: str = Field(index=True)
    doc_type: str
    required: bool = True
    satisfied: bool = False
    satisfied_by_document_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AuditEvent(SQLModel, table=True):
    id: str = Field(primary_key=True)
    case_id: str = Field(index=True)
    event_type: str
    payload_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=datetime.utcnow)


def get_engine():
    settings.ensure_dirs()
    connect_args: dict[str, Any] = {"check_same_thread": False}
    return create_engine(f"sqlite:///{settings.sqlite_path.as_posix()}", connect_args=connect_args)


engine = get_engine()


def init_db() -> None:
    SQLModel.metadata.create_all(engine)
    # lightweight SQLite migration for new columns (POC)
    with engine.connect() as conn:
        cols = conn.execute(text("PRAGMA table_info(document)")).fetchall()
        existing = {c[1] for c in cols}  # (cid, name, type, notnull, dflt, pk)
        if "detected_doc_confidence" not in existing:
            conn.execute(text("ALTER TABLE document ADD COLUMN detected_doc_confidence REAL"))
        if "detected_doc_rationale" not in existing:
            conn.execute(text("ALTER TABLE document ADD COLUMN detected_doc_rationale TEXT"))
        conn.commit()

