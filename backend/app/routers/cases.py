from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from sqlmodel import Session, select

from ..settings import settings
from ..storage import (
    AuditEvent,
    Case,
    CaseStatus,
    ChecklistItem,
    Document,
    ExtractionRun,
    ExtractedField,
    GapItem,
    engine,
)
from ..utils import json_dumps, new_id, safe_filename
from ..workflows.process_case import process_case

router = APIRouter(tags=["cases"])


class CaseCreateRequest(Case):  # type: ignore[misc]
    pass


@router.post("/cases")
def create_case(payload: dict):
    required = ["jurisdiction", "entity_type", "products", "risk_tier"]
    for k in required:
        if k not in payload:
            raise HTTPException(status_code=400, detail=f"Missing field: {k}")

    case = Case(
        id=new_id("case"),
        jurisdiction=str(payload["jurisdiction"]).upper(),
        entity_type=str(payload["entity_type"]).lower(),
        products_json=json_dumps(payload["products"]),
        risk_tier=str(payload["risk_tier"]).lower(),
        client_name=payload.get("client_name"),
        status=CaseStatus.created.value,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )

    with Session(engine) as session:
        session.add(case)
        session.add(
            AuditEvent(
                id=new_id("audit"),
                case_id=case.id,
                event_type="case_created",
                payload_json=json_dumps(payload),
            )
        )
        session.commit()
        # Capture case_id before session closes to avoid DetachedInstanceError
        case_id = case.id

    return {"case_id": case_id}


@router.get("/cases/{case_id}")
def get_case(case_id: str):
    with Session(engine) as session:
        case = session.get(Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        docs = session.exec(select(Document).where(Document.case_id == case_id)).all()
        return {
            "case": case.model_dump(),
            "documents": [d.model_dump() for d in docs],
        }


@router.post("/cases/{case_id}/documents")
async def upload_documents(case_id: str, files: list[UploadFile] = File(...)):
    settings.ensure_dirs()
    with Session(engine) as session:
        case = session.get(Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

    stored: list[dict] = []
    for f in files:
        if not f.filename:
            continue
        data = await f.read()
        size_mb = len(data) / (1024 * 1024)
        if size_mb > settings.max_upload_mb:
            raise HTTPException(status_code=413, detail=f"File too large: {f.filename}")

        doc_id = new_id("doc")
        fname = safe_filename(f.filename)
        ext = Path(fname).suffix.lower()
        if ext not in {".pdf", ".png", ".jpg", ".jpeg", ".docx", ".txt"}:
            raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

        stored_path = settings.upload_dir / f"{doc_id}{ext}"
        stored_path.write_bytes(data)

        doc = Document(
            id=doc_id,
            case_id=case_id,
            filename=fname,
            stored_path=str(stored_path),
            content_type=f.content_type,
            size_bytes=len(data),
        )
        with Session(engine) as session:
            session.add(doc)
            session.add(
                AuditEvent(
                    id=new_id("audit"),
                    case_id=case_id,
                    event_type="document_uploaded",
                    payload_json=json_dumps({"document_id": doc_id, "filename": fname}),
                )
            )
            session.commit()
        stored.append({"document_id": doc_id, "filename": fname})

    return {"uploaded": stored}


@router.post("/cases/{case_id}/process")
def process(case_id: str, background: BackgroundTasks):
    with Session(engine) as session:
        case = session.get(Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")
        case.status = CaseStatus.processing.value
        case.updated_at = datetime.utcnow()
        session.add(case)
        run = ExtractionRun(id=new_id("run"), case_id=case_id)
        session.add(run)
        session.add(
            AuditEvent(
                id=new_id("audit"),
                case_id=case_id,
                event_type="processing_enqueued",
                payload_json=json_dumps({"run_id": run.id}),
            )
        )
        session.commit()
        # Capture run_id before session closes to avoid DetachedInstanceError
        run_id = run.id

    background.add_task(process_case, case_id=case_id, run_id=run_id)
    return {"run_id": run_id}


@router.get("/cases/{case_id}/checklist")
def get_checklist(case_id: str):
    with Session(engine) as session:
        items = session.exec(select(ChecklistItem).where(ChecklistItem.case_id == case_id)).all()
    return {"items": [i.model_dump() for i in items]}


@router.get("/cases/{case_id}/gaps")
def get_gaps(case_id: str):
    with Session(engine) as session:
        gaps = session.exec(select(GapItem).where(GapItem.case_id == case_id)).all()
    return {"items": [g.model_dump() for g in gaps]}


@router.get("/cases/{case_id}/fields")
def get_fields(case_id: str):
    with Session(engine) as session:
        fields = session.exec(select(ExtractedField).where(ExtractedField.case_id == case_id)).all()
    return {"items": [f.model_dump() for f in fields]}


@router.post("/cases/{case_id}/outreach-email")
def draft_email(case_id: str):
    from ..workflows.outreach import draft_outreach_email

    return draft_outreach_email(case_id)


@router.post("/cases/{case_id}/send-email")
def send_email(case_id: str, payload: dict):
    """POC endpoint: pretend to send outreach email and log it."""
    required = ["to", "subject", "body"]
    for k in required:
        if k not in payload:
            raise HTTPException(status_code=400, detail=f"Missing field: {k}")

    to = payload.get("to") or []
    cc = payload.get("cc") or []
    if isinstance(to, str):
        to = [to]
    if isinstance(cc, str):
        cc = [cc]

    with Session(engine) as session:
        case = session.get(Case, case_id)
        if not case:
            raise HTTPException(status_code=404, detail="Case not found")

        session.add(
            AuditEvent(
                id=new_id("audit"),
                case_id=case_id,
                event_type="outreach_email_sent",
                payload_json=json_dumps(
                    {
                        "to": to,
                        "cc": cc,
                        "subject": payload["subject"],
                        "body_preview": str(payload.get("body", ""))[:4000],
                    }
                ),
            )
        )
        session.commit()

    # In a real implementation, integrate with SMTP / email API here.
    return {"status": "sent"}

